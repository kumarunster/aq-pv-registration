import json
import httpx
import pytest
from fastapi.testclient import TestClient
from nrm_api.app import create_app
from nrm_api.config import Settings
from nrm_api.drafts import Site
from nrm_api.vnbdigital import VNBDigitalClient, LookupUnavailable

SITE = Site(street='Kurt-Schumacher-Straße',house_number='8',postal_code='60311',city='Frankfurt am Main')
LOCATION = {'type':'LOCATION','title':'Kurt-Schumacher-Straße 8, 60311 Frankfurt am Main - Innenstadt',
            'url':'/overview?coordinates=50.110931,8.688347&searchType=LOCATION'}
OPERATOR = {'_id':'7376','name':'NRM Netzdienste Rhein-Main GmbH','voltageTypes':['Niederspannung']}

def resolver(locations=None,operators=None):
    calls=[]
    def handle(r):
        assert str(r.url)=='https://www.vnbdigital.de/gateway/graphql'
        assert 'authorization' not in r.headers
        body=json.loads(r.content);calls.append(body)
        assert r.method=='POST' and 'mutation' not in body['query']
        if 'vnb_search' in body['query']:
            assert body['variables']['searchTerm']=='Kurt-Schumacher-Straße 8, 60311 Frankfurt am Main'
            return httpx.Response(200,json={'data':{'vnb_search':[LOCATION] if locations is None else locations}})
        assert body['variables']=={'coordinates':'50.110931,8.688347','filter':{'voltageTypes':['Niederspannung']}}
        return httpx.Response(200,json={'data':{'vnb_coordinates':{'vnbs':[OPERATOR] if operators is None else operators}}})
    return VNBDigitalClient(httpx.MockTransport(handle)),calls

@pytest.mark.parametrize('identity,provider',[('7376','nrm'),('350','enm'),('405','mainzer'),('134','enetz')])
def test_supported_ids(identity,provider):
    client,calls=resolver(operators=[{**OPERATOR,'_id':identity}])
    data=client.resolve(SITE)
    assert data['status']=='resolved' and data['provider']==provider
    assert data['operator']['id']==identity and len(calls)==2
    assert data['source']=='https://www.vnbdigital.de/'

@pytest.mark.parametrize('item',[
    {**LOCATION,'type':'VNB'},
    {**LOCATION,'title':'Kurt-Schumacher-Straße, 60311 Frankfurt am Main'},
    {**LOCATION,'title':'Kurt-Schumacher-Straße 9, 60311 Frankfurt am Main'},
    {**LOCATION,'title':'Kurt-Schumacher-Straße 8, 60312 Frankfurt am Main'},
    {**LOCATION,'title':'Kurt-Schumacher-Straße 8, 60311 Anderer Ort'},
    {**LOCATION,'url':'https://evil.example/?coordinates=50.110931,8.688347'},
    {**LOCATION,'url':'/overview?coordinates=8.688347,50.110931'},
])
def test_inexact_or_unsafe_address_never_resolves(item):
    client,calls=resolver(locations=[item])
    assert client.resolve(SITE)['status']=='not_found'
    assert len(calls)==1

def test_multiple_locations_block():
    client,calls=resolver(locations=[LOCATION,{**LOCATION,'url':'/overview?coordinates=50.12,8.7'}])
    assert client.resolve(SITE)['status']=='ambiguous_address'
    assert len(calls)==1

def test_duplicate_location_is_not_ambiguous():
    client,_=resolver(locations=[LOCATION,LOCATION])
    assert client.resolve(SITE)['status']=='resolved'

def test_multiple_operators_block():
    client,_=resolver(operators=[OPERATOR,{**OPERATOR,'_id':'405'}])
    assert client.resolve(SITE)['status']=='ambiguous_operator'

def test_unknown_operator_not_fuzzy_matched():
    client,_=resolver(operators=[{**OPERATOR,'_id':'unknown'}])
    data=client.resolve(SITE)
    assert data['status']=='unsupported' and data['provider'] is None

@pytest.mark.parametrize('operators',[[],[{**OPERATOR,'voltageTypes':['Mittelspannung']}]])
def test_no_low_voltage_operator(operators):
    client,_=resolver(operators=operators)
    assert client.resolve(SITE)['status']=='not_found'

@pytest.mark.parametrize('response',[
    httpx.Response(500,text='private upstream error'),
    httpx.Response(200,json={'errors':[{'message':'secret'}]}),
    httpx.Response(200,json={'data':{'vnb_search':None}}),
    httpx.Response(200,text='invalid JSON'),
])
def test_upstream_errors_sanitized(response):
    client=VNBDigitalClient(httpx.MockTransport(lambda _:response))
    with pytest.raises(LookupUnavailable) as error:client.resolve(SITE)
    assert 'secret' not in error.value.message and 'private' not in error.value.message

def test_lookup_endpoint_requires_bearer(monkeypatch,tmp_path):
    settings=Settings('test-user','test-password','k'*40,draft_directory=str(tmp_path))
    called=[]
    monkeypatch.setattr(VNBDigitalClient,'resolve',lambda self,site:called.append(site) or {'status':'not_found'})
    with TestClient(create_app(settings)) as client:
        assert client.post('/api/v1/network-operators/resolve',json=SITE.model_dump()).status_code==401
        assert not called
        response=client.post('/api/v1/network-operators/resolve',json=SITE.model_dump(),headers={'Authorization':'Bearer '+'k'*40})
        assert response.status_code==200 and len(called)==1
