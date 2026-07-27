# Projektna naloga: trgovska spletna stran

Ta projekt vključuje tri dele, ki ustrezajo zahtevam naloge:

1. Program za ustvarjanje začetne baze iz datoteke JSON.
2. Program s tekstovnim vmesnikom za pregled izdelkov.
3. Program s spletnim vmesnikom (Flask) za prikaz izdelkov.

## Struktura projekta

- database.py - operacije nad SQLite bazo
- filtri.py - sestavljanje SQL poizvedb
- poustvari_bazo.py - ustvari bazo iz podatkov v data/proizvodi.json
- klici_na_bazi.py - tekstovni vmesnik
- app.py - spletni vmesnik
- templates/index.html - predloga za spletni prikaz
- data/proizvodi.json - začetni podatki

## Kako zaženeš projekt

1. Namesti odvisnosti:
   pip install -r requirements.txt

2. Ustvari začetno bazo:
   python poustvari_bazo.py

3. Zaženi tekstovni vmesnik:
   python klici_na_bazi.py

4. Zaženi spletni vmesnik:
   python app.py

Po tem odpri http://127.0.0.1:5000/ v brskalniku.
