# Projektna naloga: trgovska spletna stran

Projekt vsebuje spletno stran trgovca in uporabnika.
Uporabnik gleda samo izdelke jih filtrira, daje v košarico ali jih kupuje.
Trgovec ima pregled nad statistiko prodaje, zgodovino prodanih izdelkov. Poleg tega lahko dodajanja/briše/ureja izdelke itd. in vidi spletno stran iz vidika uporabnika.

Spletna stran vsebuje tudi registracijo novega uporabnika, v primeru da registriramo uporabnika, in želimo da je zdaj *admin*, mu to privilegijo lahko dodeli le nek drug *admin*.

za pregled strani iz perspektive *admin*-a se njegova prijava glasi: ime: "trgovec",geslo: "trgovec123". To je napisano tudi ob kliku na prijavo.


## Zahteve pred zagonom 
Za uspešen zagon potrebujemo **flask >= 1.0.0**, proces nameščanja je napisano v 1. točki zagona programa. 
Ob zagonu želimo biti ali v direktoriju *Projektna_PodatkovneBaze-main/program* in klicati `python app.py`, ali biti v glavnem direktoriju in klicati `python program\app.py`
### Zagon programa
1. Namesti odvisnosti:
   pip install -r requirements.txt

2. Zaženi spletni vmesnik:
   `python program\app.py` ali `python app.py`

Po tem odpri http://127.0.0.1:5000/ v brskalniku.



## Struktura projekta
- database.py - operacije nad SQLite bazo
- filtri.py - sestavljanje SQL poizvedb
- app.py - spletni vmesnik
- templates/index.html - predloga za spletni prikaz
- data/proizvodi.json - začetni podatki



## Podatkovna baza

ER diagram baze je v datoteki er_diagram.png.

Baza (SQLite, baza.db) ima šest tabel:

- znamke - proizvajalci izdelkov (brand_id, naziv)
- kategorije - skupine izdelkov (category_id, naziv)
- proizvodi - izdelki v trgovini (naziv, opis, koda, cena, zaloga)
- uporabniki - računi s šifriranim geslom in vlogo (trgovec ali kupec)
- narocila - glava nakupa (kupec, datum, skupna cena, status)
- postavke_narocila - posamezne vrstice nakupa (količina in cena ob nakupu)

Povezave in njihove števnosti:

- kategorije 1 : N proizvodi - kategorija ima več izdelkov, vsak izdelek je v natanko eni kategoriji (obvezna povezava)
- znamke 1 : N proizvodi - znamka ima več izdelkov, vsak izdelek pripada natanko eni znamki (obvezna povezava)
- uporabniki 1 : N narocila - uporabnik lahko odda več naročil, naročilo pa je lahko tudi brez računa, saj sme biti user_id NULL (nakup gosta)
- narocila 1 : N postavke_narocila - vsako naročilo ima vsaj eno postavko; ob brisanju naročila se postavke izbrišejo (ON DELETE CASCADE)
- proizvodi 1 : N postavke_narocila - izdelek se lahko pojavi v več naročilih, postavka pa lahko ostane brez izdelka, saj sme biti product_id NULL

Zveza med naročili in proizvodi je po pomenu M : N (eno naročilo vsebuje več izdelkov, en izdelek se prodaja v več naročilih). Ker je v relacijski bazi ni mogoče shraniti neposredno, jo razreši vmesna tabela postavke_narocila, ki nosi tudi lastna podatka kolicina in cena.

Postavka hrani naziv_proizvoda in ceno ob nakupu ločeno od tabele proizvodi. Zaradi tega zgodovina nakupov ostane pravilna tudi, če trgovec pozneje spremeni ceno izdelka ali izdelek izbriše.