"""Ustvari začetno stanje baze iz datoteke JSON."""

from database import uvozi_podatke_iz_json


if __name__ == "__main__":
    uvozi_podatke_iz_json()
    print("Baza je uspešno ustvarjena in napolnjena s podatki.")
