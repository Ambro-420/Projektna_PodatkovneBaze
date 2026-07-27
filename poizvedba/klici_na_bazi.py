"""Preprost tekstovni vmesnik za pregled izdelkov."""

from database import pridobi_vse_proizvode, pridobi_proizvode_po_filtrih


def prikazi_meni():
    print("\n1. Prikaži vse izdelke")
    print("2. Filtriraj po ceni")
    print("3. Izhod")


def glavni_meni():
    while True:
        prikazi_meni()
        izbira = input("Izberi možnost: ").strip()

        if izbira == "1":
            proizvodi = pridobi_vse_proizvode()
            for proizvod in proizvodi:
                print(
                    f"{proizvod['product_id']}. {proizvod['naziv_proizvoda']} | "
                    f"{proizvod['znamka']} | {proizvod['kategorija']} | {proizvod['cena']} EUR | Zaloga: {proizvod['zaloga']}"
                )
        elif izbira == "2":
            cena_min = float(input("Cena od: "))
            cena_max = float(input("Cena do: "))
            proizvodi = pridobi_proizvode_po_filtrih({"cena_min": cena_min, "cena_max": cena_max})
            for proizvod in proizvodi:
                print(
                    f"{proizvod['product_id']}. {proizvod['naziv_proizvoda']} | "
                    f"{proizvod['znamka']} | {proizvod['kategorija']} | {proizvod['cena']} EUR"
                )
        elif izbira == "3":
            break
        else:
            print("Neveljavna izbira.")


if __name__ == "__main__":
    glavni_meni()

