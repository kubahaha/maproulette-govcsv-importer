from src.Comparator import Comparator
from src.utils import getopening, getoperator, getaddr, strip_number, getnames
import re

static = {
    'project_name': 'centrum'
}

fieldnames_after_mod = ['name', 'brand', 'brand:wikidata', 'addr:street', 'addr:place', 'addr:city', 'addr:postcode', 'addr:housenumber']

#########

comparision = {
    'addr:housenumber': Comparator('Adres sklepu', 'addr:housenumber', strip=lambda x: getaddr(x).get('housenumber')),
    'addr:street': Comparator('Adres sklepu', 'addr:street', strip=lambda x: getaddr(x).get('street')),
    'addr:place': Comparator('Adres sklepu', 'addr:place', strip=lambda x: getaddr(x).get('place', True)),
    'addr:city': Comparator('Miejscowość', 'addr:city', print=lambda x: x.capitalize().strip(), strip=lambda x: x.lower().strip()),
    'addr:place': Comparator('Miejscowość', 'addr:place', print=lambda x: x.capitalize().strip(), strip=lambda x: x.lower().strip()),
    'addr:postcode': Comparator('Kod pocztowy sklepu', 'addr:postcode', strip=lambda x: x.strip())
}

##########

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
