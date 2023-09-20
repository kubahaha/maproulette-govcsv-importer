;;Lokalizacja instytucji;;;;;;;;;;;;;;

prepare = {
    "accept": lambda row: row.get('Czy podmiot prowadzący zawiesił działalność gospodarczą?') == 'NIE',
    "tags": {
        'addr:postcode': ,
        'addr:city': lambda it: it.get('Miejscowość') if it.get('Ulica') else '',
        'addr:place': lambda it: getaddr(it.get('Miejscowość'), place=True, housenumber=True, door=True).get('addr:place') if not it.get('Ulica') else '',
        'addr:street': lambda it: getaddr(it.get('Ulica'), street=True, housenumber=True, door=True).get('addr:street').split('/')[0] if it.get('Ulica') else '',
        'addr:housenumber': ,
        'name': 'Nazwa',
        'operator': 'Podmiot prowadzący - nazwa',
        'operator:type': '',
        'operator:website': 'Adres WWW podmiotu prowadzącego żłobek/klub'
        'website': 'Adress WWW żłobka/klubu',
        'email': 'E-mail żłobka/klubu',
        'phone': 'Telefon żłobka/klubu',
        'capacity': 'Liczba miejsc',
        'opening_hours': 'Godziny otwarcia'
        'amenity': lambda row: 'kindergarten' if row.get('Typ instytucji') == 'Żłobek' else 'childcare',
        'wheelchair': lambda x: 'yes' if x.get('Czy żłobek/klub jest dostosowany do potrzeb dzieci niepełnosprawnych lub wymagających szczególnej opieki?') == 'TAK' else 'no',
        'ref:regon': 'Podmiot prowadzący - REGON'
    }
}