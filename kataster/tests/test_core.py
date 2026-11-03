import io
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from defusedxml import ElementTree as ET
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Polygon
from kataster.core import (Parcel, ServiceError, arc_points, choose_address,
                           extract, normalize_parcel, select_parcels, url_with)


def address_feature(house='8C',street='Kirchenrottweg',postcode='63329',coords=(8.6527898,49.9723433),kind='house'):
    return {'properties':{'type':kind,'countrycode':'DE','housenumber':house,
                          'street':street,'postcode':postcode,'state':'Hessen','city':'Egelsbach'},
            'geometry':{'type':'Point','coordinates':coords}}


class AddressSafety(unittest.TestCase):
    def test_different_house_not_accepted(self):
        with self.assertRaises(ServiceError):choose_address([address_feature('8B')],'Kirchenrottweg 8C 63329 Egelsbach')
    def test_street_centroid_not_accepted(self):
        with self.assertRaises(ServiceError):choose_address([address_feature(kind='street')],'Kirchenrottweg 8C 63329 Egelsbach')
    def test_wrong_postcode_not_accepted(self):
        with self.assertRaises(ServiceError):choose_address([address_feature(postcode='12345')],'Kirchenrottweg 8C 63329 Egelsbach')
    def test_two_house_points_require_disambiguation(self):
        with self.assertRaises(ServiceError):choose_address([address_feature(),address_feature(coords=(8.653,49.972))],'Kirchenrottweg 8C 63329 Egelsbach')
    def test_case_insensitive_suffix(self):
        self.assertEqual(choose_address([address_feature()],'Kirchenrottweg 8c 63329 Egelsbach')['properties']['housenumber'],'8C')
    def test_numeric_street_does_not_replace_house(self):
        with self.assertRaises(ServiceError):choose_address([address_feature('18','Straße des 18. Oktober','04103')],'Straße des 18. Oktober 1 04103 Leipzig')


    def test_city_state_without_state_property(self):
        f=address_feature('15','Rathausstraße','10178')
        del f['properties']['state'];f['properties']['city']='Berlin'
        self.assertEqual(choose_address([f],'Rathausstrasse 15, 10178 Berlin')['properties']['state'],'Berlin')
    def test_multiple_poi_points_are_only_provisionally_accepted(self):
        features=[address_feature(coords=(8.65,49.97)),address_feature(coords=(8.651,49.97))]
        r=choose_address(features,'Kirchenrottweg 8C, 63329 Egelsbach',allow_candidates=True)
        self.assertEqual(len(r['_address_candidates']),2)


class SpatialCorrectness(unittest.TestCase):
    def test_envelope_match_is_not_polygon_match(self):
        ring=[(0,0),(10,0),(10,10),(0,10),(0,0)]
        hole=[(3,3),(7,3),(7,7),(3,7),(3,3)]
        p=Parcel({'flurstueck':'1'},Polygon(ring,[hole]))
        self.assertEqual(select_parcels([p],5,5),[])
        self.assertEqual(select_parcels([p],1,1),[p])
    def test_shared_boundary_returns_all_candidates(self):
        a=Parcel({},Polygon([(0,0),(1,0),(1,1),(0,1)]))
        b=Parcel({},Polygon([(1,0),(2,0),(2,1),(1,1)]))
        self.assertEqual(len(select_parcels([a,b],1,.5)),2)
    def test_circular_arc_large_projected_coordinates(self):
        ox,oy=475000,5535000
        points=arc_points((ox+10,oy),(ox,oy+10),(ox-10,oy))
        self.assertTrue(all(abs(math.hypot(x-ox,y-oy)-10)<1e-6 for x,y in points))
        self.assertTrue(all(y>=oy-1e-8 for x,y in points))
        for (a,b),(c,d) in zip(points,points[1:]):
            self.assertLessEqual(10-math.hypot((a+c)/2-ox,(b+d)/2-oy),.001001)
    def test_no_flur_remains_null(self):
        e=ET.fromstring('<CadastralParcel><nationalCadastralReference>020101___01396______</nationalCadastralReference><label>1396</label></CadastralParcel>')
        self.assertIsNone(normalize_parcel(e,'HH')['flur'])
    def test_state_mismatch_rejected(self):
        e=ET.fromstring('<CadastralParcel><nationalCadastralReference>020101___01396______</nationalCadastralReference></CadastralParcel>')
        with self.assertRaises(ServiceError):normalize_parcel(e,'HE')


class OutputContract(unittest.TestCase):
    def test_bavaria_returns_partial_and_60m_extent(self):
        # No credentials: map succeeds, metadata must explicitly require access.
        loc={'eingabe':'Test','gefunden':'Test','bundesland':'BY','lon':11.5761,'lat':48.1374}
        class FakeClient:records=[]
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ',{'KATASTER_BY_USER':'','KATASTER_BY_PASSWORD':''}), patch('kataster.core.wms_image',return_value=(Image.new('RGB',(1600,1200),'beige'),{'typ':'amtlicher_WMS'})):
            result=extract('Test',tmp,client=FakeClient(),location=loc)
            self.assertEqual(result['status'],'teilweise')
            self.assertEqual(result['grundstueck_status'],'zugang_erforderlich')
            self.assertEqual(result['grundstuecke'],[])
            x0,y0,x1,y1=result['bild']['bbox']
            self.assertAlmostEqual(x1-x0,60);self.assertAlmostEqual(y1-y0,45)
            self.assertTrue(Path(tmp,'grundstueck.json').is_file())
            with Image.open(Path(tmp,'karte.png')) as image:self.assertEqual(image.size,(1600,1340))
    def test_two_address_points_on_different_parcels_rejected(self):
        lon,lat=8.6527898,49.9723433
        x,y=Transformer.from_crs(4326,25832,always_xy=True).transform(lon,lat)
        loc={'eingabe':'Test','gefunden':'Test','bundesland':'HE','lon':lon,'lat':lat,
             'weitere_adresspunkte':[[lon,lat],[lon+.01,lat]]}
        parcel=Parcel({'gemarkung':'Egelsbach'},Polygon([(x-5,y-5),(x+5,y-5),(x+5,y+5),(x-5,y+5)]))
        class FakeClient:records=[]
        with tempfile.TemporaryDirectory() as tmp, patch('kataster.core.wfs_features',return_value=[parcel]), patch('kataster.core.enrich_name'):
            with self.assertRaises(ServiceError) as err:extract('Test',tmp,client=FakeClient(),location=loc)
            self.assertEqual(err.exception.code,'ADDRESS_AMBIGUOUS')

    def test_invalid_width_rejected_before_network(self):
        for v in [0,-1,float('nan'),float('inf'),2000]:
            with self.assertRaises(ServiceError):extract('x','unused',v)
    def test_existing_url_parameters_preserved_without_duplicate_request(self):
        u=url_with('https://example.org/wms?layer_id=123&REQUEST=GetCapabilities',{'REQUEST':'GetMap','BBOX':'1,2,3,4'})
        self.assertIn('layer_id=123',u);self.assertNotIn('GetCapabilities',u)

if __name__=='__main__':unittest.main()
