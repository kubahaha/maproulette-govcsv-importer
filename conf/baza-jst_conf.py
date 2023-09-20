from src.utils import getaddr
from conf.helpers import wtz_get_housenumber, wtz_getstartdate, wtz_postcode

prepare = {
    "tags": {
        'addr:postcode': wtz_postcode,
        'addr:city': lambda it: it.get('Miejscowość') if it.get('Ulica') else '',
        'addr:place': lambda it: getaddr(it.get('Miejscowość'), place=True, housenumber=True, door=True).get('addr:place') if not it.get('Ulica') else '',
        'addr:street': lambda it: getaddr(it.get('Ulica'), street=True, housenumber=True, door=True).get('addr:street').split('/')[0] if it.get('Ulica') else '',
        'addr:housenumber': wtz_get_housenumber,
        'name': 'Nazwa wtz',
        'operator': 'Organizator',
        'start_date': wtz_getstartdate
    }
}