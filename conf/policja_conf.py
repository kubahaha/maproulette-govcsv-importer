from src.Comparator import Comparator
from src.utils import getopening, getoperator, getaddr, strip_number, getnames
import re

prepare = {
    "accept": lambda x: re.match(r".*policj.*", x.get('NAZWA URZĘDU'), flags=re.IGNORECASE),
    "separator": ';',
    "tags": {
        '__lat': 'DŁUGOŚĆ GEOGRAFICZNA',
        '__lon': 'SZEROKOŚĆ GEOGRAFICZNA',           
        'addr:postcode': 'KOD POCZTOWY',
        'addr:city': lambda it: it.get('MIEJSCOWOŚĆ') if it.get('ULICA') else '',
        'addr:place': lambda it: it.get('MIEJSCOWOŚĆ') if not it.get('ULICA') else '',
        'addr:street': 'ULICA',
        'addr:housenumber': 'NR DOMU',
        'email': 'ADRES E-MAIL URZĘDU',
        'fax': lambda x: strip_number(x.get('NR FAXU        wraz z nr kierunkowym')),
        'name': lambda x: x.get('NAZWA URZĘDU').split(' w ')[0].strip(),
        'official_name': lambda x: x.get('NAZWA URZĘDU').strip(),
        'phone': lambda x: strip_number(x.get('NR TELEFONU wraz z nr kierunkowym')),
        'website': 'ADRES WWW URZĘDU'
    }
}

static = {
    'project_name': 'policja'
}

search = {
    'street': lambda row: row.get('Adres Sklepu').replace('Ul. ', '').replace('Al. ', ''),
    'city': lambda row: row.get('Miejscowość'),
    'country': lambda _: 'Polska',
    'postalcode': lambda row: row.get('Kod pocztowy sklepu')
}
 
gov_fieldnames = [
    # ('Adres sklepu', 'name', lambda x: getnames['pinb'](x)['name'].strip()),
    # ('Miejscowość', 'name', lambda x: x.strip()),
    # ('Kod pocztowy sklepu', 'phone', lambda x: strip_number(x)),
    # ('NRFAX', 'fax', lambda x: strip_number(x)),
    # ('EMAIL', 'email', lambda x: x.lower().strip()),
    # ('WWW', 'website', lambda x : x.lower().strip())
]
tags_to_add = {
    'name': 'Delikatesy Centrum',
    'brand': 'Delikatesy Centrum',
    'source': 'https://c.osm.org/t/99385',
    'shop': 'supermarket'
}
tags_to_generate = {
    # 'official_name': lambda row: getnames['pinb'](row['NAZWA']).get('official_name'),
    # 'short_name': lambda row: getnames['pinb'](row['NAZWA']).get('short_name'),
    # 'name': lambda row: getnames['pinb'](row['NAZWA']).get('name')
    # 'amenity': {
    #     'kindergarten': lambda row: row.get('Typ instytucji') == 'Żłobek',
    #     'childcare': lambda row: row.get('Typ instytucji') != 'Żłobek'
    # },
    # 'operator:type': lambda row: getoperator(row.get('Nazwa') or '', row.get('operator') or '')
}
tags_to_delete = {'source', 'name:pl', 'name:en'}
tags_to_cond_delete = {
    # 'operator:website': lambda row: row.get('website') != row.get('operator:website')
}
matching = [
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    ['addr:place', 'addr:postcode'],
    "location:300"
]