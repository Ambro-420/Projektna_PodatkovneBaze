"""SQL poizvedbe za delo z bazo izdelkov, uporabniki in naročili."""

from __future__ import annotations

from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# Proizvodi
# ---------------------------------------------------------------------------

SQL_VSE_PROIZVODE = """
SELECT
    p.product_id,
    p.naziv AS naziv_proizvoda,
    p.opis,
    p.koda,
    p.cena,
    p.zaloga,
    p.brand_id,
    p.category_id,
    p.ustvarjen,
    z.naziv AS znamka,
    k.naziv AS kategorija
FROM proizvodi AS p
LEFT JOIN znamke AS z ON p.brand_id = z.brand_id
LEFT JOIN kategorije AS k ON p.category_id = k.category_id
"""

SQL_PROIZVOD_PO_ID = SQL_VSE_PROIZVODE + "WHERE p.product_id = ?"

SQL_DODAJ_ZNAMKO = "INSERT OR IGNORE INTO znamke (naziv) VALUES (?)"
SQL_DODAJ_KATEGORIJO = "INSERT OR IGNORE INTO kategorije (naziv) VALUES (?)"
SQL_DODAJ_PROIZVOD = """
INSERT INTO proizvodi (naziv, opis, koda, cena, zaloga, brand_id, category_id)
VALUES (?, ?, ?, ?, ?, ?, ?)
"""

SQL_POSODOBI_PROIZVOD = """
UPDATE proizvodi
SET naziv = ?, opis = ?, koda = ?, cena = ?, zaloga = ?, brand_id = ?, category_id = ?
WHERE product_id = ?
"""

SQL_IZBRISI_PROIZVOD = "DELETE FROM proizvodi WHERE product_id = ?"
SQL_IZBRISI_KATEGORIJO = "DELETE FROM kategorije WHERE category_id = ?"
SQL_IZBRISI_ZNAMKO = "DELETE FROM znamke WHERE brand_id = ?"

SQL_PRIDOBI_ZNAMKO_PO_ID = "SELECT brand_id, naziv FROM znamke WHERE brand_id = ?"
SQL_PRIDOBI_KATEGORIJO_PO_ID = "SELECT category_id, naziv FROM kategorije WHERE category_id = ?"

SQL_KATEGORIJE_S_STEVILOM = """
SELECT
    k.category_id,
    k.naziv,
    COUNT(p.product_id) AS stevilo_proizvodov
FROM kategorije AS k
LEFT JOIN proizvodi AS p ON p.category_id = k.category_id
GROUP BY k.category_id, k.naziv
ORDER BY k.naziv ASC
"""

SQL_ZNAMKE_S_STEVILOM = """
SELECT
    z.brand_id,
    z.naziv,
    COUNT(p.product_id) AS stevilo_proizvodov
FROM znamke AS z
LEFT JOIN proizvodi AS p ON p.brand_id = z.brand_id
GROUP BY z.brand_id, z.naziv
ORDER BY z.naziv ASC
"""

SQL_SPREMENI_ZALOGO = "UPDATE proizvodi SET zaloga = zaloga + ? WHERE product_id = ?"
SQL_ODSTEJ_ZALOGO = """
UPDATE proizvodi
SET zaloga = zaloga - ?
WHERE product_id = ? AND zaloga >= ?
"""

# ---------------------------------------------------------------------------
# Uporabniki
# ---------------------------------------------------------------------------

SQL_DODAJ_UPORABNIKA = """
INSERT INTO uporabniki (uporabnisko_ime, email, geslo_hash, vloga, ustvarjen)
VALUES (?, ?, ?, ?, ?)
"""

SQL_UPORABNIK_PO_IMENU = """
SELECT user_id, uporabnisko_ime, email, geslo_hash, vloga, ustvarjen
FROM uporabniki
WHERE uporabnisko_ime = ?
"""

SQL_UPORABNIK_PO_ID = """
SELECT user_id, uporabnisko_ime, email, geslo_hash, vloga, ustvarjen
FROM uporabniki
WHERE user_id = ?
"""

SQL_VSI_UPORABNIKI = """
SELECT
    u.user_id,
    u.uporabnisko_ime,
    u.email,
    u.vloga,
    u.ustvarjen,
    COUNT(n.order_id) AS stevilo_narocil,
    COALESCE(SUM(n.skupna_cena), 0) AS skupna_poraba
FROM uporabniki AS u
LEFT JOIN narocila AS n ON n.user_id = u.user_id
GROUP BY u.user_id, u.uporabnisko_ime, u.email, u.vloga, u.ustvarjen
ORDER BY u.ustvarjen DESC
"""

SQL_SPREMENI_VLOGO = "UPDATE uporabniki SET vloga = ? WHERE user_id = ?"

# ---------------------------------------------------------------------------
# Naročila (zgodovina nakupov)
# ---------------------------------------------------------------------------

SQL_DODAJ_NAROCILO = """
INSERT INTO narocila (user_id, ime_kupca, datum, skupna_cena, status)
VALUES (?, ?, ?, ?, ?)
"""

SQL_DODAJ_POSTAVKO = """
INSERT INTO postavke_narocila (order_id, product_id, naziv_proizvoda, cena, kolicina)
VALUES (?, ?, ?, ?, ?)
"""

SQL_NAROCILA = """
SELECT
    n.order_id,
    n.user_id,
    n.ime_kupca,
    n.datum,
    n.skupna_cena,
    n.status,
    u.uporabnisko_ime,
    COALESCE(SUM(pn.kolicina), 0) AS stevilo_artiklov
FROM narocila AS n
LEFT JOIN uporabniki AS u ON n.user_id = u.user_id
LEFT JOIN postavke_narocila AS pn ON pn.order_id = n.order_id
GROUP BY n.order_id, n.user_id, n.ime_kupca, n.datum, n.skupna_cena, n.status, u.uporabnisko_ime
ORDER BY n.datum DESC, n.order_id DESC
"""

