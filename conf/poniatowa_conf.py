from src.Comparator import Comparator
from src.utils import getopening, getoperator, getaddr, strip_number, getnames
import re

static = {
    'project_name': 'poniatowa'
}

fieldnames_after_mod = ['name', 'phone', 'email', 'fax', 'website', 'official_name']

#########

comparision = {
    'official_name': Comparator('official_name', 'official_name', single_match=True, print=lambda x: x.strip(), strip=lambda x: x.lower().strip()),
    'name': Comparator('name', 'name', single_match=True, strip=lambda x: x.lower().strip()),
    'addr:street': Comparator('addr:street', 'addr:street', strip=lambda x: x.lower().replace('aleja', '').replace('al.', '').replace('plac', '').replace('pl.', '').replace('św.', '').strip()),
    'addr:housenumber': Comparator('addr:housenumber', 'addr:housenumber', strip=lambda x: x.strip()),
    'addr:city': Comparator('addr:city', 'addr:city', print=lambda x: x.capitalize().strip(), strip=lambda x: x.lower().strip()),
    'addr:place': Comparator('addr:place', 'addr:place', print=lambda x: x.capitalize().strip(), strip=lambda x: x.lower().strip()),
    'addr:postcode': Comparator('addr:postcode', 'addr:postcode', strip=lambda x: x.strip()),
    'phone': Comparator('phone', 'phone', single_match=True, print=lambda x: strip_number(x), strip=lambda x: strip_number(x)),
    'email': Comparator('email', 'email', single_match=True, print=lambda x: x.lower().strip(), strip=lambda x: x.lower().strip()),
    'website': Comparator('website', 'website', single_match=True, print=lambda x: x.lower().replace('&', '&amp;').strip(), strip=lambda x: x.lower().replace('https://', '').replace('http://', '').replace('/', '').strip())
}

##########

tags_to_add = {}
tags_to_generate = {
    'isced:level': lambda row: row['isced:level'],
    'ref:rspo': lambda row: row['ref:rspo'],
    'ref:regon': lambda row: row['ref:regon'],
    'ref:vatin': lambda row: row['ref:vatin'],
    'operator': lambda row: row['operator'],
    'operator:type': lambda row: row['operator:type'],
    'amenity': lambda row: row['amenity'],
    'landuse': lambda row: row['landuse'],
    'fixme': lambda row: row['fixme'],
    'note': lambda row: row['note'],
    'community_centre:for': lambda row: row['community_centre:for'],
    'healthcare,': lambda row: row['healthcare'],
    'counselling_type': lambda row: row['counselling_type']
}
tags_to_delete = {'addr:city:simc', 'full_name', 'source'}
tags_to_cond_delete = {
    'official_name': lambda row: row.get('name') != row.get('official_name')
}
