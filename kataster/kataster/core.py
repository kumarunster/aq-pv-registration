from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import subprocess
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from defusedxml import ElementTree as ET
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from pyproj import CRS, Transformer
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import transform as transform_geometry

PROVIDERS = json.loads(Path(__file__).with_name('providers.json').read_text())
ESRI = 'https://services2.arcgis.com/jUpNdisbWqRpMo35/arcgis/rest/services/flstk_DE/FeatureServer/0/query'
ESRI_CREDIT = ('Flurstücke: Esri Deutschland, aus ALKIS der Länder harmonisiert; '
               'GeoBasis DE/LGL BW, LG Brandenburg, LGBremen, Hamburg LGV, M V, LGLN, '
               'LVermGeoRP, LVGL SL, Geodaten Sachsen, LVermGeo LSA, LVermGeo SH, GDI Th '
               '[Daten geändert]. Quelle und Stand siehe JSON.')
OSM_CREDIT = 'Adresssuche: © OpenStreetMap-Mitwirkende (ODbL), Photon'
GML = 'http://www.opengis.net/gml/3.2'
XLINK = '{http://www.w3.org/1999/xlink}href'
_geo_lock = threading.Lock()
_last_geo = 0.0


class ServiceError(Exception):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code, self.details = code, details


def local(tag):
    return tag.rsplit('}', 1)[-1]


def norm(s):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(s).casefold()).encode('ascii', 'ignore').decode().lower().replace('strasse', 'str'))


def text(e, *names):
    for name in names:
        for c in e:
            if local(c.tag) == name and c.text and c.text.strip():
                return c.text.strip()
    return None


def descendant(e, name):
    return next((c.text.strip() for c in e.iter() if local(c.tag) == name and c.text and c.text.strip()), None)


def number(s):
    if s is None or not str(s).strip(' _'):
        return None
    digits = re.search(r'\d+', str(s))
    return str(int(digits[0])) if digits else None


def url_with(url, params):
    parts = urlsplit(url)
    old = [(k,v) for k,v in parse_qsl(parts.query) if k.lower() not in {p.lower() for p in params}]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(old + list(params.items())), ''))


class Client:
    """Disk cache, bounded downloads, TLS validation using system curl."""
    def __init__(self, cache_dir):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.records = []
        self.licenses = []

    def get(self, url, params=None, ttl=0):
        url = url_with(url, params or {})
        path = self.cache / (hashlib.sha256(url.encode()).hexdigest() + '.bin')
        cached = ttl and path.exists() and time.time() - path.stat().st_mtime < ttl
        if cached:
            data = path.read_bytes()
        else:
            cmd = [os.environ.get('KATASTER_CURL', '/usr/bin/curl' if Path('/usr/bin/curl').exists() else 'curl'), '--fail', '--silent', '--show-error', '--location',
                   '--proto', '=https', '--proto-redir', '=https', '--max-time', '40',
                   '--connect-timeout', '12', '--max-filesize', '30000000',
                   '--user-agent', 'KatasterService/1.0 (address-to-cadastral-extract)', url]
            auth = None
            if urlsplit(url).hostname == 'geoservices.bayern.de' and os.environ.get('KATASTER_BY_USER') and os.environ.get('KATASTER_BY_PASSWORD'):
                # Keep credentials out of process arguments, URLs, result JSON and logs.
                value = os.environ['KATASTER_BY_USER'] + ':' + os.environ['KATASTER_BY_PASSWORD']
                escaped = value.replace('\\','\\\\').replace('"','\\"').replace('\n','').replace('\r','')
                cmd[1:1] = ['--config', '-']
                auth = ('user = "' + escaped + '"\n').encode()
            try:
                r = subprocess.run(cmd, input=auth, capture_output=True, timeout=45)
            except (OSError,subprocess.TimeoutExpired) as e:
                raise ServiceError('UPSTREAM_ERROR','Netzwerkabruf konnte nicht abgeschlossen werden.',str(e)) from e
            if r.returncode:
                raise ServiceError('UPSTREAM_ERROR', f'Abruf fehlgeschlagen: {urlsplit(url).netloc}',
                                   (r.stderr.decode(errors='replace') + '\n' + r.stdout[:800].decode(errors='replace')).strip())
            data = r.stdout
            if ttl:
                tmp = path.with_suffix(f'.{threading.get_ident()}.tmp')
                tmp.write_bytes(data)
                tmp.replace(path)
        self.records.append({'url': url, 'sha256': hashlib.sha256(data).hexdigest(),
                             'abgerufen_am': datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if cached else datetime.now(timezone.utc).isoformat(),
                             'aus_cache': bool(cached)})
        return data

    def xml(self, url, params=None, ttl=0):
        raw = self.get(url, params, ttl)
        try:
            root = ET.fromstring(raw)
        except Exception as e:
            raise ServiceError('INVALID_XML', 'Der Geodienst hat kein gültiges XML geliefert.', str(e)) from e
        errors = [e.text.strip() for e in root.iter() if local(e.tag) in ('ExceptionText', 'ServiceException') and e.text]
        if errors:
            raise ServiceError('OGC_ERROR', '; '.join(errors))
        if local(root.tag) in ('WMS_Capabilities','WMT_MS_Capabilities','WFS_Capabilities'):
            notes=[{'feld':local(e.tag),'text':' '.join(e.itertext()).strip()} for e in root.iter() if local(e.tag) in ('Fees','AccessConstraints')]
            notice={'dienst':url,'angaben':notes}
            if notice not in self.licenses:self.licenses.append(notice)
        return root, raw


