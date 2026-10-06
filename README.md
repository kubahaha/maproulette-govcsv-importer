# maproulette-gov-csv importer

## Aplikacja przeglądarkowa

W repozytorium jest także statyczny interfejs do przygotowania CSV urzędów, dopasowania ich do OpenStreetMap i pobrania plików OSM oraz raportu brakujących współrzędnych. Całe przetwarzanie danych odbywa się lokalnie w przeglądarce; GitHub Pages nie otrzymuje zawartości importowanych plików.

### Uruchomienie lokalne

Wymagany jest Node.js 22 lub nowszy.

```sh
npm ci
npm run dev
```

Vite poda lokalny adres, zwykle `http://localhost:5173`. Testy uruchomisz przez `npm test`, a build produkcyjny przez `npm run build`.

### GitHub Pages

Workflow `.github/workflows/pages.yml` testuje i buduje aplikację po każdym pushu do `main`, a następnie publikuje katalog `dist`. W ustawieniach repozytorium wybierz **Settings → Pages → Build and deployment → GitHub Actions**. Vite automatycznie ustawia ścieżkę zasobów dla adresu Pages repozytorium.

### Dane i sesje

Wczytaj CSV, ustaw separator i mapowanie kolumn, a potem wczytaj wynik Overpass JSON albo spróbuj wysłać zapytanie z formularza. Etapy dopasowania działają w podanej kolejności. Tylko pojedynczy kandydat jest akceptowany automatycznie; wieloznaczności można rozstrzygnąć ręcznie. Reguły tagów pozwalają ustalić politykę konfliktu OSM/GOV oraz operacje usuń, ustaw i zastąp.

Najpierw **Mapowanie kolumn** przypisuje kolumnę albo skleja kilka kolumn do jednego tagu. Tryb **Adres** mapuje osobno miasto, ulicę, numer, kod pocztowy i miejsce na `addr:city`, `addr:street`, `addr:housenumber`, `addr:postcode` i `addr:place`; każde pole ma regex wejściowy i wyjściowy. Regex wykonuje podstawienie jak `String.replace`, domyślnie z flagami `i` i `m`, np. wejście `^.{6}(.+)$` i wyjście `$1` zamienia `90-001 Łódź` na `Łódź`. Przy braku dopasowania wartość pozostaje bez zmian. Nie są obsługiwane backreference/lookaround ani powtarzane złożone grupy.

Sesja jest automatycznie przechowywana w IndexedDB tej przeglądarki. Przycisk **Zapisz pakiet sesji** pobiera archiwum `pakiet-sesji-<nazwa>.zip`, zawierające `config.json`, źródłowy `gov.csv` i `osm.json`; zaimportowany pakiet musi zawierać te trzy pliki. Archiwa większe niż 100 MB i sesje rozpakowujące się do ponad 250 MB są odrzucane. Dane GOV pozostają w lokalnej pamięci przeglądarki, dopóki użytkownik jej nie wyczyści.

Nominatim jest opcjonalny i używany wyłącznie do uzupełnienia brakujących współrzędnych GOV przed etapem dopasowania lokalizacyjnego. Odpytuje tylko rekordy bez dopasowania w poprzednich etapach, buduje zapytanie ze wszystkich niepustych tagów `addr:*`, a pozytywne i negatywne wyniki cache'uje po znormalizowanym adresie w konfiguracji sesji. Rzeczywiste zapytania są wysyłane pojedynczo z co najmniej 1,1 s przerwy; trafienia z cache nie odpytują usługi. Bezpośrednie pobieranie z Overpass i Nominatim zależy od dostępności usług, CORS i ich limitów; import wcześniej pobranego JSON działa niezależnie od CORS.

Domyślnym endpointem aplikacji jest `https://gov-osm-overpass.kuba-medrek.workers.dev/api/overpass`. Worker proxy znajduje się w `worker/overpass-proxy.js`; lista dozwolonych originów obejmuje produkcyjne `https://kubahaha.github.io` i development `http://localhost:4173`. Wartości origin nie mają końcowego ukośnika, ponieważ przeglądarka wysyła nagłówek `Origin` bez ścieżki. Lokalny serwer można uruchomić na tym porcie poleceniem `npm run dev -- --port 4173`.

Na ekranie **Ustaw reguły i tagi** można dodawać, usuwać i przestawiać reguły dopasowania. Każdy etap adresowy wymaga zgodności wszystkich wymienionych tagów, więc np. etap „miasto” może zostawić kilka kandydatów, a późniejszy etap „miasto + ulica” może jednoznacznie rozstrzygnąć parę. Dopasowane obiekty nie przechodzą do kolejnych etapów. Pola **Źródło do wypełnienia** i **Klucz OSM** ustawiają konfigurowalny tag źródłowy, domyślnie `source:office`. Na ekranie danych OSM można usunąć wczytany plik JSON; czyści to obiekty i dotychczasowe wyniki dopasowania.

Eksport zawiera `to_change.osm`, `to_add.osm` oraz `gov_no_coord.csv`. Raport CSV zachowuje oryginalne kolumny GOV, dodaje przygotowane tagi i dokładne zapytanie Nominatim oraz link do jego ręcznego debugowania. Te same rekordy są widoczne w tabeli na ekranie eksportu. Nowe rekordy bez współrzędnych nie mogą zostać zapisane jako punkty.

## Procedura

1. Przygotuj plik `gov.csv` z danymi urzędowymi
2. Na podstawie `conf.py` po doddadniu opcji `--prepare` przygotowany zostanie `gov_clean.csv`
3. W przypadku `--download` pobrane zostaną obiekty `.osm` do pliku `data.osm`
4. Dopasowanie csv <-> osm po zadanych kryteriach (nazwa, adres)
5. Dla niedopasowanych GOV pobrać lokalizacje
6. Dopasowanie po lokalizacji do niedopasowanych OSM (współrzędne)
7. Jeżeli w dopasowanych nie ma adresu to sprawdź czy należy dodawać (zapytaj nominatima o adres dopasowanego ID)

```sh
mr cooperative change --out ./mr_new.geojson ./to_add.osm
mr cooperative tag --out ./mr_tagfix.geojson ./to_change.osm
```
