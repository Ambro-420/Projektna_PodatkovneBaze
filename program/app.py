"""Spletni vmesnik trgovine: pogled trgovca (upravljanje) in pogled kupca."""

import json
from functools import wraps

from flask import (
    Flask,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

import database

app = Flask(__name__)
app.secret_key = "seminarska-naloga-podatkovne-baze"
CART_COOKIE = "shopping_cart"
MEJA_NIZKE_ZALOGE = 5


# ---------------------------------------------------------------------------
# Prijava in vloge
# ---------------------------------------------------------------------------


def trenutni_uporabnik():
    """Vrne prijavljenega uporabnika ali None."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return database.pridobi_uporabnika_po_id(user_id)


def je_trgovec() -> bool:
    """Pove, ali je prijavljeni uporabnik trgovec."""
    uporabnik = trenutni_uporabnik()
    return bool(uporabnik and uporabnik["vloga"] == database.VLOGA_TRGOVEC)


def zahtevaj_trgovca(funkcija):
    """Dovoli dostop samo prijavljenemu trgovcu."""

    @wraps(funkcija)
    def ovoj(*args, **kwargs):
        if not je_trgovec():
            flash("Za dostop do upravljanja se moraš prijaviti kot trgovec.", "napaka")
            return redirect(url_for("prijava", naprej=request.path))
        return funkcija(*args, **kwargs)

    return ovoj


def zahtevaj_prijavo(funkcija):
    """Dovoli dostop samo prijavljenemu uporabniku."""

    @wraps(funkcija)
    def ovoj(*args, **kwargs):
        if trenutni_uporabnik() is None:
            flash("Za ta pogled se moraš prijaviti.", "napaka")
            return redirect(url_for("prijava", naprej=request.path))
        return funkcija(*args, **kwargs)

    return ovoj


@app.context_processor
def skupne_spremenljivke():
    """Podatki, ki jih potrebuje vsaka predloga (npr. gumbi za preklop pogleda)."""
    return {
        "uporabnik": trenutni_uporabnik(),
        "je_trgovec": je_trgovec(),
        "stevilo_artiklov": _stevilo_v_vozičku(_preberi_voziček()),
    }


@app.route("/prijava", methods=["GET", "POST"])
def prijava():
    if request.method == "POST":
        uporabnisko_ime = request.form.get("uporabnisko_ime", "").strip()
        geslo = request.form.get("geslo", "")
        uporabnik = database.preveri_prijavo(uporabnisko_ime, geslo)

        if uporabnik is None:
            flash("Napačno uporabniško ime ali geslo.", "napaka")
            return render_template("prijava.html", uporabnisko_ime=uporabnisko_ime)

        session["user_id"] = uporabnik["user_id"]
        flash(f"Pozdravljen, {uporabnik['uporabnisko_ime']}!", "uspeh")

        naprej = request.form.get("naprej") or request.args.get("naprej")
        if naprej and naprej.startswith("/"):
            return redirect(naprej)
        if uporabnik["vloga"] == database.VLOGA_TRGOVEC:
            return redirect(url_for("admin_nadzorna_plosca"))
        return redirect(url_for("index"))

    return render_template("prijava.html", uporabnisko_ime="")


@app.route("/registracija", methods=["GET", "POST"])
def registracija():
    if request.method == "POST":
        uporabnisko_ime = request.form.get("uporabnisko_ime", "").strip()
        email = request.form.get("email", "").strip()
        geslo = request.form.get("geslo", "")
        geslo_ponovno = request.form.get("geslo_ponovno", "")

        napake = []
        if len(uporabnisko_ime) < 3:
            napake.append("Uporabniško ime mora imeti vsaj 3 znake.")
        if len(geslo) < 5:
            napake.append("Geslo mora imeti vsaj 5 znakov.")
        if geslo != geslo_ponovno:
            napake.append("Gesli se ne ujemata.")
        if database.pridobi_uporabnika_po_imenu(uporabnisko_ime):
            napake.append("Uporabniško ime je že zasedeno.")

        if napake:
            for napaka in napake:
                flash(napaka, "napaka")
            return render_template("registracija.html", uporabnisko_ime=uporabnisko_ime, email=email)

        user_id = database.registriraj_uporabnika(uporabnisko_ime, email, geslo, database.VLOGA_KUPEC)
        session["user_id"] = user_id
        flash("Račun je ustvarjen. Dobrodošel v trgovini!", "uspeh")
        return redirect(url_for("index"))

    return render_template("registracija.html", uporabnisko_ime="", email="")


@app.route("/odjava")
def odjava():
    session.pop("user_id", None)
    flash("Odjava je bila uspešna.", "uspeh")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Voziček (piškotek)
# ---------------------------------------------------------------------------


def _preberi_voziček() -> dict[str, int]:
    vsebina = request.cookies.get(CART_COOKIE, "")
    if not vsebina:
        return {}
    try:
        return {str(k): int(v) for k, v in json.loads(vsebina).items()}
    except (ValueError, AttributeError):
        return {}


def _shrani_voziček(response, voziček: dict[str, int]):
    response.set_cookie(
        CART_COOKIE,
        json.dumps(voziček),
        max_age=3600,
        httponly=True,
        samesite="Lax",
    )
    return response


def _stevilo_v_vozičku(voziček: dict[str, int]) -> int:
    return sum(voziček.values())


# ---------------------------------------------------------------------------
# Pogled kupca
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    iskalno = request.args.get("iskalno", "").strip()
    kategorija_id = request.args.get("kategorija_id")
    sortiraj = request.args.get("sortiraj", "naziv_narascajoce")

    filtri = {
        "iskalno": iskalno if iskalno else None,
        "kategorija_id": int(kategorija_id) if kategorija_id and kategorija_id.isdigit() else None,
        "sortiraj": sortiraj,
    }

    return render_template(
        "index.html",
        proizvodi=database.pridobi_proizvode_po_filtrih(filtri),
        kategorije=database.pridobi_kategorije(),
        izbrana_kategorija=kategorija_id,
        iskalno=iskalno,
        sortiraj=sortiraj,
    )


@app.route("/voziček")
def voziček():
    voziček_podatki = _preberi_voziček()
    artikli = []
    skupno = 0.0

    for proizvod_id, kolicina in voziček_podatki.items():
        proizvod = database.pridobi_proizvod_po_id(int(proizvod_id))
        if not proizvod or kolicina <= 0:
            continue
        cena = proizvod["cena"] * kolicina
        artikli.append(
            {
                "product_id": proizvod["product_id"],
                "naziv": proizvod["naziv_proizvoda"],
                "cena": proizvod["cena"],
                "kolicina": kolicina,
                "skupaj": cena,
                "zaloga": proizvod["zaloga"],
            }
        )
        skupno += cena

    return render_template("cart.html", artikli=artikli, skupno=skupno)


@app.route("/voziček/dodaj/<int:proizvod_id>", methods=["POST"])
def dodaj_v_voziček(proizvod_id: int):
    try:
        kolicina = int(request.form.get("kolicina", "1"))
    except ValueError:
        kolicina = 0

    proizvod = database.pridobi_proizvod_po_id(proizvod_id)
    if not proizvod or kolicina < 1:
        flash("Izdelka ni bilo mogoče dodati v voziček.", "napaka")
        return redirect(url_for("index"))

    if proizvod["zaloga"] < 1:
        flash(f"{proizvod['naziv_proizvoda']} ni na zalogi.", "napaka")
        return redirect(url_for("index"))

    voziček_podatki = _preberi_voziček()
    nova_kolicina = voziček_podatki.get(str(proizvod_id), 0) + kolicina
    if nova_kolicina > proizvod["zaloga"]:
        nova_kolicina = proizvod["zaloga"]
        flash(f"Na zalogi je le {proizvod['zaloga']} kosov.", "napaka")
    else:
        flash(f"{proizvod['naziv_proizvoda']} je dodan v voziček.", "uspeh")

    voziček_podatki[str(proizvod_id)] = nova_kolicina
    response = make_response(redirect(url_for("index")))
    return _shrani_voziček(response, voziček_podatki)


@app.route("/voziček/posodobi/<int:proizvod_id>", methods=["POST"])
def posodobi_voziček(proizvod_id: int):
    try:
        kolicina = int(request.form.get("kolicina", "1"))
    except ValueError:
        kolicina = 0

    voziček_podatki = _preberi_voziček()
    proizvod = database.pridobi_proizvod_po_id(proizvod_id)

    if kolicina < 1 or not proizvod:
        voziček_podatki.pop(str(proizvod_id), None)
    else:
        voziček_podatki[str(proizvod_id)] = min(kolicina, proizvod["zaloga"])

    response = make_response(redirect(url_for("voziček")))
    return _shrani_voziček(response, voziček_podatki)


@app.route("/voziček/odstrani/<int:proizvod_id>", methods=["POST"])
def odstrani_iz_vozička(proizvod_id: int):
    voziček_podatki = _preberi_voziček()
    voziček_podatki.pop(str(proizvod_id), None)
    response = make_response(redirect(url_for("voziček")))
    return _shrani_voziček(response, voziček_podatki)


@app.route("/voziček/zaključi", methods=["POST"])
def zakljuci_nakup():
    voziček_podatki = _preberi_voziček()
    if not voziček_podatki:
        flash("Voziček je prazen.", "napaka")
        return redirect(url_for("voziček"))

    uporabnik = trenutni_uporabnik()
    postavke = [
        {"product_id": int(proizvod_id), "kolicina": kolicina}
        for proizvod_id, kolicina in voziček_podatki.items()
    ]

    order_id = database.ustvari_narocilo(
        postavke,
        user_id=uporabnik["user_id"] if uporabnik else None,
        ime_kupca=uporabnik["uporabnisko_ime"] if uporabnik else request.form.get("ime_kupca", "Gost"),
    )

    if order_id is None:
        flash("Nakupa ni bilo mogoče zaključiti – zaloga se je medtem spremenila.", "napaka")
        return redirect(url_for("voziček"))

    flash(f"Nakup je zaključen. Številka naročila: {order_id}.", "uspeh")
    response = make_response(redirect(url_for("index")))
    response.set_cookie(CART_COOKIE, "", max_age=0)
    return response


@app.route("/moji-nakupi")
@zahtevaj_prijavo
def moji_nakupi():
    uporabnik = trenutni_uporabnik()
    return render_template(
        "moji_nakupi.html",
        narocila=database.pridobi_narocila_uporabnika(uporabnik["user_id"]),
    )


# ---------------------------------------------------------------------------
# Pogled trgovca
# ---------------------------------------------------------------------------


@app.route("/admin")
@zahtevaj_trgovca
def admin_nadzorna_plosca():
    return render_template(
        "admin/nadzorna_plosca.html",
        povzetek=database.pridobi_povzetek_trgovine(),
        najbolj_prodajani=database.pridobi_najbolj_prodajane(5),
        nizka_zaloga=database.pridobi_proizvode_z_nizko_zalogo(MEJA_NIZKE_ZALOGE),
        zadnja_narocila=database.pridobi_narocila()[:5],
    )


@app.route("/admin/proizvodi")
@zahtevaj_trgovca
def admin_proizvodi():
    iskalno = request.args.get("iskalno", "").strip()
    kategorija_id = request.args.get("kategorija_id")
    sortiraj = request.args.get("sortiraj", "naziv_narascajoce")

    proizvodi = database.pridobi_proizvode_po_filtrih(
        {
            "iskalno": iskalno if iskalno else None,
            "kategorija_id": int(kategorija_id) if kategorija_id and kategorija_id.isdigit() else None,
            "sortiraj": sortiraj,
        }
    )

    return render_template(
        "admin/proizvodi.html",
        proizvodi=proizvodi,
        kategorije=database.pridobi_kategorije(),
        izbrana_kategorija=kategorija_id,
        iskalno=iskalno,
        sortiraj=sortiraj,
        meja_nizke_zaloge=MEJA_NIZKE_ZALOGE,
    )


@app.route("/admin/proizvodi/nov", methods=["GET", "POST"])
@zahtevaj_trgovca
def admin_nov_proizvod():
    if request.method == "POST":
        podatki, napake = _preberi_obrazec_proizvoda()
        if napake:
            for napaka in napake:
                flash(napaka, "napaka")
            return render_template(
                "admin/obrazec_proizvoda.html",
                proizvod=request.form,
                kategorije=database.pridobi_kategorije(),
                znamke=database.pridobi_znamke(),
                je_nov=True,
            )

        database.dodaj_proizvod(**podatki)
        flash(f"Izdelek »{podatki['naziv']}« je dodan v trgovino.", "uspeh")
        return redirect(url_for("admin_proizvodi"))

    return render_template(
        "admin/obrazec_proizvoda.html",
        proizvod=None,
        kategorije=database.pridobi_kategorije(),
        znamke=database.pridobi_znamke(),
        je_nov=True,
    )


@app.route("/admin/proizvodi/<int:proizvod_id>/uredi", methods=["GET", "POST"])
@zahtevaj_trgovca
def admin_uredi_proizvod(proizvod_id: int):
    proizvod = database.pridobi_proizvod_po_id(proizvod_id)
    if not proizvod:
        flash("Izdelek ne obstaja.", "napaka")
        return redirect(url_for("admin_proizvodi"))

    if request.method == "POST":
        podatki, napake = _preberi_obrazec_proizvoda()
        if napake:
            for napaka in napake:
                flash(napaka, "napaka")
            return render_template(
                "admin/obrazec_proizvoda.html",
                proizvod=request.form,
                kategorije=database.pridobi_kategorije(),
                znamke=database.pridobi_znamke(),
                je_nov=False,
                proizvod_id=proizvod_id,
            )

        database.posodobi_proizvod(proizvod_id, **podatki)
        flash("Izdelek je posodobljen.", "uspeh")
        return redirect(url_for("admin_proizvodi"))

    return render_template(
        "admin/obrazec_proizvoda.html",
        proizvod=proizvod,
        kategorije=database.pridobi_kategorije(),
        znamke=database.pridobi_znamke(),
        je_nov=False,
        proizvod_id=proizvod_id,
    )


@app.route("/admin/proizvodi/<int:proizvod_id>/izbrisi", methods=["POST"])
@zahtevaj_trgovca
def admin_izbrisi_proizvod(proizvod_id: int):
    database.izbrisi_proizvod(proizvod_id)
    flash("Izdelek je izbrisan.", "uspeh")
    return redirect(url_for("admin_proizvodi"))


@app.route("/admin/proizvodi/<int:proizvod_id>/zaloga", methods=["POST"])
@zahtevaj_trgovca
def admin_spremeni_zalogo(proizvod_id: int):
    try:
        sprememba = int(request.form.get("sprememba", "0"))
    except ValueError:
        sprememba = 0

    if sprememba:
        database.spremeni_zalogo(proizvod_id, sprememba)
        flash(f"Zaloga je spremenjena za {sprememba:+d}.", "uspeh")

    return redirect(request.form.get("naprej") or url_for("admin_proizvodi"))


@app.route("/admin/kategorije", methods=["GET", "POST"])
@zahtevaj_trgovca
def admin_kategorije():
    if request.method == "POST":
        naziv = request.form.get("naziv", "").strip()
        if not naziv:
            flash("Naziv kategorije ne sme biti prazen.", "napaka")
        else:
            database.dodaj_kategorijo(naziv)
            flash(f"Kategorija »{naziv}« je na voljo.", "uspeh")
        return redirect(url_for("admin_kategorije"))

    return render_template(
        "admin/kategorije.html",
        kategorije=database.pridobi_kategorije_s_stevilom(),
        znamke=database.pridobi_znamke_s_stevilom(),
    )


@app.route("/admin/kategorije/<int:category_id>/izbrisi", methods=["POST"])
@zahtevaj_trgovca
def admin_izbrisi_kategorijo(category_id: int):
    if database.izbrisi_kategorijo(category_id):
        flash("Kategorija je izbrisana.", "uspeh")
    else:
        flash("Kategorije ni mogoče izbrisati, ker vsebuje izdelke.", "napaka")
    return redirect(url_for("admin_kategorije"))


@app.route("/admin/znamke", methods=["POST"])
@zahtevaj_trgovca
def admin_dodaj_znamko():
    naziv = request.form.get("naziv", "").strip()
    if not naziv:
        flash("Naziv znamke ne sme biti prazen.", "napaka")
    else:
        database.dodaj_znamko(naziv)
        flash(f"Znamka »{naziv}« je na voljo.", "uspeh")
    return redirect(url_for("admin_kategorije"))


@app.route("/admin/znamke/<int:brand_id>/izbrisi", methods=["POST"])
@zahtevaj_trgovca
def admin_izbrisi_znamko(brand_id: int):
    if database.izbrisi_znamko(brand_id):
        flash("Znamka je izbrisana.", "uspeh")
    else:
        flash("Znamke ni mogoče izbrisati, ker ima izdelke.", "napaka")
    return redirect(url_for("admin_kategorije"))


@app.route("/admin/narocila")
@zahtevaj_trgovca
def admin_narocila():
    return render_template(
        "admin/narocila.html",
        narocila=database.pridobi_narocila(),
        statusi=database.STATUSI_NAROCILA,
    )


@app.route("/admin/narocila/<int:order_id>")
@zahtevaj_trgovca
def admin_narocilo(order_id: int):
    narocilo = database.pridobi_narocilo(order_id)
    if not narocilo:
        flash("Naročilo ne obstaja.", "napaka")
        return redirect(url_for("admin_narocila"))
    return render_template("admin/narocilo.html", narocilo=narocilo, statusi=database.STATUSI_NAROCILA)


@app.route("/admin/narocila/<int:order_id>/status", methods=["POST"])
@zahtevaj_trgovca
def admin_status_narocila(order_id: int):
    status = request.form.get("status", "")
    try:
        database.posodobi_status_narocila(order_id, status)
        flash(f"Status naročila {order_id} je »{status}«.", "uspeh")
    except ValueError:
        flash("Neveljaven status naročila.", "napaka")
    return redirect(request.form.get("naprej") or url_for("admin_narocila"))


@app.route("/admin/uporabniki")
@zahtevaj_trgovca
def admin_uporabniki():
    return render_template(
        "admin/uporabniki.html",
        uporabniki=database.pridobi_uporabnike(),
        vloge=database.VLOGE,
    )


@app.route("/admin/uporabniki/<int:user_id>/vloga", methods=["POST"])
@zahtevaj_trgovca
def admin_spremeni_vlogo(user_id: int):
    vloga = request.form.get("vloga", "")
    if user_id == session.get("user_id") and vloga != database.VLOGA_TRGOVEC:
        flash("Ne moreš si odvzeti lastne vloge trgovca.", "napaka")
        return redirect(url_for("admin_uporabniki"))

    try:
        database.spremeni_vlogo(user_id, vloga)
        flash("Vloga je spremenjena.", "uspeh")
    except ValueError:
        flash("Neveljavna vloga.", "napaka")
    return redirect(url_for("admin_uporabniki"))


# ---------------------------------------------------------------------------
# Pomožne funkcije
# ---------------------------------------------------------------------------


def _preberi_obrazec_proizvoda() -> tuple[dict, list[str]]:
    """Prebere in preveri podatke iz obrazca za izdelek."""
    napake: list[str] = []

    naziv = request.form.get("naziv", "").strip()
    if not naziv:
        napake.append("Naziv izdelka je obvezen.")

    try:
        cena = float(request.form.get("cena", "").replace(",", "."))
        if cena < 0:
            napake.append("Cena ne sme biti negativna.")
    except ValueError:
        cena = 0.0
        napake.append("Cena mora biti število.")

    try:
        zaloga = int(request.form.get("zaloga", "0"))
        if zaloga < 0:
            napake.append("Zaloga ne sme biti negativna.")
    except ValueError:
        zaloga = 0
        napake.append("Zaloga mora biti celo število.")

    category_id = _id_ali_nova(
        request.form.get("category_id", ""),
        request.form.get("nova_kategorija", "").strip(),
        database.dodaj_kategorijo,
    )
    if category_id is None:
        napake.append("Izberi obstoječo kategorijo ali vpiši novo.")

    brand_id = _id_ali_nova(
        request.form.get("brand_id", ""),
        request.form.get("nova_znamka", "").strip(),
        database.dodaj_znamko,
    )
    if brand_id is None:
        napake.append("Izberi obstoječo znamko ali vpiši novo.")

    podatki = {
        "naziv": naziv,
        "opis": request.form.get("opis", "").strip(),
        "koda": request.form.get("koda", "").strip(),
        "cena": cena,
        "zaloga": zaloga,
        "category_id": category_id,
        "brand_id": brand_id,
    }
    return podatki, napake


def _id_ali_nova(izbrani_id: str, nov_naziv: str, funkcija_dodaj):
    """Vrne ID izbrane vrednosti ali ustvari novo, če je trgovec vpisal naziv."""
    if nov_naziv:
        return funkcija_dodaj(nov_naziv)
    if izbrani_id.isdigit():
        return int(izbrani_id)
    return None


if __name__ == "__main__":
    app.run(debug=True)