def choose_address(features, query, allow_candidates=False):
    """Never silently accept street/municipality centroids or different house numbers."""
    postcode = re.search(r'\b\d{5}\b', query)
    house_matches = re.findall(r'(?<!\d)(\d{1,4}\s?[a-zA-Z]?)(?!\d)', query)
    wanted = {norm(house_matches[-1])} if house_matches else set()
    valid = []
    for f in features:
        p = f.get('properties', {})
        if p.get('countrycode', '').upper() != 'DE' or p.get('type') != 'house':
            continue
        if not p.get('housenumber') or norm(p['housenumber']) not in wanted:
            continue
        if postcode and p.get('postcode') != postcode[0]:
            continue
        # Photon is fuzzy. Require the returned street to occur in the query.
        if not p.get('street') or norm(p['street']) not in norm(query):
            continue
        if not postcode and p.get('city') and norm(p['city']) not in norm(query):
            continue
        if not p.get('state') and p.get('city') in ('Berlin','Hamburg','Bremen'):
            p['state']=p['city']
        if not p.get('state'):continue
        coords = f['geometry']['coordinates']
        if not any(math.dist(coords, v['geometry']['coordinates']) < 0.00002 for v in valid):
            valid.append(f)
    if len(valid)>1:
        # Prefer an explicit OSM address/building over businesses sharing it.
        direct=[f for f in valid if f['properties'].get('osm_key')=='building' or
                (f['properties'].get('osm_key')=='place' and f['properties'].get('osm_value')=='house')]
        if len(direct)==1:valid=direct
        else:
            areas={ (f['properties'].get('osm_type'),f['properties'].get('osm_id')):f for f in valid if f['properties'].get('extent') }
            if len(areas)==1:
                area=next(iter(areas.values()));west,north,east,south=area['properties']['extent']
                if all(west-0.00001<=f['geometry']['coordinates'][0]<=east+0.00001 and south-0.00001<=f['geometry']['coordinates'][1]<=north+0.00001 for f in valid):valid=[area]
    if len(valid)>1 and allow_candidates:
        # POIs can share the address. Do not accept them until ALL points have
        # been proven to belong to the SAME cadastral parcel in extract().
        states={f['properties']['state'] for f in valid}
        if len(states)==1:
            first=dict(valid[0]);first['_address_candidates']=[f['geometry']['coordinates'] for f in valid]
            return first
    if len(valid) != 1:
        raise ServiceError('ADDRESS_AMBIGUOUS' if valid else 'ADDRESS_NOT_EXACT',
                           'Kein eindeutiger Haustreffer. Straße, Hausnummer, PLZ und Ort präzisieren.',
                           [f.get('properties') for f in features])
    return valid[0]


