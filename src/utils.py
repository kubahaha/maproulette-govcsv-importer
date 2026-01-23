import re
from itertools import accumulate

import requests

from src.engines.nominatim import Nominatim
from src.osm_model.tags import OSM_TECH_TAGS, ADDR, ADDR_CITY, ADDR_DOOR, ADDR_HOUSENUMBER, ADDR_PLACE, ADDR_POSTCODE, ADDR_STREET


FIELDS = {
    'addr': ADDR,
    'tech': OSM_TECH_TAGS
}


def strip_number(phone, str_str_format='2232'):
    clear = phone.replace('-', '').replace('+48', '').replace('(', '').replace(')', '').replace(' ', '')
    prefix = re.search(r'^(00)?(48)(\d+)', clear, flags=re.MULTILINE)
    if prefix:
        clear = prefix.group(3)
    if len(clear) != sum(int(x) for x in str_format if x.isdigit()):
        return ""
    lenghts = [accumulate([0] + [int(x) for x in str_format])]
    out = '+48'
    for i, k in zip(lenghts[0:], lenghts[1:]):
        out += f' {clear[i:k]}'

    return out


def get_operator_type(name, operator_name):
    public_match = re.search(r'(urz[aą]d)|(miast[oa])|(gmin[ay]|(m\. st\.))', operator_name, re.IGNORECASE)
    if public_match:
        return 'public'

    private_match = re.search(r'(niepubliczn)|(sp\.* *z\.* *o\.* *o)|(s\. *c\.)|(sp[óo][łl]ka)|(prywatny)', name, re.IGNORECASE)
    if private_match:
        return 'private'
    return ''


def parse_address(addrstring, pattern=r"^(?:(?P<CITY__2>[\w\d ęółśążźćń]+[a-zęółśążźćń]),? +)?(?:(?:(?:ul(?:\.|ica|))|(?:al(?:\.|eja|))|(?:pl(?:\.|ac|))) +(?P<STREET>[\w\d \.ęółśążźćń-]+[a-zęółśążźćń]) +)?(?:(?P<PLACE>[\w\d ęółśążźćń]+[a-zęółśążźćń]) +)?(?P<HOUSENUMBER>\d+[a-z]?)(?:(?:(?:\/)|(?:l\.)|(?:lok)|(?:m\.) *)(?P<DOOR>\w+))?,? *((?P<POSTCODE>\d{2}\-\d{3}) +)(?P<CITY__1>[\w\d \-ęółśążźćń]+)"):
    m = re.match(pattern, addrstring, re.IGNORECASE + re.MULTILINE)
    try:
        address = m.groupdict()
    except AttributeError:
        print(f'ERROR!: {addrstring}')
        raise
    addr = {}

    for key in ['CITY', 'PLACE', 'DOOR', 'HOUSENUMBER', 'POSTCODE', 'STREET']:
        if address.get(key, False):
            addr.update({key: address[key]})

        for i in range(1, 64):
            new_key = f'{key}__{i}'
            if new_key in address.keys():
                if address.get(new_key, False):
                    addr.update({key: address[new_key]})
            else:
                break

    return {
        ADDR_HOUSENUMBER: addr.get('HOUSENUMBER', None),
        ADDR_DOOR: addr.get('DOOR', None),
        ADDR_STREET: addr.get('STREET', None),
        ADDR_CITY: addr.get('CITY', None),
        ADDR_PLACE: addr.get('PLACE', None),
        ADDR_POSTCODE: addr.get('POSTCODE', None)
    }


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
            result.update({ADDR_STREET: street_name.strip()})
            addrstring = re.sub(reg, r'\1', addrstring)

    if place and not city:
        # reg = re.compile(r'((os(\.|iedle)*)(.+))', re.IGNORECASE)
        # match = reg.match(addrstring)
        if len(addrstring.strip()) > 0:
            result.update({ADDR_PLACE: addrstring.strip()})

    if result.get(ADDR_STREET) and result.get(ADDR_PLACE):
        del result[ADDR_PLACE]
    elif result.get(ADDR_PLACE) and result.get(ADDR_STREET):
        del result[ADDR_STREET]

    if not result.keys():
        if street and not place and not city and housenumber:
            result.update({ADDR_STREET: addrstring})
        else:
            raise Exception('wtf?', org_addrstring)
    return result


def force_https(url, add_missing=True, rewrite=False):
    https_prefix = 'https://'
    if url.startswith(https_prefix):
        return url

    if url.startswith('http://'):
        if rewrite:
            return url.replace('http://', https_prefix)
    elif add_missing:
        return https_prefix + url

    return url


# def download_latlon(tags, engine=Nominatim):
#     found = False
#     engine = engine()

#     if tags.get("official_name"):
#         found = engine.query(tags["official_name"])

#     if not found and (tags.get("addr:city") or tags.get("addr:place")) and tags.get("addr:street") and tags.get("addr:housenumber"):
#         found = engine.query(f'{tags.get("addr:street", tags.get("addr:place", ""))} {tags.get("addr:housenumber", "")} {tags.get("addr:city", "")} {tags.get("addr:postcode", "")}')

#     if not found and (tags.get("addr:city") or tags.get("addr:place")) and tags.get("name") and tags.get("addr:housenumber"):
#         found = engine.query(f'{tags.get("addr:name", "")}, {tags.get("addr:city", tags.get("addr:place", ""))}, {tags.get("addr:postcode", "")}')

#     if found:
#         return engine.result_2_latlon(found)
#     print(f'Warning: location not found\n{tags}')
#     return {}


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
    public_match = re.search(r'(urz[ąa])d)|(miast[oa])|(gmin[ay]|(m\. st\.))', operator_name, re.IGNORECASE)
    if public_match:
        return 'public'

    private_match = re.search(r'(niepubliczn)|(sp\.* *z\.* *o\.* *o)|(s\. *c\.)|(sp[óo][łl]ka)|(prywatny)', name, re.IGNORECASE)
    if private_match:
        return 'private'
    return ''


def miejscownik(mianownik):
    try:
        res = requests.get(f'http://nlp.actaforte.pl:8080/Nomina/Miejscowosci?nazwa={mianownik}', timeout=15)
        msc = re.search(r'Miejscownik [a-zA-ZęółśążźćńĘÓŁŚĄŻŹĆŃ \(\)]+:</td><td><div><b>([a-zA-Z \-ęółśążźćńĘÓŁŚĄŻŹĆŃ]+)', res.text).group(1)
    except Exception:
        return False
    return msc