SQL_NAROCILO_PO_ID = """
SELECT
    n.order_id,
    n.user_id,
    n.ime_kupca,
    n.datum,
    n.skupna_cena,
    n.status,
    u.uporabnisko_ime
FROM narocila AS n
LEFT JOIN uporabniki AS u ON n.user_id = u.user_id
WHERE n.order_id = ?
"""

SQL_POSTAVKE_NAROCILA = """
SELECT
    pn.item_id,
    pn.order_id,
    pn.product_id,
    pn.naziv_proizvoda,
    pn.cena,
    pn.kolicina,
    (pn.cena * pn.kolicina) AS skupaj
FROM postavke_narocila AS pn
WHERE pn.order_id = ?
ORDER BY pn.item_id ASC
"""

SQL_POSODOBI_STATUS_NAROCILA = "UPDATE narocila SET status = ? WHERE order_id = ?"

# ---------------------------------------------------------------------------
# Statistika za trgovca
# ---------------------------------------------------------------------------

SQL_STATISTIKA_PRODAJE = """
SELECT
    pn.product_id,
    pn.naziv_proizvoda,
    SUM(pn.kolicina) AS prodanih,
    SUM(pn.cena * pn.kolicina) AS promet
FROM postavke_narocila AS pn
JOIN narocila AS n ON n.order_id = pn.order_id
WHERE n.status <> 'preklicano'
GROUP BY pn.product_id, pn.naziv_proizvoda
ORDER BY prodanih DESC
LIMIT ?
"""

SQL_POVZETEK_TRGOVINE = """
SELECT
    (SELECT COUNT(*) FROM proizvodi) AS stevilo_proizvodov,
    (SELECT COUNT(*) FROM kategorije) AS stevilo_kategorij,
    (SELECT COUNT(*) FROM znamke) AS stevilo_znamk,
    (SELECT COUNT(*) FROM uporabniki) AS stevilo_uporabnikov,
    (SELECT COUNT(*) FROM narocila) AS stevilo_narocil,
    (SELECT COALESCE(SUM(skupna_cena), 0) FROM narocila WHERE status <> 'preklicano') AS promet,
    (SELECT COUNT(*) FROM proizvodi WHERE zaloga = 0) AS brez_zaloge,
    (SELECT COUNT(*) FROM proizvodi WHERE zaloga > 0 AND zaloga <= 5) AS nizka_zaloga
"""

SQL_NIZKA_ZALOGA = SQL_VSE_PROIZVODE + "WHERE p.zaloga <= ?\nORDER BY p.zaloga ASC, p.naziv ASC"

SQL_NAROCILA_UPORABNIKA = """
SELECT
    n.order_id,
    n.datum,
    n.skupna_cena,
    n.status,
    COALESCE(SUM(pn.kolicina), 0) AS stevilo_artiklov
FROM narocila AS n
LEFT JOIN postavke_narocila AS pn ON pn.order_id = n.order_id
WHERE n.user_id = ?
GROUP BY n.order_id, n.datum, n.skupna_cena, n.status
ORDER BY n.datum DESC, n.order_id DESC
"""


def sestavi_poizvedbo(filtri: Dict[str, Any] | None = None) -> Tuple[str, list[Any]]:
    """Sestavi SQL poizvedbo za filtriranje izdelkov."""
    sql = SQL_VSE_PROIZVODE
    parametri: list[Any] = []
    pogoji: list[str] = []

    if filtri is None:
        return sql + "ORDER BY p.naziv ASC", parametri

    if filtri.get("znamka_id") is not None:
        pogoji.append("p.brand_id = ?")
        parametri.append(filtri["znamka_id"])

    if filtri.get("kategorija_id") is not None:
        pogoji.append("p.category_id = ?")
        parametri.append(filtri["kategorija_id"])

    if filtri.get("cena_min") is not None:
        pogoji.append("p.cena >= ?")
        parametri.append(filtri["cena_min"])

    if filtri.get("cena_max") is not None:
        pogoji.append("p.cena <= ?")
        parametri.append(filtri["cena_max"])

    if filtri.get("samo_na_zalogi"):
        pogoji.append("p.zaloga > 0")

    if filtri.get("iskalno"):
        pogoji.append("(p.naziv LIKE ? OR p.opis LIKE ? OR p.koda LIKE ?)")
        vzorec = f"%{filtri['iskalno']}%"
        parametri.extend([vzorec, vzorec, vzorec])

    if pogoji:
        sql += "WHERE " + " AND ".join(pogoji) + "\n"

    sql += _razvrscanje(filtri.get("sortiraj"))
    return sql, parametri


def _razvrscanje(sortiraj: str | None) -> str:
    """Vrne ORDER BY del poizvedbe glede na izbrano razvrščanje."""
    moznosti = {
        "cena_narascajoce": "ORDER BY p.cena ASC",
        "cena_padajoce": "ORDER BY p.cena DESC",
        "naziv_padajoce": "ORDER BY p.naziv DESC",
        "zaloga_narascajoce": "ORDER BY p.zaloga ASC",
        "zaloga_padajoce": "ORDER BY p.zaloga DESC",
        "najnovejsi": "ORDER BY p.product_id DESC",
    }
    return moznosti.get(sortiraj or "", "ORDER BY p.naziv ASC")