def geocode(client, address):
    global _last_geo
    if not isinstance(address, str) or not 5 <= len(address) <= 300:
        raise ServiceError('INVALID_ADDRESS', 'Adresse muss 5 bis 300 Zeichen enthalten.')
    base = os.environ.get('KATASTER_PHOTON_URL', 'https://photon.komoot.io/api/')
    with _geo_lock:
        # Low-volume, explicit single-user queries; switch URL for production.
        delay = 1.1 - (time.monotonic() - _last_geo)
        if delay > 0:
            time.sleep(delay)
        raw = client.get(base, {'q': address, 'limit': 10, 'lang': 'de', 'bbox': '5.8,47.2,15.1,55.1'}, ttl=604800)
        _last_geo = time.monotonic()
    f = choose_address(json.loads(raw).get('features', []), address, allow_candidates=True)
    p = f['properties']
    state = next((c for c,v in PROVIDERS.items() if norm(v['name']) == norm(p['state'])), None)
    if state is None:
        raise ServiceError('STATE_UNKNOWN', 'Bundesland nicht eindeutig erkannt.', p)
    lon, lat = f['geometry']['coordinates']
    label = f"{p['street']} {p['housenumber']}, {p.get('postcode','')} {p.get('city','')}".strip()
    source = 'Photon / OpenStreetMap'
    if state == 'HE':
        # Preserve the official Hessian house coordinates used by the original workflow.
        try:
            raw = client.get('https://www.geoportal.hessen.de/mapbender/geoportal/gaz_geom_mobile.php',
                dict(searchText=label, outputFormat='json', resultTarget='web', searchEPSG=25832,
                     maxResults=15, maxRows=15, map_width=1600, map_height=1200), ttl=604800)
            hits = json.loads(raw).get('geonames', [])
            if len(hits) == 1 and hits[0].get('category') == 'haus':
                h = hits[0]
                x,y = (float(h['minx'])+float(h['maxx']))/2, (float(h['miny'])+float(h['maxy']))/2
                lon,lat = Transformer.from_crs(25832,4326,always_xy=True).transform(x,y)
                source = 'Geoportal Hessen (Hauskoordinate); Bundeslandermittlung: Photon'
        except (ServiceError, ValueError, KeyError):
            pass
    return {'eingabe': address, 'gefunden': label, 'bundesland': state, 'lon': lon, 'lat': lat,
            'quelle': source, 'weitere_adresspunkte': f.get('_address_candidates',[]), 'genauigkeit': 'Hauspunkt; Zuordnung durch räumliche Überlagerung, keine amtlich bestätigte Adressrelation'}


@dataclass
class Parcel:
    data: dict
    geometry: object
    element: object = None


def arc_points(a,b,c):
    # Densify GML circular arcs to <= 1 mm chord error. Reject degenerate arcs.
    ax,ay=a
    bx,by=b[0]-ax,b[1]-ay;cx,cy=c[0]-ax,c[1]-ay
    det=2*(bx*cy-by*cx)
    if abs(det)<1e-8:return [a,b,c]
    bb=bx*bx+by*by;cc=cx*cx+cy*cy
    ux=ax+(bb*cy-cc*by)/det
    uy=ay+(cc*bx-bb*cx)/det
    radius=math.hypot(ax-ux,ay-uy)
    angles=[math.atan2(v[1]-uy,v[0]-ux) for v in (a,b,c)]
    span=(angles[2]-angles[0])%(2*math.pi)
    middle=(angles[1]-angles[0])%(2*math.pi)
    if middle>span:span-=2*math.pi
    step=2*math.acos(max(-1,min(1,1-0.001/radius))) if radius>0.001 else math.pi/4
    count=max(2,math.ceil(abs(span)/max(step,1e-6)))
    if count>20000:raise ServiceError('GEOMETRY_TOO_COMPLEX','Zu komplexer Kreisbogen.')
    return [a]+[(ux+radius*math.cos(angles[0]+span*i/count),uy+radius*math.sin(angles[0]+span*i/count)) for i in range(1,count)]+[c]


def ring_coords(e):
    segments=[]
    def read(node):
        kind=local(node.tag)
        if kind in ('Circle','CircleByCenterPoint','ArcByCenterPoint'):
            raise ServiceError('CURVED_GEOMETRY','Nicht unterstützte Kreis-Geometrie.')
        if kind in ('Arc','ArcString'):
            vals=next((c for c in node.iter() if local(c.tag)=='posList'),None)
            if vals is None or not vals.text:raise ServiceError('CURVED_GEOMETRY','Kreisbogen ohne posList.')
            nums=list(map(float,vals.text.split()));pts=list(zip(nums[::2],nums[1::2]))
            if len(pts)<3 or len(pts)%2!=1:raise ServiceError('CURVED_GEOMETRY','Ungültiger Kreisbogen.')
            seg=[]
            for i in range(0,len(pts)-2,2):
                arc=arc_points(*pts[i:i+3]);seg.extend(arc[1:] if seg else arc)
            segments.append(seg);return
        if kind=='posList' and node.text:
            nums=list(map(float,node.text.split()));dim=int(node.get('srsDimension','2'))
            segments.append(list(zip(nums[0::dim],nums[1::dim])));return
        for c in node:read(c)
    read(e)
    coords=[]
    for segment in segments:
        if coords and segment and math.dist(coords[-1],segment[-1])<0.01:segment.reverse()
        if coords and segment and math.dist(coords[-1],segment[0])>0.02:
            raise ServiceError('GEOMETRY_DISCONNECTED','Unverbundene Ringsegmente.')
        coords.extend(segment[1:] if coords and segment and coords[-1]==segment[0] else segment)
    if not coords:
        for c in e.iter():
            if local(c.tag)=='pos' and c.text:coords.append(tuple(map(float,c.text.split()[:2])))
    if len(coords)<4:raise ServiceError('GEOMETRY_MISSING','Keine auswertbare Polygon-Geometrie.')
    return coords


