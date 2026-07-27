import unittest
from pathlib import Path

import database


class TestBaza(unittest.TestCase):
    def setUp(self) -> None:
        self.testna_datoteka = Path("test_baza.db")
        if self.testna_datoteka.exists():
            self.testna_datoteka.unlink()
        database.DATOTEKA_BAZE = self.testna_datoteka
        database.ustvari_bazo()

    def tearDown(self) -> None:
        if self.testna_datoteka.exists():
            self.testna_datoteka.unlink()

    def test_dodaj_in_pridobi_proizvod(self) -> None:
        brand_id = database.dodaj_znamko("Znamka test")
        category_id = database.dodaj_kategorijo("Kategorija test")
        proizvod_id = database.dodaj_proizvod(
            naziv="Testni proizvod",
            opis="Opis proizvoda",
            cena=12.5,
            zaloga=5,
            brand_id=brand_id,
            category_id=category_id,
        )

        proizvod = database.pridobi_proizvod_po_id(proizvod_id)
        self.assertIsNotNone(proizvod)
        self.assertEqual(proizvod["naziv_proizvoda"], "Testni proizvod")
        self.assertEqual(proizvod["znamka"], "Znamka test")
        self.assertEqual(proizvod["kategorija"], "Kategorija test")

    def test_filtriranje_po_ceni_in_iskanju(self) -> None:
        brand_id = database.dodaj_znamko("Znamka test")
        category_id = database.dodaj_kategorijo("Kategorija test")
        database.dodaj_proizvod("Kava", "Dobra kava", 10.0, 3, brand_id, category_id)
        database.dodaj_proizvod("Čaj", "Zelen čaj", 4.5, 8, brand_id, category_id)

        rezultati = database.pridobi_proizvode_po_filtrih({"cena_min": 5, "iskalno": "kava"})
        self.assertEqual(len(rezultati), 1)
        self.assertEqual(rezultati[0]["naziv_proizvoda"], "Kava")

    def test_automatsko_napolni_bazo_iz_json_ko_je_prazna(self) -> None:
        database.zagotovi_zacetne_podatke()
        proizvodi = database.pridobi_proizvode_po_filtrih({})

        self.assertGreaterEqual(len(proizvodi), 4)
        self.assertTrue(any(proizvod["naziv_proizvoda"] == "Nivea krema" for proizvod in proizvodi))


if __name__ == "__main__":
    unittest.main()
