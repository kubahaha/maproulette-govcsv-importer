from src.utils import strip_number
import re

prepare = {
    "accept": lambda x: re.match(r".*policj.*", x.get('NAZWA URZĘDU'), flags=re.IGNORECASE),
    "separator": ';',
    "tags": {
        '__lat': 'DŁUGOŚĆ GEOGRAFICZNA',
        '__lon': 'SZEROKOŚĆ GEOGRAFICZNA',           
        'addr:postcode': 'KOD POCZTOWY',
        'addr:city': lambda it: it.get('MIEJSCOWOŚĆ') if it.get('ULICA') else '',
        'addr:place': lambda it: it.get('MIEJSCOWOŚĆ') if not it.get('ULICA') else '',
        'addr:street': 'ULICA',
        'addr:housenumber': 'NR DOMU',
        'email': 'ADRES E-MAIL URZĘDU',
        'fax': lambda x: strip_number(x.get('NR FAXU        wraz z nr kierunkowym')),
        'name': lambda x: x.get('NAZWA URZĘDU').split(' w ')[0].strip().split(' we ')[0].strip(),
        'official_name': lambda x: x.get('NAZWA URZĘDU').strip(),
        'phone': lambda x: strip_number(x.get('NR TELEFONU wraz z nr kierunkowym')),
        'website': 'ADRES WWW URZĘDU'
    }
}

matching = [
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    "location:300",
    ['addr:place', 'addr:postcode'],
    ['addr:street', 'addr:city']
]

tags_to_delete = {
    'office': '*',
    'government': '*',
}

tags_to_add = {
    'amenity': 'police',
    'source:amenity': 'Baza teleadresowa administracji zespolonej  - wypis na dzień 16.08.2021'
}