def gml_geometry(feature, epsg):
    prop = next((c for c in feature if local(c.tag) in ('geometry','geometrie','geom','position')), None)
    if prop is None:
        raise ServiceError('GEOMETRY_MISSING', 'Flurstück ohne Geometrie.')
    polygons = []
    for patch in prop.iter():
        if local(patch.tag) not in ('Polygon', 'PolygonPatch'):
            continue
        outer = next((c for c in patch if local(c.tag) == 'exterior'), None)
        if outer is not None:
            holes = [ring_coords(c) for c in patch if local(c.tag) == 'interior']
            polygons.append(Polygon(ring_coords(outer), holes))
    if not polygons:
        raise ServiceError('GEOMETRY_MISSING', 'Polygonform wird nicht unterstützt.')
    geom = MultiPolygon(polygons) if len(polygons)>1 else polygons[0]
    srs = next((c.get('srsName') for c in prop.iter() if c.get('srsName')), f'EPSG:{epsg}')
    source = CRS.from_user_input(srs)
    if source.to_epsg() != epsg:
        t = Transformer.from_crs(source, epsg, always_xy=True)
        geom = transform_geometry(t.transform, geom)
    if not geom.is_valid:
        raise ServiceError('GEOMETRY_INVALID', 'Ungültige Flurstücksgeometrie; keine automatische Reparatur.')
    return geom


def normalize_parcel(e, state):
    key = text(e, 'nationalCadastralReference', 'flstkennz', 'flurstueckskennzeichen', 'fsko')
    if not key or not re.fullmatch(r'[0-9_]{18,20}',key):
        raise ServiceError('PARCEL_ID_MISSING', 'Kein gültiges Flurstückskennzeichen.')
    if key[:2] != PROVIDERS[state]['landesschluessel']:
        raise ServiceError('STATE_MISMATCH', 'Flurstück und Adress-Bundesland widersprechen sich.')
    zae = text(e,'flstnrzae','zaehler','zae') or descendant(e,'zaehler') or number(key[9:14])
    nen = text(e,'flstnrnen','nenner','nen') or descendant(e,'nenner') or number(key[14:18])
    zae,nen = number(zae),number(nen)
    label = text(e,'label','flurstueckstext','flurstnr') or (zae + ('/'+nen if nen and nen!='0' else ''))
    flur = number(text(e,'flur','flurnummer','fln')) or number(key[6:9])
    gem = text(e,'gemarkung','gemarkung_name','namgmk')
    # NAS's gemarkung is a structured key, not a name.
    if gem and gem.isnumeric():gem=None
    area = text(e,'areaValue','flaeche','amtlicheFlaeche','amtliche_flaeche','afl')
    return {'gemarkung': gem, 'gemarkungsschluessel':key[:6], 'gemarkungsnummer':key[2:6],
            'flur': flur if flur and flur!='0' else None,
            'flur_status':'vorhanden' if flur and flur!='0' else 'im_Datensatz_nicht_gefuehrt',
            'flurstueck':label, 'zaehler':zae, 'nenner':nen if nen and nen!='0' else None,
            'flurstueckskennzeichen':key, 'amtliche_flaeche_m2':float(area) if area else None,
            'objektstand':text(e,'aktualit','beginLifespanVersion','beginn','beg') or descendant(e,'timePosition') or descendant(e,'beginnt'),
            'datenquelle':'amtlicher_Landesdienst'}


def wfs_config(client, state):
    p = PROVIDERS[state]
    root,raw = client.xml(p['wfs'],dict(SERVICE='WFS',REQUEST='GetCapabilities'),ttl=86400)
    # Use the namespace URI, not just a server-specific prefix (important for SH).
    # iterparse yields ('start-ns', (prefix, URI)).
    namespaces = dict(v for event,v in ET.iterparse(io.BytesIO(raw), events=['start-ns']))
    types = [e for e in root.iter() if local(e.tag)=='FeatureType']
    ft = next((e for e in types if (text(e,'Name') or '').split(':')[-1] in ('Flurstueck','AX_Flurstueck','CadastralParcel','v_al_flurstueck','flurstuecke')),None)
    if ft is None:
        raise ServiceError('WFS_SCHEMA_UNSUPPORTED', 'Kein Flurstücks-FeatureType im Landesdienst gefunden.')
    name = text(ft,'Name')
    return name, namespaces.get(name.split(':')[0]), root


