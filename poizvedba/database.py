"""Funkcije za upravljanje s podatkovno bazo SQLite."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

import filtri

DATOTEKA_BAZE = Path(__file__).resolve().parent / "baza.db"


def _povezava() -> sqlite3.Connection:
    """Vrne povezavo do baze."""
    povezava = sqlite3.connect(DATOTEKA_BAZE)
    povezava.row_factory = sqlite3.Row
    return povezava


def ustvari_bazo() -> None:
    """Ustvari bazo in vse potrebne tabele."""
    ustvari_tabele()


def ustvari_tabele() -> None:
    """Ustvari tabele za znamke, kategorije in proizvode."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(
            """
            CREATE TABLE IF NOT EXISTS znamke (
                brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
                naziv TEXT NOT NULL UNIQUE
            )
            """
        )
        kazalec.execute(
            """
            CREATE TABLE IF NOT EXISTS kategorije (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                naziv TEXT NOT NULL UNIQUE
            )
            """
        )
        kazalec.execute(
            """
            CREATE TABLE IF NOT EXISTS proizvodi (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                naziv TEXT NOT NULL,
                opis TEXT,
                cena REAL NOT NULL,
                zaloga INTEGER NOT NULL DEFAULT 0,
                brand_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                FOREIGN KEY (brand_id) REFERENCES znamke (brand_id),
                FOREIGN KEY (category_id) REFERENCES kategorije (category_id)
            )
            """
        )
        povezava.commit()
    finally:
        povezava.close()


def uvozi_podatke_iz_json(podatki_path: str | Path | None = None) -> None:
    """Ustvari začetno stanje baze iz datoteke JSON."""
    pot = Path(podatki_path) if podatki_path else Path(__file__).resolve().parent / "data" / "proizvodi.json"
    with pot.open("r", encoding="utf-8") as datoteka:
        podatki = json.load(datoteka)

    ustvari_bazo()
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute("DELETE FROM proizvodi")
        kazalec.execute("DELETE FROM znamke")
        kazalec.execute("DELETE FROM kategorije")

        for naziv in podatki.get("znamke", []):
            kazalec.execute(filtri.SQL_DODAJ_ZNAMKO, (naziv,))

        for naziv in podatki.get("kategorije", []):
            kazalec.execute(filtri.SQL_DODAJ_KATEGORIJO, (naziv,))

        for proizvod in podatki.get("proizvodi", []):
            brand_id = _pridobi_znamko_po_nazivu(povezava, proizvod["znamka"])
            category_id = _pridobi_kategorijo_po_nazivu(povezava, proizvod["kategorija"])
            kazalec.execute(
                filtri.SQL_DODAJ_PROIZVOD,
                (
                    proizvod["naziv"],
                    proizvod.get("opis", ""),
                    proizvod.get("cena", 0),
                    proizvod.get("zaloga", 0),
                    brand_id,
                    category_id,
                ),
            )

        povezava.commit()
    finally:
        povezava.close()


def dodaj_znamko(naziv: str) -> int:
    """Doda novo znamko in vrne njen ID."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(filtri.SQL_DODAJ_ZNAMKO, (naziv,))
        povezava.commit()
        return int(kazalec.lastrowid or _pridobi_znamko_po_nazivu(povezava, naziv))
    finally:
        povezava.close()


def dodaj_kategorijo(naziv: str) -> int:
    """Doda novo kategorijo in vrne njen ID."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(filtri.SQL_DODAJ_KATEGORIJO, (naziv,))
        povezava.commit()
        return int(kazalec.lastrowid or _pridobi_kategorijo_po_nazivu(povezava, naziv))
    finally:
        povezava.close()


