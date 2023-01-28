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

def getoperator(name, operator_name):
    public_match = re.search('(urz(ą|a)d)|(miast(o|a))|(gmin(a|y)|(m\. st\.))', operator_name, re.IGNORECASE)
    if public_match:
        return 'public'

    private_match = re.search('(niepubliczn)|(sp\.* *z\.* *o\.* *o)|(s\. *c\.)|(spó|oł|lka)|(prywatny)', name, re.IGNORECASE)
    if private_match:
        return 'private'
    return ''

def getnames_pinb(oldname):
    reg = re.compile('(.+) ((we*|dla) .+)')
    match = reg.match(oldname.strip())

    if match:
        return {
            'name': match.group(1).strip(),
            'official_name': match.group(0),
            'short_name': f'PINB {match.group(2)}' if match.group(1)[0] == 'P' else ''
        }
    return {
        'name': oldname.strip(),
    }

def getnames_sanepid(oldname):
    reg = re.compile('(.+) ((we*|dla) .+)')
    match = reg.match(oldname.strip())

    if match:
        return {
            'name': match.group(1).strip(),
            'official_name': match.group(0),
            'short_name': f'Sanepid {match.group(2)}' if match.group(1)[0] != 'G' else ''
        }
    return {
        'name': oldname.strip(),
    }

getnames = {
    'pinb': getnames_pinb,
    'sanepid': getnames_sanepid
}

def getopening(openstr):
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

def getaddr(addrstring, place=False):
    clean = addrstring.split('>')[-1].replace('miasto', '').strip()

    
    reg = re.compile(r'(.+)(pl(\.|ac)*|al(\.|eja)*|ul(\.|ica)*) (.*?) (\d+[a-zA-Z]*)( lok.*?([\-\d\w]+))*', re.IGNORECASE)
    match = reg.match(clean)

    if match:
        return {
            'city': match.group(1).strip(),
            'door': (match.group(9) or '').strip(),
            'housenumber': match.group(7).strip(),
            'street': match.group(6).strip()
        }
    reg = re.compile(r'(.+?) ((os(\.|iedle)*) (.+)) (\d[\w\d]+)( (lok(\.|al) (.+)))*', re.IGNORECASE)
    match = reg.match(clean)
    if match:
        return {
            'city': match.group(1).strip(),
            'door': (match.group(10) or '').strip(),
            'housenumber': match.group(6).strip(),
            'place': match.group(2).strip()
        }

    reg = re.compile(r'(.+) (.+) (\d[\d\w]+)( (lok(\.|al) (.+)))*', re.IGNORECASE)
    match = reg.match(clean)
    if match:
        if place:
            return {
                'door': (match.group(7) or '').strip(),
                'housenumber': match.group(3).strip(),
                'place': match.group(1).strip()
            }
        return {
            'door': (match.group(7) or '').strip(),
            'housenumber': match.group(3).strip(),
            'city': match.group(1).strip()
        }        
    if place:
        return {'place': clean.strip()}
    return {'city': clean.strip()}


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

def nominatim_assign(nominatim, key):
    tmp = False
    for k in key:
        tmp = tmp or nominatim['address'].get(k, False)
    
    if tmp:
        return tmp
    else:
        print(f"  Nominatim failed! {'/'.join(key)}")
        print(f"  https://nominatim.openstreetmap.org/ui/reverse.html?lat={nominatim['lat']}&lon={nominatim['lon']}&zoom=18&format=jsonv2\n")

def count_distance(first, second):
    R = 6373.0

    lat1 = radians(float(first['lat']))
    lon1 = radians(float(first['lon']))
    lat2 = radians(float(second['lat']))
    lon2 = radians(float(second['lon']))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance