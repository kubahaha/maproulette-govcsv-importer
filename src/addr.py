import re

def getaddr(addrstring, city=False, place=False, street=False, housenumber=False, door=False):
    # if not city:
        # clean = f'Fakecity {addrstring}'
    result = {}

    if door:
        reg = re.compile(r'(.+)( lok.*? ([\-\d\w]+))', re.IGNORECASE)
        match = reg.match(addrstring)
        if match:
            result.update({'place': match.group(3).strip()})
            addrstring = re.sub(reg, r'\1', addrstring)

    if housenumber:
        reg = re.compile(r'(.*?) (\d+[a-zA-Z]*)', re.IGNORECASE)
        match = reg.match(addrstring)
        if match:
            result.update({'housenumber': match.group(2).strip()})
            addrstring = re.sub(reg, r'\1', addrstring)

    
    if street:
        reg = re.compile(r'(.*)(pl(\.|ac)*|al(\.|eja)*|ul(\.|ica)*) (.*)', re.IGNORECASE)
        match = reg.match(addrstring)
        if match:
            result.update({'street': match.group(6).strip()})
            addrstring = re.sub(reg, r'\1', addrstring)

    if place and not city:
        # reg = re.compile(r'((os(\.|iedle)*)(.+))', re.IGNORECASE)
        match = reg.match(addrstring)
        result.update({'place': addrstring})

    return result

for text in [
    'Ul. Grunwaldzka 28a',
    'Ul. Rzeszowska 131',
    'Dobra 45',
    'Ul. Przemyska 43a',
    'Ul. Zygmunta Augusta 6/23',
    'Ul. Piłsudskiego 28 UC1',
    'Tymbark 55',
    'Wiśniowa 646',
    'Pl. Kościuszki 7',
    'Bratkowice 401',
    'Os. Panorama 12',
    'Ul. Hausera 4',
    'Ul. Opalińskiego 9',
    'Ul. Rynek 1',
    'Uście Gorlickie 56',
    'Ul. Sadowa 41',
    'Ul. 1  Maja 11',
    'Ul. Powstańców Śląskich 9'
    ]:
    print(text, getaddr(text, place=True, street=True, housenumber=True, door=True))