def dodaj_proizvod(
    naziv: str,
    opis: str,
    cena: float,
    zaloga: int,
    brand_id: int,
    category_id: int,
) -> int:
    """Doda nov proizvod v bazo."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(
            filtri.SQL_DODAJ_PROIZVOD,
            (naziv, opis, cena, zaloga, brand_id, category_id),
        )
        povezava.commit()
        return int(kazalec.lastrowid)
    finally:
        povezava.close()


def pridobi_vse_proizvode() -> list[dict[str, Any]]:
    """Vrne vse proizvode z dodanimi imeni znamke in kategorije."""
    return pridobi_proizvode_po_filtrih()


def pridobi_kategorije() -> list[dict[str, Any]]:
    """Vrne seznam vseh kategorij."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute("SELECT category_id, naziv FROM kategorije ORDER BY naziv ASC")
        return [dict(vrstica) for vrstica in kazalec.fetchall()]
    finally:
        povezava.close()


def pridobi_proizvod_po_id(proizvod_id: int) -> Optional[dict[str, Any]]:
    """Vrne en proizvod po ID-ju."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(filtri.SQL_PROIZVOD_PO_ID, (proizvod_id,))
        vrstica = kazalec.fetchone()
        return dict(vrstica) if vrstica else None
    finally:
        povezava.close()


def odstej_zalogo(proizvod_id: int, kolicina: int) -> bool:
    """Odšteje zalogo proizvoda ob nakupu in vrne True, če je bila operacija uspešna."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(
            "UPDATE proizvodi SET zaloga = zaloga - ? WHERE product_id = ? AND zaloga >= ?",
            (kolicina, proizvod_id, kolicina),
        )
        povezava.commit()
        return kazalec.rowcount > 0
    finally:
        povezava.close()


def pridobi_proizvode_po_filtrih(filtri_podatki: Optional[Dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Vrne proizvode glede na filtre."""
    sql, parametri = filtri.sestavi_poizvedbo(filtri_podatki)
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(sql, parametri)
        return [dict(vrstica) for vrstica in kazalec.fetchall()]
    finally:
        povezava.close()


def posodobi_proizvod(
    proizvod_id: int,
    naziv: Optional[str] = None,
    opis: Optional[str] = None,
    cena: Optional[float] = None,
    zaloga: Optional[int] = None,
    brand_id: Optional[int] = None,
    category_id: Optional[int] = None,
) -> None:
    """Posodobi izbrane podatke proizvoda."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        trenutni = pridobi_proizvod_po_id(proizvod_id)
        if not trenutni:
            raise ValueError(f"Proizvod z ID {proizvod_id} ne obstaja")

        kazalec.execute(
            filtri.SQL_POSODOBI_PROIZVOD,
            (
                naziv if naziv is not None else trenutni["naziv_proizvoda"],
                opis if opis is not None else trenutni["opis"],
                cena if cena is not None else trenutni["cena"],
                zaloga if zaloga is not None else trenutni["zaloga"],
                brand_id if brand_id is not None else trenutni["brand_id"],
                category_id if category_id is not None else trenutni["category_id"],
                proizvod_id,
            ),
        )
        povezava.commit()
    finally:
        povezava.close()


def izbrisi_proizvod(proizvod_id: int) -> None:
    """Izbriše proizvod iz baze."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(filtri.SQL_IZBRISI_PROIZVOD, (proizvod_id,))
        povezava.commit()
    finally:
        povezava.close()


def _pridobi_znamko_po_nazivu(povezava: sqlite3.Connection, naziv: str) -> int:
    kazalec = povezava.execute("SELECT brand_id FROM znamke WHERE naziv = ?", (naziv,))
    vrstica = kazalec.fetchone()
    return int(vrstica[0]) if vrstica else 0


def _pridobi_kategorijo_po_nazivu(povezava: sqlite3.Connection, naziv: str) -> int:
    kazalec = povezava.execute("SELECT category_id FROM kategorije WHERE naziv = ?", (naziv,))
    vrstica = kazalec.fetchone()
    return int(vrstica[0]) if vrstica else 0


def zagotovi_zacetne_podatke() -> None:
    """Ustvari bazo in jo napolni s podatki, če je prazna."""
    ustvari_bazo()
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        stevilo_proizvodov = kazalec.execute("SELECT COUNT(*) FROM proizvodi").fetchone()[0]
        if stevilo_proizvodov == 0:
            uvozi_podatke_iz_json()
    finally:
        povezava.close()


zagotovi_zacetne_podatke()