def wfs_features(client, state, bbox):
    p = PROVIDERS[state]
    name, uri, _ = wfs_config(client,state)
    crs = f"urn:ogc:def:crs:EPSG::{p['epsg']}"
    params = dict(SERVICE='WFS',VERSION='2.0.0',REQUEST='GetFeature',TYPENAMES=name,
                  SRSNAME=crs,BBOX=','.join(map(str,bbox))+','+crs,COUNT=100)
    if uri:params['NAMESPACES']=f'xmlns({name.split(":")[0]},{uri})'
    root,_ = client.xml(p['wfs'],params)
    features = [e for e in root.iter() if local(e.tag)==name.split(':')[-1]]
    if len(features)>=100:
        raise ServiceError('RESULT_TRUNCATED','Zu viele Kandidaten; keine eindeutige Zuordnung möglich.')
    result=[]
    for e in features:
        result.append(Parcel(normalize_parcel(e,state),gml_geometry(e,p['epsg']),e))
    return result


def zoning_name(root):
    n = next((c for c in root if local(c.tag)=='name'),None)
    return descendant(n,'text') if n is not None else None


def enrich_name(client,state,parcel):
    p=PROVIDERS[state]
    if parcel.data['gemarkung']:
        return
    e=parcel.element
    if e is None:return
    if local(e.tag)=='CadastralParcel':
        link = next((c.get(XLINK) for c in e if local(c.tag)=='zoning'),None)
        for _ in range(3):
            if not link:break
            # Treat links as identifiers only. Always query the configured public
            # WFS, even when it advertises a registry URI or an inline fragment.
            parts=urlsplit(link)
            ident=dict(parse_qsl(parts.query)).get('ID') or parts.fragment or parts.path.rstrip('/').split('/')[-1]
            if not re.fullmatch(r'CadastralZoning_[0-9_]+',ident):
                raise ServiceError('UNEXPECTED_ZONING_ID','Katasterbezirk-ID wird nicht unterstützt.')
            root,_=client.xml(p['wfs'],dict(SERVICE='WFS',VERSION='2.0.0',REQUEST='GetFeature',
                STOREDQUERY_ID='urn:ogc:def:query:OGC-WFS::GetFeatureById',ID=ident),ttl=86400)
            # Some implementations return a FeatureCollection around the zoning.
            root=next((c for c in root.iter() if local(c.tag)=='CadastralZoning'),root)
            level=descendant(root,'LocalisedCharacterString') or ''
            if 'gemarkung' == level.lower() or (len(text(root,'nationalCadastalZoningReference') or '')==6):
                parcel.data['gemarkung']=zoning_name(root)
                return
            link=next((c.get(XLINK) for c in root if local(c.tag)=='upperLevelUnit'),None)
    elif local(e.tag)=='AX_Flurstueck':
        # A Gemarkung is a non-spatial NAS catalogue object. Filter by its official key.
        name,uri,_=wfs_config(client,state)
        prefix=name.split(':')[0]
        gem=parcel.data['gemarkungsnummer']
        filt=(f'<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0" xmlns:{prefix}="{uri}">'
              f'<fes:PropertyIsEqualTo><fes:ValueReference>{prefix}:schluessel/{prefix}:AX_Gemarkung_Schluessel/{prefix}:gemarkungsnummer</fes:ValueReference>'
              f'<fes:Literal>{gem}</fes:Literal></fes:PropertyIsEqualTo></fes:Filter>')
        params=dict(SERVICE='WFS',VERSION='2.0.0',REQUEST='GetFeature',TYPENAMES=prefix+':AX_Gemarkung',
                    NAMESPACES=f'xmlns({prefix},{uri})',FILTER=filt,COUNT=5)
        root,_=client.xml(p['wfs'],params,ttl=86400)
        candidates=[c for c in root.iter() if local(c.tag)=='AX_Gemarkung' and descendant(c,'gemarkungsnummer')==gem]
        if len(candidates)==1:
            parcel.data['gemarkung']=text(candidates[0],'bezeichnung')


