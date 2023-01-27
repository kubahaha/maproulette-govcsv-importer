# Żłobki

## Pliki wejściowe

[pinb.osm](https://overpass-turbo.eu/s/1pQK).
[pinb_osm.csv](https://overpass-turbo.eu/s/1pQL).
[pinb_gov.csv](https://dane.gov.pl/pl/dataset/2199,baza-teleadresowa-administracji-zespolonej).

## Program

osm_modify.py pinb -m komoot
./gov_match.py pinb -m komoot
python3 ./generate_osmfiles.py -g ./tmp/pinb_gov_paired.csv -o ./tmp/pinb_osm_modified.csv -f ./input/pinb.osm
mr cooperative change --out ./output/pinb_cooperative.geojson ./output/pinb_cooperative.osm
mr cooperative tag --out ./output/pinb_tagfix.geojson ./output/pinb_tagfix.osm

## Stats

### Adresy OSM

Nominatim:
Total: 74/74 100% | found: 26 35% | filled: 42 57% | missing: 6 8%

Komoot:
Total: 74/74 100% | found: 26 35% | filled: 33 45% | missing: 15 20%

### Parowanie

Nominatim
total: 392/392 100% - paired: 59/392 15% - missing: 132/392 34% - to_add: 201/392 51%
Komoot:
total: 392/392 - 100% - paired: 59/392 - 15% - missing: 8/392 - 2% - to_add: 325/392 - 83%