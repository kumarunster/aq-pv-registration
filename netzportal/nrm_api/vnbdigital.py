"""Read-only VNBdigital address lookup, using the observed public website queries."""
from datetime import datetime, timezone
import re
import unicodedata
from urllib.parse import urlsplit, parse_qs

import httpx
from .drafts import Site
from .errors import PortalError

ENDPOINT = 'https://www.vnbdigital.de/gateway/graphql'
SEARCH = '''query ($searchTerm: String!) {
  vnb_search(searchTerm: $searchTerm) { _id title subtitle url type }
}'''
OPERATORS = '''query ($coordinates: String, $filter: vnb_FilterInput) {
  vnb_coordinates(coordinates: $coordinates) {
    vnbs(filter: $filter) { _id name types voltageTypes }
  }
}'''
# IDs verified against VNBdigital on 4 November 2026. Never fuzzy-match companies.
PROVIDERS = {'7376': 'nrm', '350': 'enm', '405': 'mainzer', '134': 'enetz'}


class LookupUnavailable(PortalError):
    code = 'vnbdigital_unavailable'
    message = 'VNBdigital lookup is unavailable or returned an unexpected response.'
    status_code = 503


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().replace('ß', 'ss').split())


class VNBDigitalClient:
    def __init__(self, transport=None):
        self.transport = transport

    @staticmethod
    def query(client, query, variables, field):
        try:
            r = client.post(ENDPOINT, json={'query': query, 'variables': variables})
            r.raise_for_status()
            body = r.json()
            if body.get('errors') or not isinstance(body.get('data'), dict) or field not in body['data']:
                raise LookupUnavailable()
            return body['data'][field]
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            raise LookupUnavailable() from None

    def resolve(self, site: Site):
        term = f'{site.street} {site.house_number}, {site.postal_code} {site.city}'
        result = {'source': 'https://www.vnbdigital.de/', 'queried_at': datetime.now(timezone.utc).isoformat(),
                  'address': site.model_dump(), 'voltage_level': 'Niederspannung',
                  'status': 'not_found', 'operator': None, 'provider': None, 'candidates': []}
        with httpx.Client(timeout=20, transport=self.transport, follow_redirects=False, trust_env=False) as client:
            items = self.query(client, SEARCH, {'searchTerm': term}, 'vnb_search')
            if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
                raise LookupUnavailable()
            matches = []
            for item in items:
                if item.get('type') != 'LOCATION':
                    continue
                title = item.get('title') or ''
                # Only house-level matches; a postcode, street or company hit is insufficient.
                street, separator, locality = title.partition(',')
                if (not separator or normalize(street) != normalize(f'{site.street} {site.house_number}')
                        or not re.search(rf'(?<!\d){re.escape(site.postal_code)}(?!\d)', locality)
                        or not re.search(r'(?<!\w)' + re.escape(normalize(site.city)) + r'(?!\w)', normalize(locality))):
                    continue
                url = urlsplit(item.get('url') or '')
                if url.scheme or url.netloc or url.path != '/overview':
                    continue
                coordinates = parse_qs(url.query).get('coordinates', [''])[0]
                if not re.fullmatch(r'-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?', coordinates):
                    continue
                lat, lon = map(float, coordinates.split(','))
                if not (47 <= lat <= 56 and 5 <= lon <= 16):
                    continue
                if not any(m['coordinates'] == coordinates for m in matches):
                    matches.append({'title': title, 'coordinates': coordinates})
            if not matches:
                return result
            if len(matches) != 1:
                return {**result, 'status': 'ambiguous_address', 'candidates': matches}
            location = matches[0]
            area = self.query(client, OPERATORS, {'coordinates': location['coordinates'],
                              'filter': {'voltageTypes': ['Niederspannung']}}, 'vnb_coordinates')
            if not isinstance(area, dict) or not isinstance(area.get('vnbs'), list):
                raise LookupUnavailable()
            operators = {}
            for operator in area['vnbs']:
                if (not isinstance(operator, dict) or not operator.get('_id') or not operator.get('name')
                        or not isinstance(operator.get('voltageTypes'), list)):
                    raise LookupUnavailable()
                if 'Niederspannung' in operator['voltageTypes']:
                    identity = str(operator['_id'])
                    operators[identity] = {'id': identity, 'name': operator['name'],
                                           'url': f'https://www.vnbdigital.de/vnb/{identity}'}
            result['location'] = location
            if not operators:
                return result
            if len(operators) != 1:
                return {**result, 'status': 'ambiguous_operator', 'candidates': list(operators.values())}
            operator = next(iter(operators.values()))
            provider = PROVIDERS.get(operator['id'])
            return {**result, 'status': 'resolved' if provider else 'unsupported',
                    'operator': operator, 'provider': provider}
