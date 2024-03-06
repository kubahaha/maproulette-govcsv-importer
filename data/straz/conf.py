import re
from src.utils import strip_number, force_https, getaddr, miejscownik


# https://dane.gov.pl/pl/dataset/1050/resource/36594/table
prepare = {
    "separator": ',',
    "tags": {
        'addr:city': 'Miejscowość',
        'addr:housenumber': lambda x: getaddr(x.get('Adres', ''), street=True, housenumber=True).get('addr:housenumber', ''),
        'addr:postcode': 'Kod pocztowy',
        'addr:street': lambda x: getaddr(x.get('Adres', ''), street=True, housenumber=True).get('addr:street', ''),
        'email': 'Służbowy adres e-mail',
        'fax': lambda x: strip_number(x.get('FAX'), format='2322'),
        'name': lambda x: make_name(x.get('Nazwa')),
        'official_name': lambda x: make_official_name(x.get('Nazwa')),
        'phone': lambda x: strip_number(x.get('Centrala'), format='2322'),
        'short_name': 'Nazwa',
        'website': 'Służbowa strona WWW'
    }
}

matching = [
    ['official_name'],
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:place'],
    ['addr:city'],
    ['addr:street', 'addr:city'],
    "location:400"
]

tags_to_delete = {
    'access': '*',
    'addr:country': '*',
    'addr:county': '*',
    'addr:housename': '*',
    'addr:state': '*',
    'alt_name': '*',
    'amenity': '*',
    'contact:email': '*',
    'contact:fax': '*',
    'contact:phone': '*',
    'contact:website': '*',
    'description': '*',
    'designation': '*',
    'name:pl': '*',
    'opening_hours:covid19': '*',
    'ref': '*',
    'source': '*',
    'source:amenity': '*',
    'survey:date': '*'
}

tags_to_add = {
    'office': 'government',
    'government': 'public_safety'
}

tags_source = {'source:office': 'Dane teleadresowe jednostek organizacyjnych Państwowej Straży Pożarnej według stanu na 16.02.2022'}

tags_to_replace = {'website': lambda url: force_https(url, True, True)}

rules = {
    'update_addr': False,
    'download_latlon': True
}


def make_name(short_name):
    name_d = short_name.split()
    prefix = {'KM': 'Komenda Miejska', 'KP': 'Komenda Powiatowa', 'KW': 'Komenda Wojewódzka', 'KG': 'Komenda Główna'}[name_d[0]]
    return f"{prefix} Państwowej Straży Pożarnej"


def make_official_name(short_name):
    name_d = short_name.split()
    prefix = {'KM': 'Komenda Miejska', 'KP': 'Komenda Powiatowa', 'KW': 'Komenda Wojewódzka', 'KG': 'Komenda Główna'}[name_d[0]]
    city = miejscownik(' '.join(name_d[2:]))

    e = 'e' if city[0] in ['F', 'W'] and city[1] not in ['a', 'e', 'i', 'y', 'o', 'u'] else ''

    return f"{prefix} Państwowej Straży Pożarnej w{e} {city}"
