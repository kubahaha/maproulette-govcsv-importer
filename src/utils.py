import re
from itertools import accumulate

import requests

fieldnames = {
    'addr': ['addr:postcode', 'addr:city', 'addr:place', 'addr:street', 'addr:housenumber', 'addr:door'],
    'tech': ['@lat', '@lon', '@id']
}


def strip_number(phone, format='2232'):
    clear = phone.replace('-', '').replace('+48', '').replace('(', '').replace(')', '').replace(' ', '')
    prefix = re.search(r'^(00)?(48)(\d+)', clear, flags=re.MULTILINE)
    if prefix:
        clear = prefix.group(3)
    if len(clear) != sum(int(x) for x in format if x.isdigit()):
        return ""
    lenghts = list(accumulate([0] + list(int(x) for x in format)))
    out = '+48'
    for i, k in zip(lenghts[0:], lenghts[1:]):
        out += f' {clear[i:k]}'

    return out
    # return f"+48 {clear[g[0]:g[1]]} {clear[g[1]:g[2]]} {clear[g[2]:g[3]]} {clear[g[3]:g[4]]}"


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


def force_https(url, add_missing=True, rewrite=False):
    if url.startswith('https://'):
        return url
    elif url.startswith('http://'):
        if rewrite:
            return url.replace('http://', 'https://')
    else:
        if add_missing:
            return 'https://' + url

    return url


def format_phone():
    pass


def query_nominatim(q=False, p=False):
    if q:
        url = f'https://nominatim.openstreetmap.org/search?q={q}&format=jsonv2'.replace(' ', '+')
    elif p:
        url = f'https://nominatim.openstreetmap.org/search?p={p}&format=jsonv2'.replace(' ', '+')
    else:
        raise ValueError()
    # print(url)
    resp = requests.get(url)
    resp_json = resp.json()

    if resp_json:
        # print(resp_json[0])
        return resp_json[0]


def get_lat_lon_nominatim(tags):
    found = False

    if tags.get("official_name"):
        found = query_nominatim(q=tags["official_name"])
        if found:
            return {'lat': found['lat'], 'lon': found['lon']}

    if (tags.get("addr:city") or tags.get("addr:place")) and tags.get("addr:street") and tags.get("addr:housenumber"):
        found = query_nominatim(q=f'{tags.get("addr:street", tags.get("addr:place", ""))} {tags.get("addr:housenumber", "")} {tags.get("addr:city", "")} {tags.get("addr:postcode", "")}')
        if found:
            return {'lat': found['lat'], 'lon': found['lon']}

    if (tags.get("addr:city") or tags.get("addr:place")) and tags.get("name") and tags.get("addr:housenumber"):
        found = query_nominatim(q=f'{tags.get("addr:name", "")}, {tags.get("addr:city", tags.get("addr:place", ""))}, {tags.get("addr:postcode", "")}')
        if found:
            return {'lat': found['lat'], 'lon': found['lon']}

    return {}


def get_opening_hours(openstr):
    if not openstr:
        return False

    match = re.search(r'(Poniedziałek, Wtorek, Środa, Czwartek, Piątek)(, Sobota)*(, Niedziela)* (\d{1,2}):(\d{1,2})-(\d{1,2}):(\d{1,2})', openstr)
    if match:
        if match.group(3):
            return f'Mo-Su {match.group(4)}:{match.group(5)}-{match.group(6)}:{match.group(7)}'
        if match.group(2):
            return f'Mo-Sa {match.group(4)}:{match.group(5)}-{match.group(6)}:{match.group(7)}'

        return f'Mo-Fr {match.group(4)}:{match.group(5)}-{match.group(6)}:{match.group(7)}'
    return False


def get_operator(name, operator_name):
    public_match = re.search('(urz(ą|a)d)|(miast(o|a))|(gmin(a|y)|(m\. st\.))', operator_name, re.IGNORECASE)
    if public_match:
        return 'public'

    private_match = re.search('(niepubliczn)|(sp\.* *z\.* *o\.* *o)|(s\. *c\.)|(spó|oł|lka)|(prywatny)', name, re.IGNORECASE)
    if private_match:
        return 'private'
    return ''


def miejscownik(mianownik):
    try:
        res = requests.get(f'http://nlp.actaforte.pl:8080/Nomina/Miejscowosci?nazwa={mianownik}')
        msc = re.search(r'Miejscownik [a-zA-ZęółśążźćńĘÓŁŚĄŻŹĆŃ \(\)]+:</td><td><div><b>([a-zA-Z \-ęółśążźćńĘÓŁŚĄŻŹĆŃ]+)', res.text).group(1)
    except Exception:
        return False
    return msc
