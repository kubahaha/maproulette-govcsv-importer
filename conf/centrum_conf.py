from src.Comparator import Comparator
from src.utils import getopening, getoperator, getaddr, strip_number, getnames
import re

static = {
    'project_name': 'centrum'
}

fieldnames_after_mod = ['name', 'brand', 'brand:wikidata']

#########

comparision = {
    'addr:housenumber': Comparator('Adres Sklepu', 'addr:housenumber',
        left_strip=lambda x: getaddr(x, place=True, street=True, housenumber=True).get('housenumber'),
        left_print=lambda x: getaddr(x, place=True, street=True, housenumber=True).get('housenumber')
    ),
    'addr:street': Comparator('Adres Sklepu', 'addr:street',
        left_strip=lambda x: getaddr(x, place=True, street=True, housenumber=True).get('street'),
        left_print=lambda x: getaddr(x, place=True, street=True, housenumber=True).get('street')
    ),
    'addr:place': Comparator('Adres Sklepu', 'addr:place',
        left_strip=lambda x: getaddr(x, place=True, street=True, housenumber=True).get('place'),
        left_print=lambda x: getaddr(x, place=True, street=True, housenumber=True).get('place')
    ),
    'addr:city': Comparator('Miejscowość', 'addr:city',
        strip=lambda x: x.lower().strip(),
        print=lambda x: x.capitalize().strip()
    ),
    'addr:postcode': Comparator('Kod pocztowy sklepu', 'addr:postcode')}

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
