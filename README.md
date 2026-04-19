# maproulette-gov-csv importer

## Procedura

1. Przygotuj plik `gov.csv` z danymi urzędowymi
2. Na podstawie `conf.py` po doddadniu opcji `--prepare` przygotowany zostanie `gov_clean.csv`
3. W przypadku `--download` pobrane zostaną obiekty `.osm` do pliku `data.osm`
4. Dopasowanie csv <-> osm po zadanych kryteriach (nazwa, adres)
5. Dla niedopasowanych GOV pobrać lokalizacje
6. Dopasowanie po lokalizacji do niedopasowanych OSM (współrzędne)
7. Jeżeli w dopasowanych nie ma adresu to sprawdź czy należy dodawać (zapytaj nominatima o adres dopasowanego ID)
