from src.Comparator import Comparator
from src.utils import getopening, getoperator, getaddr, strip_number, getnames
import re

static = {
    'project_name': 'pinb'
}

fieldnames_after_mod = ['name', 'phone', 'email', 'fax', 'website', 'official_name']

#########

comparision = {
    'official_name': Comparator('NAZWA', 'official_name', single_match=True, print=lambda x: getnames['pinb'](x).get('official_name') or getnames['pinb'](x)['name'], strip=lambda x: x.lower().strip()),
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

gov_fieldnames = [
    ('NAZWA', 'name', lambda x: getnames['pinb'](x)['name'].strip()),
    ('KOD POCZTOWY', 'name', lambda x: x.strip()),
    ('NRTEL', 'phone', lambda x: strip_number(x)),
    ('NRFAX', 'fax', lambda x: strip_number(x)),
    ('EMAIL', 'email', lambda x: x.lower().strip()),
    ('WWW', 'website', lambda x : x.lower().strip())
]
tags_to_add = {
    'source:office': 'Baza teleadresowa administracji zespolonej według stanu na 16.08.2021',
    'office': 'government',
    'government': 'building_control'
}
tags_to_generate = {
    'official_name': lambda row: getnames['pinb'](row['NAZWA']).get('official_name'),
    'short_name': lambda row: getnames['pinb'](row['NAZWA']).get('short_name'),
    'name': lambda row: getnames['pinb'](row['NAZWA']).get('name')
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



#DEL
amenity:wikipedia



#CHANGE
access
alt_name
amenity
authentication
authentication:none
authentication:membership_card
authentication:app
authentication:nfc
authentication:phone_call
authentication:short_message


brand
brand:website
brand:wikidata
brand:wikipedia
capacity
check_date
phone
website
email
fee
name
network
official_name
opening_hours
operator:wikidata
operator:wikipedia
operator
output
payment:Greenway_RfiD_card
payment:account_cards
payment:app
payment:cards
payment:cash
payment:contactless
payment:credit_cards
payment:debit_cards
payment:e100
payment:electronic_purses
payment:mastercard
payment:visa
phone
power
ref
short_name
socket:ccs
socket:cee_red_16a
socket:cee_red_32a
socket:chademo:current
socket:chademo:output
socket:chademo
socket:device:USB-A
socket:output
socket:schuko
socket:tesla:output
socket:tesla
socket:tesla_destination
socket:tesla_standard
socket:tesla_supercharger:output
socket:tesla_supercharger
socket:tesla_supercharger_ccs:output
socket:tesla_supercharger_ccs
socket:threephase
socket:type1:output
socket:type1
socket:type1_combo
socket:type2:current
socket:type2:output
socket:type2:voltage
socket:type2
socket:type2_cable:output
socket:type2_cable
socket:type2_combo:current
socket:type2_combo:output
socket:type2_combo
socket:typee
socket
source
truck
website