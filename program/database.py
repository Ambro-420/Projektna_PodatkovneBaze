"""Funkcije za upravljanje s podatkovno bazo SQLite."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from werkzeug.security import check_password_hash, generate_password_hash

import filtri

DATOTEKA_BAZE = Path(__file__).resolve().parent / "baza.db"

VLOGA_TRGOVEC = "trgovec"
VLOGA_KUPEC = "kupec"
VLOGE = (VLOGA_TRGOVEC, VLOGA_KUPEC)

STATUSI_NAROCILA = ("oddano", "poslano", "zakljuceno", "preklicano")

# Privzeti račun trgovca, da je vmesnik dostopen takoj po namestitvi.
PRIVZETI_TRGOVEC = ("trgovec", "trgovec@trgovina.si", "trgovec123")


def _povezava() -> sqlite3.Connection:
    """Vrne povezavo do baze."""
    povezava = sqlite3.connect(DATOTEKA_BAZE)
    povezava.row_factory = sqlite3.Row
    povezava.execute("PRAGMA foreign_keys = ON")
    return povezava


def _zdaj() -> str:
    """Vrne trenutni čas v obliki, ki jo shranjujemo v bazo."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ustvari_bazo() -> None:
    """Ustvari bazo in vse potrebne tabele."""
    ustvari_tabele()
    posodobi_shemo()


