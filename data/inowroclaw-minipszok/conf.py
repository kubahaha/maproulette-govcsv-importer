prepare = {
    "separator": ';',
    "tags": {
        '__lat': 'Szerokość geograficzna punktu',
        '__lon': 'Długość geograficzna punktu'
    }
}

matching = [
    "location:100"
]

tags_to_delete = {}

tags_to_add = {
    'amenity': 'waste_disposal',
    'fee': 'no',
    'name': 'Mini Pszok',
    'operator': 'Przedsiębiorstwo Gospodarki Komunalnej i Mieszkaniowej w Inowrocławiu',
    'operator:type': 'public',
    'waste': 'organic'
}

tags_source = {'source:office': ' Wykaz lokalizacji kontenerów na odpady zielone - mini PSZOK-ów w Inowrocławiu na dzień 7.02.2024'}

tags_to_replace = {}

rules = {
    'update_addr': False,
    'download_latlon': True
}
