import re

from src.utils import getaddr


def wtz_get_housenumber(row):
    addr = {}
    if row.get('Ulica'):
        addr = getaddr(row.get('Ulica'), street=True, housenumber=True, door=True)
    else:
        addr = getaddr(row.get('Miejscowość'), place=True, housenumber=True, door=True)

    return addr.get('addr:housenumber')

def wtz_getstartdate(row):
    if not row.get('Data utworzenia wtz'):
        return ''
    start = row.get('Data utworzenia wtz').split('-')
    if len(start) != 3:
        return ''
    
    if start[2][0] == '9':
        start[2] = f'19{start[2]}'
    else:
        start[2] = f'20{start[2]}'

    return f'{start[2]}-{start[0]}-{start[1]}'

def wtz_postcode(row):
    postcode = ''.join(row.get('Kod').split('-'))
    return f'{postcode[0:2]}-{postcode[2:5]}'

def wtz_get_facility_for(row):
    patterns = {
        'mental_health': r'.*(intelektual|umysł|niedorozw).*',
        'disabled': r'.*(głuch|niesłysz|niewido).*'
    }

    for value, regex in patterns.items():
        if re.match(regex, row.get('Nazwa wtz'), re.IGNORECASE) or re.match(regex, row.get('Organizator'), re.IGNORECASE):
            return value
        
    return ''