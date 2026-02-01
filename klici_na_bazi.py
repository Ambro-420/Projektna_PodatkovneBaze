import sqlite3 as dbapi

# py datoteka za pridobivanje podatkov iz podatkovne baze

lokacija = "/home/ambro/Desktop/Projektna_PodatkovneBaze/baza.db"
povezava = dbapi.connect(lokacija)
kazalec = povezava.cursor()

# poskusna poizvedba
kazalec.execute("SELECT * FROM product")
rezultati = kazalec.fetchall() # .fetchall vre vrstice

for vrstica in rezultati:
    print(vrstica)
kazalec.close()
povezava.close()