def ustvari_tabele() -> None:
    """Ustvari tabele za znamke, kategorije, proizvode, uporabnike in naročila."""
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
                koda TEXT,
                cena REAL NOT NULL,
                zaloga INTEGER NOT NULL DEFAULT 0,
                brand_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                ustvarjen TEXT,
                FOREIGN KEY (brand_id) REFERENCES znamke (brand_id),
                FOREIGN KEY (category_id) REFERENCES kategorije (category_id)
            )
            """
        )
        kazalec.execute(
            """
            CREATE TABLE IF NOT EXISTS uporabniki (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                uporabnisko_ime TEXT NOT NULL UNIQUE,
                email TEXT,
                geslo_hash TEXT NOT NULL,
                vloga TEXT NOT NULL DEFAULT 'kupec',
                ustvarjen TEXT NOT NULL
            )
            """
        )
        kazalec.execute(
            """
            CREATE TABLE IF NOT EXISTS narocila (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ime_kupca TEXT,
                datum TEXT NOT NULL,
                skupna_cena REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'oddano',
                FOREIGN KEY (user_id) REFERENCES uporabniki (user_id)
            )
            """
        )
        kazalec.execute(
            """
            CREATE TABLE IF NOT EXISTS postavke_narocila (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER,
                naziv_proizvoda TEXT NOT NULL,
                cena REAL NOT NULL,
                kolicina INTEGER NOT NULL,
                FOREIGN KEY (order_id) REFERENCES narocila (order_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES proizvodi (product_id)
            )
            """
        )
        kazalec.execute("CREATE INDEX IF NOT EXISTS idx_postavke_narocilo ON postavke_narocila (order_id)")
        kazalec.execute("CREATE INDEX IF NOT EXISTS idx_narocila_uporabnik ON narocila (user_id)")
        povezava.commit()
    finally:
        povezava.close()


def posodobi_shemo() -> None:
    """Doda manjkajoče stolpce v starejše baze, da ostanejo uporabne."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        obstojeci = {vrstica["name"] for vrstica in kazalec.execute("PRAGMA table_info(proizvodi)")}
        if "koda" not in obstojeci:
            kazalec.execute("ALTER TABLE proizvodi ADD COLUMN koda TEXT")
        if "ustvarjen" not in obstojeci:
            kazalec.execute("ALTER TABLE proizvodi ADD COLUMN ustvarjen TEXT")
        povezava.commit()
    finally:
        povezava.close()


# ---------------------------------------------------------------------------
# Začetni podatki
# ---------------------------------------------------------------------------


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

        cas = _zdaj()
        for proizvod in podatki.get("proizvodi", []):
            brand_id = _pridobi_znamko_po_nazivu(povezava, proizvod["znamka"])
            category_id = _pridobi_kategorijo_po_nazivu(povezava, proizvod["kategorija"])
            kazalec.execute(
                filtri.SQL_DODAJ_PROIZVOD,
                (
                    proizvod["naziv"],
                    proizvod.get("opis", ""),
                    proizvod.get("koda", ""),
                    proizvod.get("cena", 0),
                    proizvod.get("zaloga", 0),
                    brand_id,
                    category_id,
                ),
            )
            kazalec.execute(
                "UPDATE proizvodi SET ustvarjen = ? WHERE product_id = ?",
                (cas, kazalec.lastrowid),
            )

        povezava.commit()
    finally:
        povezava.close()


def zagotovi_privzetega_trgovca() -> None:
    """Ustvari privzeti račun trgovca, če v bazi še ni nobenega trgovca."""
    povezava = _povezava()
    try:
        stevilo = povezava.execute(
            "SELECT COUNT(*) FROM uporabniki WHERE vloga = ?", (VLOGA_TRGOVEC,)
        ).fetchone()[0]
    finally:
        povezava.close()

    if stevilo == 0:
        ime, email, geslo = PRIVZETI_TRGOVEC
        registriraj_uporabnika(ime, email, geslo, VLOGA_TRGOVEC)


def zagotovi_zacetne_podatke() -> None:
    """Ustvari bazo in jo napolni s podatki, če je prazna."""
    ustvari_bazo()
    povezava = _povezava()
    try:
        stevilo_proizvodov = povezava.execute("SELECT COUNT(*) FROM proizvodi").fetchone()[0]
    finally:
        povezava.close()

    if stevilo_proizvodov == 0:
        uvozi_podatke_iz_json()
    zagotovi_privzetega_trgovca()


# ---------------------------------------------------------------------------
# Znamke in kategorije
# ---------------------------------------------------------------------------


def dodaj_znamko(naziv: str) -> int:
    """Doda novo znamko in vrne njen ID."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(filtri.SQL_DODAJ_ZNAMKO, (naziv,))
        povezava.commit()
        if kazalec.rowcount == 0:
            return _pridobi_znamko_po_nazivu(povezava, naziv)
        return int(kazalec.lastrowid)
    finally:
        povezava.close()


def dodaj_kategorijo(naziv: str) -> int:
    """Doda novo kategorijo in vrne njen ID."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(filtri.SQL_DODAJ_KATEGORIJO, (naziv,))
        povezava.commit()
        if kazalec.rowcount == 0:
            return _pridobi_kategorijo_po_nazivu(povezava, naziv)
        return int(kazalec.lastrowid)
    finally:
        povezava.close()


def pridobi_kategorije() -> list[dict[str, Any]]:
    """Vrne seznam vseh kategorij."""
    return _vrni_vrstice("SELECT category_id, naziv FROM kategorije ORDER BY naziv ASC")


def pridobi_znamke() -> list[dict[str, Any]]:
    """Vrne seznam vseh znamk."""
    return _vrni_vrstice("SELECT brand_id, naziv FROM znamke ORDER BY naziv ASC")


def pridobi_kategorije_s_stevilom() -> list[dict[str, Any]]:
    """Vrne kategorije skupaj s številom proizvodov v vsaki."""
    return _vrni_vrstice(filtri.SQL_KATEGORIJE_S_STEVILOM)


def pridobi_znamke_s_stevilom() -> list[dict[str, Any]]:
    """Vrne znamke skupaj s številom proizvodov v vsaki."""
    return _vrni_vrstice(filtri.SQL_ZNAMKE_S_STEVILOM)


def izbrisi_kategorijo(category_id: int) -> bool:
    """Izbriše kategorijo, če v njej ni nobenega proizvoda."""
    if _stevilo("SELECT COUNT(*) FROM proizvodi WHERE category_id = ?", (category_id,)):
        return False
    _izvedi(filtri.SQL_IZBRISI_KATEGORIJO, (category_id,))
    return True


def izbrisi_znamko(brand_id: int) -> bool:
    """Izbriše znamko, če nima nobenega proizvoda."""
    if _stevilo("SELECT COUNT(*) FROM proizvodi WHERE brand_id = ?", (brand_id,)):
        return False
    _izvedi(filtri.SQL_IZBRISI_ZNAMKO, (brand_id,))
    return True


# ---------------------------------------------------------------------------
# Proizvodi
# ---------------------------------------------------------------------------


def dodaj_proizvod(
    naziv: str,
    opis: str,
    cena: float,
    zaloga: int,
    brand_id: int,
    category_id: int,
    koda: str = "",
) -> int:
    """Doda nov proizvod v bazo."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(
            filtri.SQL_DODAJ_PROIZVOD,
            (naziv, opis, koda, cena, zaloga, brand_id, category_id),
        )
        proizvod_id = int(kazalec.lastrowid)
        kazalec.execute(
            "UPDATE proizvodi SET ustvarjen = ? WHERE product_id = ?",
            (_zdaj(), proizvod_id),
        )
        povezava.commit()
        return proizvod_id
    finally:
        povezava.close()


def pridobi_vse_proizvode() -> list[dict[str, Any]]:
    """Vrne vse proizvode z dodanimi imeni znamke in kategorije."""
    return pridobi_proizvode_po_filtrih()


def pridobi_proizvod_po_id(proizvod_id: int) -> Optional[dict[str, Any]]:
    """Vrne en proizvod po ID-ju."""
    vrstice = _vrni_vrstice(filtri.SQL_PROIZVOD_PO_ID, (proizvod_id,))
    return vrstice[0] if vrstice else None


def pridobi_proizvode_po_filtrih(filtri_podatki: Optional[Dict[str, Any]] = None) -> list[dict[str, Any]]:
    """Vrne proizvode glede na filtre."""
    sql, parametri = filtri.sestavi_poizvedbo(filtri_podatki)
    return _vrni_vrstice(sql, parametri)


def posodobi_proizvod(
    proizvod_id: int,
    naziv: Optional[str] = None,
    opis: Optional[str] = None,
    cena: Optional[float] = None,
    zaloga: Optional[int] = None,
    brand_id: Optional[int] = None,
    category_id: Optional[int] = None,
    koda: Optional[str] = None,
) -> None:
    """Posodobi izbrane podatke proizvoda."""
    trenutni = pridobi_proizvod_po_id(proizvod_id)
    if not trenutni:
        raise ValueError(f"Proizvod z ID {proizvod_id} ne obstaja")

    _izvedi(
        filtri.SQL_POSODOBI_PROIZVOD,
        (
            naziv if naziv is not None else trenutni["naziv_proizvoda"],
            opis if opis is not None else trenutni["opis"],
            koda if koda is not None else trenutni["koda"],
            cena if cena is not None else trenutni["cena"],
            zaloga if zaloga is not None else trenutni["zaloga"],
            brand_id if brand_id is not None else trenutni["brand_id"],
            category_id if category_id is not None else trenutni["category_id"],
            proizvod_id,
        ),
    )


def izbrisi_proizvod(proizvod_id: int) -> None:
    """Izbriše proizvod iz baze in ohrani zgodovino nakupov.

    Postavke že oddanih naročil ostanejo, le povezava na proizvod se sprosti.
    Naziv in cena sta v postavki shranjena ločeno, zato je zgodovina še vedno
    berljiva tudi po brisanju proizvoda.
    """
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute("BEGIN IMMEDIATE")
        kazalec.execute(
            "UPDATE postavke_narocila SET product_id = NULL WHERE product_id = ?",
            (proizvod_id,),
        )
        kazalec.execute(filtri.SQL_IZBRISI_PROIZVOD, (proizvod_id,))
        povezava.commit()
    except sqlite3.Error:
        povezava.rollback()
        raise
    finally:
        povezava.close()


def odstej_zalogo(proizvod_id: int, kolicina: int) -> bool:
    """Odšteje zalogo proizvoda ob nakupu in vrne True, če je bila operacija uspešna."""
    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(filtri.SQL_ODSTEJ_ZALOGO, (kolicina, proizvod_id, kolicina))
        povezava.commit()
        return kazalec.rowcount > 0
    finally:
        povezava.close()


def spremeni_zalogo(proizvod_id: int, sprememba: int) -> None:
    """Poveča (ali zmanjša) zalogo proizvoda za podano vrednost."""
    _izvedi(filtri.SQL_SPREMENI_ZALOGO, (sprememba, proizvod_id))
    _izvedi("UPDATE proizvodi SET zaloga = 0 WHERE product_id = ? AND zaloga < 0", (proizvod_id,))


def pridobi_proizvode_z_nizko_zalogo(meja: int = 5) -> list[dict[str, Any]]:
    """Vrne proizvode, ki jih je treba naročiti."""
    return _vrni_vrstice(filtri.SQL_NIZKA_ZALOGA, (meja,))


# ---------------------------------------------------------------------------
# Uporabniki
# ---------------------------------------------------------------------------


def registriraj_uporabnika(
    uporabnisko_ime: str,
    email: str,
    geslo: str,
    vloga: str = VLOGA_KUPEC,
) -> int:
    """Ustvari nov uporabniški račun in vrne njegov ID."""
    if vloga not in VLOGE:
        raise ValueError(f"Neveljavna vloga: {vloga}")
    if pridobi_uporabnika_po_imenu(uporabnisko_ime):
        raise ValueError("Uporabniško ime je že zasedeno")

    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute(
            filtri.SQL_DODAJ_UPORABNIKA,
            (uporabnisko_ime, email, generate_password_hash(geslo), vloga, _zdaj()),
        )
        povezava.commit()
        return int(kazalec.lastrowid)
    finally:
        povezava.close()


def pridobi_uporabnika_po_imenu(uporabnisko_ime: str) -> Optional[dict[str, Any]]:
    """Vrne uporabnika po uporabniškem imenu."""
    vrstice = _vrni_vrstice(filtri.SQL_UPORABNIK_PO_IMENU, (uporabnisko_ime,))
    return vrstice[0] if vrstice else None


def pridobi_uporabnika_po_id(user_id: int) -> Optional[dict[str, Any]]:
    """Vrne uporabnika po ID-ju."""
    vrstice = _vrni_vrstice(filtri.SQL_UPORABNIK_PO_ID, (user_id,))
    return vrstice[0] if vrstice else None


def preveri_prijavo(uporabnisko_ime: str, geslo: str) -> Optional[dict[str, Any]]:
    """Vrne uporabnika, če se geslo ujema, sicer None."""
    uporabnik = pridobi_uporabnika_po_imenu(uporabnisko_ime)
    if uporabnik and check_password_hash(uporabnik["geslo_hash"], geslo):
        return uporabnik
    return None


def pridobi_uporabnike() -> list[dict[str, Any]]:
    """Vrne vse uporabnike s povzetkom njihovih nakupov."""
    return _vrni_vrstice(filtri.SQL_VSI_UPORABNIKI)


def spremeni_vlogo(user_id: int, vloga: str) -> None:
    """Spremeni vlogo uporabnika."""
    if vloga not in VLOGE:
        raise ValueError(f"Neveljavna vloga: {vloga}")
    _izvedi(filtri.SQL_SPREMENI_VLOGO, (vloga, user_id))


# ---------------------------------------------------------------------------
# Naročila
# ---------------------------------------------------------------------------


def ustvari_narocilo(
    postavke: Iterable[Dict[str, Any]],
    user_id: Optional[int] = None,
    ime_kupca: str = "",
) -> Optional[int]:
    """Zapiše nakup v zgodovino in odšteje zalogo.

    Postavke so slovarji z ključi ``product_id`` in ``kolicina``. Cela operacija
    teče v eni transakciji, zato se ob premajhni zalogi ne shrani nič.
    """
    postavke = [p for p in postavke if int(p.get("kolicina", 0)) > 0]
    if not postavke:
        return None

    povezava = _povezava()
    try:
        kazalec = povezava.cursor()
        kazalec.execute("BEGIN IMMEDIATE")

        pripravljene = []
        skupna_cena = 0.0
        for postavka in postavke:
            proizvod_id = int(postavka["product_id"])
            kolicina = int(postavka["kolicina"])
            vrstica = kazalec.execute(
                "SELECT naziv, cena, zaloga FROM proizvodi WHERE product_id = ?",
                (proizvod_id,),
            ).fetchone()
            if vrstica is None or vrstica["zaloga"] < kolicina:
                povezava.rollback()
                return None
            pripravljene.append((proizvod_id, vrstica["naziv"], float(vrstica["cena"]), kolicina))
            skupna_cena += float(vrstica["cena"]) * kolicina

        kazalec.execute(
            filtri.SQL_DODAJ_NAROCILO,
            (user_id, ime_kupca, _zdaj(), round(skupna_cena, 2), "oddano"),
        )
        order_id = int(kazalec.lastrowid)

        for proizvod_id, naziv, cena, kolicina in pripravljene:
            kazalec.execute(filtri.SQL_DODAJ_POSTAVKO, (order_id, proizvod_id, naziv, cena, kolicina))
            kazalec.execute(filtri.SQL_ODSTEJ_ZALOGO, (kolicina, proizvod_id, kolicina))

        povezava.commit()
        return order_id
    except sqlite3.Error:
        povezava.rollback()
        raise
    finally:
        povezava.close()


def pridobi_narocila() -> list[dict[str, Any]]:
    """Vrne zgodovino vseh nakupov v trgovini."""
    return _vrni_vrstice(filtri.SQL_NAROCILA)


def pridobi_narocilo(order_id: int) -> Optional[dict[str, Any]]:
    """Vrne eno naročilo skupaj z njegovimi postavkami."""
    vrstice = _vrni_vrstice(filtri.SQL_NAROCILO_PO_ID, (order_id,))
    if not vrstice:
        return None
    narocilo = vrstice[0]
    narocilo["postavke"] = _vrni_vrstice(filtri.SQL_POSTAVKE_NAROCILA, (order_id,))
    return narocilo


def pridobi_narocila_uporabnika(user_id: int) -> list[dict[str, Any]]:
    """Vrne zgodovino nakupov posameznega kupca."""
    return _vrni_vrstice(filtri.SQL_NAROCILA_UPORABNIKA, (user_id,))


def posodobi_status_narocila(order_id: int, status: str) -> None:
    """Spremeni status naročila."""
    if status not in STATUSI_NAROCILA:
        raise ValueError(f"Neveljaven status: {status}")
    _izvedi(filtri.SQL_POSODOBI_STATUS_NAROCILA, (status, order_id))


# ---------------------------------------------------------------------------
# Statistika
# ---------------------------------------------------------------------------


def pridobi_povzetek_trgovine() -> dict[str, Any]:
    """Vrne števce za nadzorno ploščo trgovca."""
    vrstice = _vrni_vrstice(filtri.SQL_POVZETEK_TRGOVINE)
    return vrstice[0] if vrstice else {}


def pridobi_najbolj_prodajane(omejitev: int = 5) -> list[dict[str, Any]]:
    """Vrne najbolje prodajane proizvode."""
    return _vrni_vrstice(filtri.SQL_STATISTIKA_PRODAJE, (omejitev,))


# ---------------------------------------------------------------------------
# Pomožne funkcije
# ---------------------------------------------------------------------------


def _vrni_vrstice(sql: str, parametri: Iterable[Any] = ()) -> list[dict[str, Any]]:
    povezava = _povezava()
    try:
        return [dict(vrstica) for vrstica in povezava.execute(sql, tuple(parametri))]
    finally:
        povezava.close()


def _izvedi(sql: str, parametri: Iterable[Any] = ()) -> int:
    povezava = _povezava()
    try:
        kazalec = povezava.execute(sql, tuple(parametri))
        povezava.commit()
        return kazalec.rowcount
    finally:
        povezava.close()


def _stevilo(sql: str, parametri: Iterable[Any] = ()) -> int:
    povezava = _povezava()
    try:
        return int(povezava.execute(sql, tuple(parametri)).fetchone()[0])
    finally:
        povezava.close()


def _pridobi_znamko_po_nazivu(povezava: sqlite3.Connection, naziv: str) -> int:
    vrstica = povezava.execute("SELECT brand_id FROM znamke WHERE naziv = ?", (naziv,)).fetchone()
    return int(vrstica[0]) if vrstica else 0


def _pridobi_kategorijo_po_nazivu(povezava: sqlite3.Connection, naziv: str) -> int:
    vrstica = povezava.execute("SELECT category_id FROM kategorije WHERE naziv = ?", (naziv,)).fetchone()
    return int(vrstica[0]) if vrstica else 0


zagotovi_zacetne_podatke()
