from src.utils import strip_number, force_https


prepare = {
    "accept": lambda x: x.get('TYP') != 'KSS',
    "separator": ',',
    "tags": {
        'government': {'TYP': {'BWIP': 'tax', 'DUCS': 'tax', 'IAS': 'tax', 'KIS': 'tax', 'OC': 'customs', 'UCS': 'customs', 'US': 'tax', 'WUS': 'tax'}},
        'official_name': lambda x: x.get('NAZWA URZĘDU').strip(),
        'name': lambda x: x.get('NAZWA URZĘDU').split(' w ')[0].strip().split(' we ')[0].strip(),
        'addr:postcode': 'KOD',
        'addr:city': lambda it: it.get('MIASTO') if it.get('ULICA') else '',
        'addr:place': lambda it: it.get('MIASTO') if not it.get('ULICA') else '',
        'addr:street': 'ULICA',
        'addr:housenumber': 'NR BUDYNKU / LOKALU',
        'phone': lambda x: strip_number(x.get('NR TELEFONU   wraz z nr kierunkowym'), format='2322'),
        'fax': lambda x: strip_number(x.get('NR FAXU'), format='2322'),
        'email': 'ADRES E-MAIL URZĘDU',
        'website': 'ADRESY STRON BIP JEDNOSTEK KAS'
    }
}

matching = [
    ['official_name'],
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:place'],
    "location:300",
    ['addr:place', 'addr:postcode'],
    ['addr:street', 'addr:city'],
    ['addr:housenumber', 'addr:city', 'addr:postcode']
]

tags_to_delete = {
    'amenity': '*'
}

tags_to_add = {'office': 'government'}

tags_source = {'source:office': ' Baza teleadresowa jednostek KAS na dzień 12.02.2024'}

tags_to_replace = {'website': lambda url: force_https(url, True, True)}

rules = {
    'update_addr': False,
    'download_latlon': True
}
