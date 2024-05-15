import re
from itertools import accumulate
from src.engines.Nominatim import Nominatim

import requests

FIELDS = {
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


def get_operator_type(name, operator_name):
    public_match = re.search('(urz(ą|a)d)|(miast(o|a))|(gmin(a|y)|(m\. st\.))', operator_name, re.IGNORECASE)
    if public_match:
        return 'public'

    private_match = re.search('(niepubliczn)|(sp\.* *z\.* *o\.* *o)|(s\. *c\.)|(spó|oł|lka)|(prywatny)', name, re.IGNORECASE)
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
        'addr:housenumber': addr.get('HOUSENUMBER', None),
        'addr:door': addr.get('DOOR', None),
        'addr:street': addr.get('STREET', None),
        'addr:city': addr.get('CITY', None),
        'addr:place': addr.get('PLACE', None),
        'addr:postcode': addr.get('POSTCODE', None)
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


def download_latlon(tags, engine=Nominatim):
    found = False

    if tags.get("official_name"):
        found = engine.query(tags["official_name"])

    if not found and (tags.get("addr:city") or tags.get("addr:place")) and tags.get("addr:street") and tags.get("addr:housenumber"):
        found = engine.query(f'{tags.get("addr:street", tags.get("addr:place", ""))} {tags.get("addr:housenumber", "")} {tags.get("addr:city", "")} {tags.get("addr:postcode", "")}')

    if not found and (tags.get("addr:city") or tags.get("addr:place")) and tags.get("name") and tags.get("addr:housenumber"):
        found = engine.query(f'{tags.get("addr:name", "")}, {tags.get("addr:city", tags.get("addr:place", ""))}, {tags.get("addr:postcode", "")}')

    if found:
        return engine.result_2_latlon(found)
    print(f'Warning: location not found\n{tags}')
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
