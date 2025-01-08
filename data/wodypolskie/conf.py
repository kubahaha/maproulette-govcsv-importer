import re
from src.utils import strip_number, force_https, getaddr


prepare = {
    "accept": lambda x: True,
    "separator": ',',
    "tags": {
        "__lat": "Y",
        "__lon": "X",
        'name': "Name",
        'addr:postcode': 'kod',
        'phone': lambda x: strip_number(x.get('telefon'), format='2322'),
        'email': 'email',
        'short_name': lambda x: make_short_name(x.get('Name'))
    }
}

matching = [
    ['name'],
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    "location:200",
    ['addr:place', 'addr:postcode'],
    ['addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:city', 'addr:postcode']
]

tags_to_delete = {
    'amenity': '*'
}

tags_to_add = {
    'office': 'government',
    'operator':'Państwowe Gospodarstwo Wodne Wody Polskie',
    'government': 'water'
}

tags_source = {
    'source:office': 'Państwowe Gospodarstwo Wodne Wody Polskie - dane kontaktowe na dzień 27.11.2024'
}

tags_to_replace = {'website': lambda url: force_https(url, True, True)}

rules = {
    'update_addr': False,
    'download_latlon': False
}


def make_short_name(name):
    match = re.match(r'Regionalny Zarząd Gospodarki Wodnej (?P<LACZNIK>we?) (?P<CITY>.+)', name)

    if not match:
        return ''
    
    data = match.groupdict()
    return f'RZGW {data.get("LACZNIK")} {data.get("CITY")}'
