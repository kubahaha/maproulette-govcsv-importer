from src.utils import strip_number, force_https, parse_address


prepare = {
    "separator": ',',
    "tags": {
        'government': 'pension_fund',
        'official_name': lambda x: f'Zakład Ubezpieczeń Społecznych - {x.get("nazwa").replace("ZUS ", "").strip()}',
        'name': 'nazwa',
        'addr:postcode': lambda it: it.get('adres_1')[0:6],
        'addr:city': lambda it: it.get('adres_1')[7:],
        'addr:street': lambda it: ' '.join(it.get('adres_2').replace('ul. ', '').split(" ")[:-1]),
        'addr:housenumber': lambda it: it.get('adres_2').split(" ")[-1],
        'opening_hours': lambda it: "Mo 8:00-17:00; Tu-Fr 8:00-15:00" if it.get('poniedzialek') == "8.00-17.00" else "Mo-We 8:00-15:30; Th 08:00-17:00; Fr 8:00-14:00"
    }
}

matching = [
    ['official_name'],
    ['name'],
    ['addr:housenumber', 'addr:street', 'addr:city'],
    ['addr:street', 'addr:city'],
    "location:300",
    ['addr:city', 'addr:postcode'],
    ['addr:city'],
]

tags_to_delete = {
    'amenity': '*'
}

tags_to_add = {'office': 'government'}
tags_source = {'source:office': 'Baza punktów obsługi klientów ZUS na dzień 12.12.2025'}
tags_to_replace = {}

rules = {
    'update_addr': False,
    'download_latlon': True
}