def esri_features(client,state,bbox_or_point,point=False):
    epsg=PROVIDERS[state]['epsg']
    params=dict(f='json',geometry=','.join(map(str,bbox_or_point)),
                geometryType='esriGeometryPoint' if point else 'esriGeometryEnvelope',
                inSR=epsg,outSR=epsg,spatialRel='esriSpatialRelIntersects',
                outFields='*',returnGeometry='true',resultRecordCount=100)
    result=json.loads(client.get(ESRI,params))
    if 'error' in result:raise ServiceError('ESRI_ERROR','Ersatzquelle meldet einen Fehler.',result['error'])
    if result.get('exceededTransferLimit'):raise ServiceError('RESULT_TRUNCATED','Ersatzquelle hat die Antwort gekürzt.')
    parcels=[]
    for f in result.get('features',[]):
        a=f['attributes'];key=a.get('Flurstückskennzeichen')
        if not key or key[:2]!=PROVIDERS[state]['landesschluessel']:continue
        # Esri rings: classify by containment depth, preserving holes and islands.
        rings=[Polygon(r) for r in f['geometry']['rings']]
        shells=[]
        for i,r in enumerate(rings):
            parents=[j for j,v in enumerate(rings) if j!=i and v.contains(r)]
            if len(parents)%2:continue
            holes=[list(v.exterior.coords) for j,v in enumerate(rings) if j!=i and r.contains(v) and
                   len([k for k,w in enumerate(rings) if k!=j and w.contains(v)])==len(parents)+1]
            shells.append(Polygon(r.exterior.coords,holes))
        geom=MultiPolygon(shells) if len(shells)>1 else shells[0]
        gem=a.get('Gemarkung')
        zae,nen=number(a.get('Zähler')),number(a.get('Nenner'))
        flur=number(a.get('Flurnummer'))
        data={'gemarkung':gem if gem and not str(gem).isnumeric() else None,
              'gemarkungsschluessel':key[:6],'gemarkungsnummer':key[2:6],
              'flur':flur if flur!='0' else None,
              'flur_status':'vorhanden' if flur and flur!='0' else 'im_Datensatz_nicht_gefuehrt',
              'flurstueck':zae+('/'+nen if nen and nen!='0' else ''),'zaehler':zae,'nenner':nen if nen!='0' else None,
              'flurstueckskennzeichen':key,'amtliche_flaeche_m2':a.get('Amtliche_Fläche__m__'),
              'objektstand':a.get('Aktualität'),'datenquelle':'Esri_Deutschland_harmonisierte_ALKIS_Kopie'}
        parcels.append(Parcel(data,geom))
    return parcels


def select_parcels(parcels,x,y):
    # Exact intersection for straight rings; circular arcs are densified to <=1 mm.
    # No nearest-neighbour guess.
    point=Point(x,y)
    return [p for p in parcels if p.geometry.covers(point)]


def wms_image(client,state,bbox,width_m):
    p=PROVIDERS[state]
    root,_=client.xml(p.get('wms_capabilities',p['wms']),dict(SERVICE='WMS',REQUEST='GetCapabilities'),ttl=86400)
    all_layers={text(e,'Name'):e for e in root.iter() if local(e.tag)=='Layer' and text(e,'Name')}
    if not all(l in all_layers for l in p['layers']):
        raise ServiceError('WMS_LAYER_MISSING','Konfigurierte Kartenebene ist im Landesdienst nicht verfügbar.')
    version=root.get('version','1.3.0')
    # A 60 m extent must not be enlarged to satisfy a minimum display scale.
    # Request fewer pixels, then resize the same metric extent if necessary.
    min_scale=p.get('min_scale',0)
    for l in p['layers']:
        v=text(all_layers[l],'MinScaleDenominator')
        if v:min_scale=max(min_scale,float(v))
    rw=min(1600,max(80,int(width_m/(min_scale*0.00028)))) if min_scale else 1600
    rh=round(rw*0.75)
    params=dict(SERVICE='WMS',VERSION=version,REQUEST='GetMap',LAYERS=','.join(p['layers']),STYLES='',
                BBOX=','.join(map(str,bbox)),WIDTH=rw,HEIGHT=rh,FORMAT='image/png',TRANSPARENT='FALSE')
    params['CRS' if version.startswith('1.3') else 'SRS']=f"EPSG:{p['epsg']}"
    raw=client.get(p['wms'],params)
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ServiceError('WMS_NOT_IMAGE','Der Kartendienst lieferte kein PNG.',raw[:1000].decode(errors='replace'))
    img=Image.open(io.BytesIO(raw)).convert('RGB')
    if img.size!=(rw,rh):raise ServiceError('WMS_WRONG_DIMENSIONS','Unerwartete Bildabmessungen.')
    if all(lo==hi for lo,hi in img.getextrema()):
        raise ServiceError('WMS_EMPTY','Leeres Kartenbild; Maßstabsbereich oder Dienst prüfen.')
    if img.size!=(1600,1200):img=img.resize((1600,1200),Image.Resampling.LANCZOS)
    return img,{'typ':'amtlicher_WMS','url':url_with(p['wms'],params),'angeforderte_pixel':[rw,rh],
                'inhalt':'reduzierte_Parzellarkarte_ohne_Flurstuecksnummern' if state=='BY' else 'Katasterdarstellung_des_Landesdienstes'}


