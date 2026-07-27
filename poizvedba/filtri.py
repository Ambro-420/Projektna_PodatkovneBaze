"""SQL poizvedbe za delo z bazo izdelkov."""

from __future__ import annotations

from typing import Any, Dict, Tuple

SQL_VSE_PROIZVODE = """
SELECT
    p.product_id,
    p.naziv AS naziv_proizvoda,
    p.opis,
    p.cena,
    p.zaloga,
    p.brand_id,
    p.category_id,
    z.naziv AS znamka,
    k.naziv AS kategorija
FROM proizvodi AS p
LEFT JOIN znamke AS z ON p.brand_id = z.brand_id
LEFT JOIN kategorije AS k ON p.category_id = k.category_id
"""

SQL_PROIZVOD_PO_ID = """
SELECT
    p.product_id,
    p.naziv AS naziv_proizvoda,
    p.opis,
    p.cena,
    p.zaloga,
    p.brand_id,
    p.category_id,
    z.naziv AS znamka,
    k.naziv AS kategorija
FROM proizvodi AS p
LEFT JOIN znamke AS z ON p.brand_id = z.brand_id
LEFT JOIN kategorije AS k ON p.category_id = k.category_id
WHERE p.product_id = ?
"""

SQL_DODAJ_ZNAMKO = "INSERT OR IGNORE INTO znamke (naziv) VALUES (?)"
SQL_DODAJ_KATEGORIJO = "INSERT OR IGNORE INTO kategorije (naziv) VALUES (?)"
SQL_DODAJ_PROIZVOD = """
INSERT INTO proizvodi (naziv, opis, cena, zaloga, brand_id, category_id)
VALUES (?, ?, ?, ?, ?, ?)
"""

SQL_POSODOBI_PROIZVOD = """
UPDATE proizvodi
SET naziv = ?, opis = ?, cena = ?, zaloga = ?, brand_id = ?, category_id = ?
WHERE product_id = ?
"""

SQL_IZBRISI_PROIZVOD = "DELETE FROM proizvodi WHERE product_id = ?"

SQL_PRIDOBI_ZNAMKO_PO_ID = "SELECT brand_id, naziv FROM znamke WHERE brand_id = ?"
SQL_PRIDOBI_KATEGORIJO_PO_ID = "SELECT category_id, naziv FROM kategorije WHERE category_id = ?"


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

    if filtri.get("iskalno"):
        pogoji.append("(p.naziv LIKE ? OR p.opis LIKE ?)")
        vzorec = f"%{filtri['iskalno']}%"
        parametri.extend([vzorec, vzorec])

    if pogoji:
        sql += "WHERE " + " AND ".join(pogoji) + "\n"

    sortiraj = filtri.get("sortiraj")
    if sortiraj == "cena_narascajoce":
        sql += "ORDER BY p.cena ASC"
    elif sortiraj == "cena_padajoce":
        sql += "ORDER BY p.cena DESC"
    elif sortiraj == "naziv_padajoce":
        sql += "ORDER BY p.naziv DESC"
    else:
        sql += "ORDER BY p.naziv ASC"

    return sql, parametri
