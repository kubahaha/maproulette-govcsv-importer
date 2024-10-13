from src.utils import force_https
import re


def get_housennumber(address):
    nr = address.split(' ')[-1]
    if re.match(r'\d+', nr):
        return nr


def get_street(row):
    street = ' '.join(row.get('ADRES').split(' ')[:-1]).title()
    city = row.get('MIEJSCOWOŚĆ').title()

    if city != street:
        return street


prepare = {
    "accept": lambda x: x.get('RODZAJ PODMIOTU') == 'STACJA PALIW',
    "separator": ';',
    "tags": {
        'operator': lambda x: x.get('NAZWA').title(),
        'addr:housenumber': lambda it: get_housennumber(it.get('ADRES')),
        'addr:street': get_street,
        'addr:city': lambda it: it.get('MIEJSCOWOŚĆ').title() if get_street(it) else '',
        'addr:place': lambda it: it.get('MIEJSCOWOŚĆ') if not get_street(it) else '',
        'addr:postcode': 'KOD POCZTOWY',
        'fuel:octane_95': {
            'RON95': {'X': 'yes'}
        },
        'fuel:octane_98': {
            'RON98': {'X': 'yes'}
        },
        'fuel:diesel': {
            'ON': {'X': 'yes'}
        },
        'fuel:lpg': {
            'LPG': {'X': 'yes'}
        },
        'fuel:CNG': {
            'CNG': {'X': 'yes'}
        }
    }
}

matching = [
    ['official_name'],
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    # "location:300",
    ['addr:place', 'addr:postcode'],
    ['addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:city', 'addr:postcode']
]

tags_to_delete = {}

tags_to_add = {'amenity': 'fuel'}

tags_source = {'source:amenity': 'Wykaz stacji paliwowych na dzień 15.03.2024'}

tags_to_replace = {'website': lambda url: force_https(url, True, True)}

rules = {
    'update_addr': False,
    'download_latlon': True
}
