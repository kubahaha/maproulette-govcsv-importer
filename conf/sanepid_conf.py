from src.Comparator import Comparator
from src.utils import getopening, getoperator, getaddr, strip_number, getnames
import re

static = {
    'project_name': 'sanepid'
}

fieldnames_after_mod = ['name', 'phone', 'email', 'fax', 'website', 'official_name']

#########

comparision = {
    'official_name': Comparator('NAZWA', 'official_name', single_match=True, print=lambda x: getnames['sanepid'](x).get('official_name') or getnames['sanepid'](x).get('name') or '', strip=lambda x: x.lower().strip()),
    'addr:street': Comparator('ULICA', 'addr:street', strip=lambda x: x.lower().replace('aleja', '').replace('al.', '').replace('plac', '').replace('pl.', '').replace('św.', '').strip()),
    'addr:housenumber': Comparator('NRDOMU', 'addr:housenumber', strip=lambda x: x.strip()),
    'addr:city': Comparator('MIEJSCOWOŚĆ', 'addr:city', print=lambda x: x.capitalize().strip(), strip=lambda x: x.lower().strip()),
    'addr:place': Comparator('MIEJSCOWOŚĆ', 'addr:place', print=lambda x: x.capitalize().strip(), strip=lambda x: x.lower().strip()),
    'addr:postcode': Comparator('KOD POCZTOWY', 'addr:postcode', strip=lambda x: x.strip()),
    'phone': Comparator('NRTEL', 'phone', single_match=True, print=lambda x: strip_number(x), strip=lambda x: strip_number(x)),
    'fax': Comparator('NRFAX', 'fax', single_match=True, print=lambda x: strip_number(x), strip=lambda x: strip_number(x)),
    'email': Comparator('EMAIL', 'email', single_match=True, print=lambda x: x.lower().strip(), strip=lambda x: x.lower().strip()),
    'website': Comparator('WWW', 'website', single_match=True, print=lambda x: x.lower().replace('&', '&amp;').strip(), strip=lambda x: x.lower().replace('https://', '').replace('http://', '').replace('/', '').strip())
}

##########

tags_to_add = {
    'source:office': 'Baza teleadresowa administracji zespolonej według stanu na 16.08.2021',
    'office': 'government',
    'government': 'healthcare'
}
tags_to_generate = {
    'official_name': lambda row: getnames['sanepid'](row['NAZWA']).get('official_name'),
    'short_name': lambda row: getnames['sanepid'](row['NAZWA']).get('short_name'),
    'name': lambda row: getnames['sanepid'](row['NAZWA']).get('name')
    # 'amenity': {
    #     'kindergarten': lambda row: row.get('Typ instytucji') == 'Żłobek',
    #     'childcare': lambda row: row.get('Typ instytucji') != 'Żłobek'
    # },
    # 'operator:type': lambda row: getoperator(row.get('Nazwa') or '', row.get('operator') or '')
}
tags_to_delete = {'addr:city:simc', 'full_name', 'source'}
tags_to_cond_delete = {
    # 'operator:website': lambda row: row.get('website') != row.get('operator:website')
}
