import re
from src.utils import strip_number, force_https, parse_address


def social_facility_for(text):
    if 'podeszły' in text:
        return 'senior'
    if 'intelektualn' in text or 'psychicznie' in text:
        return 'mental_health'
    if 'somatyczn' in text:
        return 'diseased'
    if 'Stwardnienie Rozsiane' in text:
        return 'diseased'
    raise NotImplementedError(text)


def start_date(line):
    match = re.match(r'.+ z (?P<DAY>\d{1,2})\.(?P<MONTH>\d{1,2})\.(?P<YEAR>\d{4}) r\..+', line)
    try:
        data = match.groupdict()
    except AttributeError:
        print(f'ERROR! {line}')
        raise
    return f"{data.get('YEAR')}-{('0' + data.get('MONTH'))[-2:]}-{('0' + data.get('DAY'))[-2:]}"


prepare = {
    "accept": lambda x: x.get('TYP') != 'KSS',
    "separator": ',',
    "tags": {
        'social_facility:for': lambda x: social_facility_for(x.get('Typ domu pomocy społecznej')),
        'operator': 'Podmiot prowadzący',
        'capacity': 'Liczba miejsc przeznaczona dla mieszkańców domu pomocy społecznej',
        'name': lambda x: x.get('Nazwa domu pomocy społecznej').split(' w ')[0].strip().split(' we ')[0].strip(),
        'addr:city': lambda it: parse_address(it.get('Adres')).get('addr:city'),
        'addr:postcode': lambda it: parse_address(it.get('Adres')).get('addr:postcode'),
        'addr:place': lambda it: parse_address(it.get('Adres')).get('addr:place'),
        'addr:street': lambda it: parse_address(it.get('Adres')).get('addr:street'),
        'addr:housenumber': lambda it: parse_address(it.get('Adres')).get('addr:housenumber'),
        'phone': lambda x: strip_number(x.get('telefon', '').split(';')[0], format='2322'),
        'start_date': lambda x: start_date(x.get('decyzja', ''))
    }
}

matching = [
    ['official_name'],
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    "location:300",
    ['addr:place', 'addr:postcode'],
    ['addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:city', 'addr:postcode']
]

tags_to_delete = {}

tags_to_add = {
    'amenity': 'social_facility',
    "social_facility": "nursing_home"
}

tags_source = {'source:amenity': 'Rejestr domów pomocy społecznej województwa mazowieckiego stan na 10 maja 2024 r.'}

tags_to_replace = {'website': lambda url: force_https(url, True, True)}

rules = {
    'update_addr': False,
    'download_latlon': True
}