def font(size):
    for name in ('Arial.ttf','DejaVuSans.ttf','/System/Library/Fonts/Supplemental/Arial.ttf'):
        try:return ImageFont.truetype(name,size)
        except OSError:pass
    return ImageFont.load_default(size=size)


def draw_parcels(parcels,bbox):
    img=Image.new('RGB',(1600,1200),'white');d=ImageDraw.Draw(img)
    x0,y0,x1,y1=bbox
    def xy(pt):return ((pt[0]-x0)/(x1-x0)*1600,(y1-pt[1])/(y1-y0)*1200)
    window=Polygon([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])
    for parcel in parcels:
        clipped=parcel.geometry.intersection(window)
        polys=list(clipped.geoms) if clipped.geom_type in ('MultiPolygon','GeometryCollection') else [clipped]
        for poly in polys:
            if poly.geom_type!='Polygon' or poly.is_empty:continue
            d.polygon([xy(p) for p in poly.exterior.coords],fill='#fff0e3',outline='#292929',width=3)
            for ring in poly.interiors:d.polygon([xy(p) for p in ring.coords],fill='white',outline='#292929',width=3)
            pt=poly.representative_point()
            d.text(xy((pt.x,pt.y)),parcel.data['flurstueck'],font=font(25),fill='#222222',anchor='mm')
    return img


def save_image(img,path,address,state,width_m,image_info,esri_used=False):
    # Footer lies outside the 60 x 45 m geographic map, preserving its extent.
    out=Image.new('RGB',(1600,1310 if esri_used else 1280),'white');out.paste(img,(0,0));d=ImageDraw.Draw(out)
    d.line((0,1200,1600,1200),fill='#cccccc',width=2)
    caption=f"{PROVIDERS[state]['name']} | Ausschnitt {width_m:g} × {width_m*0.75:g} m | "+('Flurstücksskizze (ohne Gebäude)' if image_info['typ']=='Flurstuecksskizze' else 'Katasterkarte')
    d.text((22,1212),caption,font=font(21),fill='#333333')
    d.text((22,1244),PROVIDERS[state]['attribution'],font=font(16),fill='#444444')
    if esri_used:d.text((22,1271),'Flurstücksdaten: Esri Deutschland / ALKIS der Länder [Daten geändert]; vollständiger Quellenvermerk im JSON.',font=font(16),fill='#444444')
    info=PngImagePlugin.PngInfo();info.add_text('Description',caption);info.add_text('Source',image_info.get('url','amtliche Flurstücksgeometrien'))
    info.add_text('Attribution',PROVIDERS[state]['attribution']+'; '+OSM_CREDIT+('; '+ESRI_CREDIT if esri_used else ''))
    out.save(path,pnginfo=info)


