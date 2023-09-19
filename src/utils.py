from audioop import add
import re

fieldnames = {
    'addr': ['addr:postcode', 'addr:city', 'addr:place', 'addr:street', 'addr:housenumber', 'addr:door'],
    'tech': ['@lat', '@lon', '@id']
}

def strip_number(phone):
    clear = phone.replace('-', '').replace('+48', '').replace('(', '').replace(')', '').replace(' ', '')
    if len(clear) == 11 and clear[0] == '4' and clear[1] == '8':
        clear = clear[2:]
    if len(clear) > 0:
        return f"+48 {clear[0:2]} {clear[2:5]} {clear[5:7]} {clear[7:9]}"
    return ""

def get_operator_type(name, operator_name):
    public_match = re.search('(urz(ą|a)d)|(miast(o|a))|(gmin(a|y)|(m\. st\.))', operator_name, re.IGNORECASE)
    if public_match:
        return 'public'

    private_match = re.search('(niepubliczn)|(sp\.* *z\.* *o\.* *o)|(s\. *c\.)|(spó|oł|lka)|(prywatny)', name, re.IGNORECASE)
    if private_match:
        return 'private'
    return ''

def getaddr(addrstring, city=False, place=False, street=False, housenumber=False, door=False):
    if not addrstring:
        return {}
    org_addrstring = addrstring
    result = {}

    if door:
        reg = re.compile(r'(.+)( lok.*? ([\-\d\w]+))', re.IGNORECASE)
        match = reg.match(addrstring)
        if match:
            result.update({'addr:door': match.group(3).strip()})
            addrstring = re.sub(reg, r'\1', addrstring)

    if housenumber:
        reg = re.compile(r'(.*?) (\d+[a-zA-Z]*)', re.IGNORECASE)
        match = reg.match(addrstring)
        if match:
            result.update({'addr:housenumber': match.group(2).strip()})
            addrstring = re.sub(reg, r'\1', addrstring)
    
    if street:
        reg = re.compile(r'(.*)(pl(\.|ac)*|al(\.|eja)*|ul(\.|ica)*)? ?(.*)', re.IGNORECASE)
        match = reg.match(addrstring)
        
        if match:
            street_name = match.group(6) or match.group(1)
            result.update({'addr:street': street_name.strip()})
            addrstring = re.sub(reg, r'\1', addrstring)

    if place and not city:
        # reg = re.compile(r'((os(\.|iedle)*)(.+))', re.IGNORECASE)
        # match = reg.match(addrstring)
        if len(addrstring.strip()) > 0:
            result.update({'addr:place': addrstring.strip()})

    if result.get('addr:street') and result.get('addr:place'):
        del result['addr:place']
    elif result.get('addr:place') and result.get('addr:street'):
        del result['addr:street']

    if not result.keys():
        if street and not place and not city and housenumber:
            result.update({'addr:street': addrstring})
        else:
            raise Exception('wtf?', org_addrstring)
    return result


def nominatim_addr(nominatim):
    prefix = nominatim['address']
    city = prefix.get('city') or prefix.get('town') or prefix.get('village')
    city_not_place = prefix.get('road') or (city and prefix.get('place'))

    return {
        'addr:housenumber': prefix.get('house_number'),
        'addr:street': prefix.get('road'),
        'addr:city': city if city_not_place else '',
        'addr:place': city if not city_not_place else prefix.get('place'),
        'addr:postcode': prefix.get('postcode'),
        'addr:door': prefix.get('door')
    }

def komoot_addr(komoot):
    prefix = komoot['features'][0]['properties']
    is_city = prefix.get('city') and (prefix.get('street') or prefix.get('locality'))

    return {
        'addr:housenumber': prefix.get('housenumber'),
        'addr:street': prefix.get('street'),
        'addr:city': prefix.get('city') if is_city else '',
        'addr:place': prefix.get('city') if not is_city else prefix.get('locality'),
        'addr:postcode': prefix.get('postcode'),
        'addr:door': prefix.get('door')
    }

ADDR_FIELDS = {
    'street': lambda x: f'{x.get("addr:street")} {x.get("addr:housenumber")}',
    'city': lambda x: x.get('addr:city') or x.get('addr:place'),
    'postalcode': lambda x: x.get('addr:postcode')
}

def nominatim_searchurl(row, fields=ADDR_FIELDS, single=False):
    if single:
        filled = [field_map(row) if field_map(row) else "" for field_map in fields.values()]
        return ' '.join(filled)
    
    filled = [f'{field}={field_map(row)}' if field_map(row) else "" for field, field_map in fields.items()]
    return '&'.join(filled)
