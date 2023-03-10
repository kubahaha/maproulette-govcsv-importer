# gov csv to maproulette

## PINB (Nadzór budowlany)

### Pliki wejściowe

[pinb.osm](https://overpass-turbo.eu/s/1pQK).
[pinb_osm.csv](https://overpass-turbo.eu/s/1qGl).
[pinb_gov.csv](https://dane.gov.pl/pl/dataset/2199,baza-teleadresowa-administracji-zespolonej).

### Program

./osm_modify.py pinb -m komoot
./gov_match.py pinb -m komoot
./generate_osmfiles.py pinb
mr cooperative change --out ./output/pinb_cooperative.geojson ./output/pinb_cooperative.osm
mr cooperative tag --out ./output/pinb_tagfix.geojson ./output/pinb_tagfix.osm

### Stats

#### Adresy OSM

Nominatim:
Total: 74/74 100% | found: 26 35% | filled: 42 57% | missing: 6 8%

Komoot:
Total: 74/74 100% | found: 26 35% | filled: 33 45% | missing: 15 20%

#### Parowanie

Nominatim
total: 392/392 100% - paired: 59/392 15% - missing: 132/392 34% - to_add: 201/392 51%
Komoot:
total: 392/392 - 100% - paired: 59/392 - 15% - missing: 8/392 - 2% - to_add: 325/392 - 83%

## Sanepid

### Pliki wejściowe

[sanepid.osm](https://overpass-turbo.eu/s/1qGk).
[sanepid_osm.csv](https://overpass-turbo.eu/s/1qGj).
[sanepid_gov.csv](https://dane.gov.pl/pl/dataset/2199,baza-teleadresowa-administracji-zespolonej).

### Program

./osm_modify.py sanepid -m komoot
./gov_match.py sanepid -m komoot
./generate_osmfiles.py sanepid
mr cooperative change --out ./output/sanepid_cooperative.geojson ./output/sanepid_cooperative.osm
mr cooperative tag --out ./output/sanepid_tagfix.geojson ./output/sanepid_tagfix.osm

### Stats

#### Adresy OSM

Nominatim:
Total: 152/152 100% | found: 95 62% | filled: 38 25% | missing: 19 12%

Komoot:
Total: 152/152 100% | found: 95 62% | filled: 37 24% | missing: 20 13%
#### Parowanie

Nominatim
total: 344/344 100% - paired: 5/344 1% - missing: 105/344 31% - to_add: 234/344 68%
Komoot:
total: 344/344 100% - paired: 5/344 1% - missing: 6/344 2% - to_add: 333/344 97%