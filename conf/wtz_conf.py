from src.Comparator import Comparator
from src.utils import getopening, getoperator, getaddr, strip_number, getnames
import re


def _get_housenumber(row):
    addr = {}
    if row.get('Ulica'):
        addr = getaddr(row.get('Ulica'), street=True, housenumber=True, door=True)
    else:
        addr = getaddr(row.get('Miejscowość'), place=True, housenumber=True, door=True)

    return addr.get('addr:housenumber')

def _getstartdate(row):
    if not row.get('Data utworzenia wtz'):
        return ''
    start = row.get('Data utworzenia wtz').split('-')
    if len(start) != 3:
        return ''
    
    if start[2][0] == '9':
        start[2] = f'19{start[2]}'
    else:
        start[2] = f'20{start[2]}'

    return f'{start[2]}-{start[0]}-{start[1]}'

def _postcode(row):
    postcode = ''.join(row.get('Kod').split('-'))
    return f'{postcode[0:2]}-{postcode[2:5]}'


prepare = {
    "tags": {
        'addr:postcode': _postcode,
        'addr:city': lambda it: it.get('Miejscowość') if it.get('Ulica') else '',
        'addr:place': lambda it: getaddr(it.get('Miejscowość'), place=True, housenumber=True, door=True).get('addr:place') if not it.get('Ulica') else '',
        'addr:street': lambda it: getaddr(it.get('Ulica'), street=True, housenumber=True, door=True).get('addr:street').split('/')[0] if it.get('Ulica') else '',
        'addr:housenumber': _get_housenumber,
        'name': 'Nazwa wtz',
        'operator': 'Organizator',
        'start_date': _getstartdate
    }
}

matching = [
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    ['addr:place', 'addr:postcode'],
    "location:300"
]

tags_to_delete = {
    'amenity': '*',
    'healthcare': '*',
    'office': '*',
    'social_facility': '*',
    'social_facility:for': '*'
}

tags_to_add = {
    'amenity': 'social_facility',
    'social_facility': 'workshop',
    'social_facility:for': 'mental_health',
    'source:amenity': 'Baza adresowa warsztatów terapii zajęciowej - wypis na dzień 19.09.2023'
}

overpass = """[out:xml][timeout:9999];
    {{geocodeArea: Polska;}}->.searchArea;

    (
        nw[amenity=social_facility](area.searchArea);
        nw[amenity=school](area.searchArea);
        nw[healthcare](area.searchArea);
        nw[office](area.searchArea);
        nw[amenity=community_centre](area.searchArea);
    ) -> .pois;
    nw.pois["name"~"Warsztaty? Terapii Zajęciowej", i];
    out meta;
    >;
    out meta;
    """