def extract(address,output_dir,width_m=60,*,allow_fallback=True,client=None,location=None):
    if not isinstance(width_m,(int,float)) or not math.isfinite(width_m) or not 10<=width_m<=1000:
        raise ServiceError('INVALID_WIDTH','Breite muss zwischen 10 und 1000 Metern liegen.')
    dest=Path(output_dir);dest.mkdir(parents=True,exist_ok=True)
    client=client or Client(dest/'.cache')
    location=location or geocode(client,address)
    state=location['bundesland'];p=PROVIDERS[state]
    x,y=Transformer.from_crs(4326,p['epsg'],always_xy=True).transform(location['lon'],location['lat'])
    bbox=(x-width_m/2,y-width_m*0.375,x+width_m/2,y+width_m*0.375)
    warnings=[];all_parcels=[];selected=[];esri_used=False
    parcel_status='ok'
    by_auth = bool(os.environ.get('KATASTER_BY_USER') and os.environ.get('KATASTER_BY_PASSWORD'))
    if state=='BY' and not by_auth:
        parcel_status='zugang_erforderlich'
        warnings.append(p['hinweis'])
    else:
        try:
            all_parcels=wfs_features(client,state,(x-0.1,y-0.1,x+0.1,y+0.1))
            selected=select_parcels(all_parcels,x,y)
            if not selected:raise ServiceError('NO_PARCEL_AT_POINT','Kein Flurstück enthält den Adresspunkt.')
            for parcel in selected:
                try:enrich_name(client,state,parcel)
                except ServiceError as e:warnings.append('Gemarkungsname konnte nicht ergänzt werden: '+str(e))
        except ServiceError as e:
            warnings.append('Landesdienst: '+str(e))
            if allow_fallback:
                try:
                    all_parcels=esri_features(client,state,(x,y),point=True);selected=select_parcels(all_parcels,x,y)
                    esri_used=True
                    warnings.append('Ersatzquelle verwendet: harmonisierte ALKIS-Kopie von Esri Deutschland; kann gegenüber dem Landesdienst veraltet sein.')
                except ServiceError as fallback_error:warnings.append('Ersatzquelle: '+str(fallback_error))
            if not selected:parcel_status='nicht_verfuegbar'
    candidates=location.get('weitere_adresspunkte',[])
    if candidates:
        trans=Transformer.from_crs(4326,p['epsg'],always_xy=True)
        if len(selected)!=1 or not all(selected[0].geometry.covers(Point(*trans.transform(*pt))) for pt in candidates):
            raise ServiceError('ADDRESS_AMBIGUOUS','Mehrere Adresspunkte liegen nicht eindeutig auf demselben Flurstück. Adresse präzisieren.',location)
        warnings.append('Mehrere OSM-Adressobjekte wurden räumlich geprüft: alle liegen auf demselben Flurstück.')
    if len(selected)==1 and selected[0].geometry.boundary.distance(Point(x,y))<0.01:
        parcel_status='grenznah'
        warnings.append('Adresspunkt liegt innerhalb von 1 cm an einer Flurstücksgrenze. Zuordnung prüfen.')
    if len(selected)>1:
        parcel_status='mehrdeutig'
        warnings.append('Mehrere Flurstücke überlagern den Adresspunkt. Keine automatische Auswahl.')
    for parcel in selected:
        if not parcel.data['gemarkung']:
            warnings.append('Gemarkungsname fehlt; der amtliche Gemarkungsschlüssel ist vorhanden.')
    image_path=dest/'karte.png'
    try:
        img,image_info=wms_image(client,state,bbox,width_m)
        image_status='ok'
    except ServiceError as e:
        warnings.append('Kartenbild: '+str(e))
        img=None;image_info={'typ':'nicht_verfuegbar'};image_status='nicht_verfuegbar'
        if state!='BY' and selected:
            try:
                surrounding=esri_features(client,state,bbox) if esri_used else wfs_features(client,state,bbox)
                if surrounding:
                    img=draw_parcels(surrounding,bbox)
                    image_info={'typ':'Flurstuecksskizze','inhalt':'Flurstücksgrenzen und Nummern; keine Gebäude oder vollständige Katasterkartografie'}
                    image_status='ersatzdarstellung'
            except ServiceError as e:warnings.append('Ersatzdarstellung: '+str(e))
    if img is not None:save_image(img,image_path,location['gefunden'],state,width_m,image_info,esri_used)
    complete=parcel_status=='ok' and image_status=='ok' and all(q.data['gemarkung'] for q in selected)
    result={'status':'ok' if complete else 'teilweise','adresse':location,
            'grundstueck_status':parcel_status,'grundstuecke':[q.data for q in selected],
            'bild':{'status':image_status,'datei':'karte.png' if img is not None else None,
                    'breite_meter':width_m,'hoehe_meter':width_m*0.75,'kartenbereich_pixel':[0,0,1600,1200],
                    'gesamtgroesse_pixel':[1600,1340] if img is not None else None,
                    'crs':f"EPSG:{p['epsg']}",'bbox':bbox,**image_info},
            'hinweise':list(dict.fromkeys(warnings+['Ein Adresspunkt ermittelt das ihn enthaltende Flurstück. Weitere zugehörige Grundstücksteile oder Eigentumseinheiten sind damit nicht ermittelt.',
                        'Kartenbild und JSON sind kein förmlicher amtlicher Katasterauszug.',
                        'GML-Kreisbögen werden für die Punktprüfung mit maximal 1 mm Sehnenfehler angenähert.'])),
            'quellenvermerk':[p['attribution'],OSM_CREDIT]+([ESRI_CREDIT] if esri_used else []),
            'abgerufen_am':datetime.now(timezone.utc).isoformat(),'lizenzangaben_der_dienste':getattr(client,'licenses',[]),'abrufnachweise':client.records}
    (dest/'grundstueck.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
