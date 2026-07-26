# podatke se bo filtriralo na način ena funcija zgradi poizvedbo, druga jo izvede
# podatke razvrščam iz tabel: brands, product, category
testni_filter = ["brands", "brand_id"]
def sestavi_poizvedbo(filtri):
    """funcija sestavi poizvedbo na podlagi filtrov ki si jih kupec izbere"""
    tabela = filtri[0]
    id_podatka = filtri[1]
    # osnvni del, vedno v obliki SELECT ... FROM ...
    osnovna_poizvedba = f"SELECT {id_podatka} FORM {id_podatka}"
    return(osnovna_poizvedba)

    # dinamično dodajanje filtrov

print(sestavi_poizvedbo(testni_filter))