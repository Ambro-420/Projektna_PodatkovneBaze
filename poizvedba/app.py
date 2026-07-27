"""Spletni vmesnik za prikaz izdelkov."""

import json

from flask import Flask, make_response, redirect, render_template, request, url_for

from database import (
    odstej_zalogo,
    pridobi_kategorije,
    pridobi_proizvod_po_id,
    pridobi_proizvode_po_filtrih,
)

app = Flask(__name__)
CART_COOKIE = "shopping_cart"


def _preberi_voziček() -> dict[str, int]:
    vsebina = request.cookies.get(CART_COOKIE, "")
    if not vsebina:
        return {}
    try:
        return {str(k): int(v) for k, v in json.loads(vsebina).items()}
    except ValueError:
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

    proizvodi = pridobi_proizvode_po_filtrih(filtri)
    kategorije = pridobi_kategorije()
    voziček_podatki = _preberi_voziček()
    stevilo_artiklov = _stevilo_v_vozičku(voziček_podatki)

    return render_template(
        "index.html",
        proizvodi=proizvodi,
        kategorije=kategorije,
        izbrana_kategorija=kategorija_id,
        iskalno=iskalno,
        sortiraj=sortiraj,
        stevilo_artiklov=stevilo_artiklov,
    )


@app.route("/voziček")
def voziček():
    voziček_podatki = _preberi_voziček()
    artikli = []
    skupno = 0.0

    for proizvod_id, kolicina in voziček_podatki.items():
        proizvod = pridobi_proizvod_po_id(int(proizvod_id))
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
    kolicina = int(request.form.get("kolicina", "1"))
    proizvod = pridobi_proizvod_po_id(proizvod_id)
    if not proizvod or kolicina < 1:
        return redirect(url_for("index"))

    if proizvod["zaloga"] < kolicina:
        return redirect(url_for("index"))

    voziček_podatki = _preberi_voziček()
    trenutna_kolicina = voziček_podatki.get(str(proizvod_id), 0)
    nova_kolicina = trenutna_kolicina + kolicina
    if nova_kolicina > proizvod["zaloga"]:
        nova_kolicina = proizvod["zaloga"]

    voziček_podatki[str(proizvod_id)] = nova_kolicina
    response = make_response(redirect(url_for("index")))
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
        return redirect(url_for("voziček"))

    for proizvod_id, kolicina in voziček_podatki.items():
        proizvod = pridobi_proizvod_po_id(int(proizvod_id))
        if not proizvod or proizvod["zaloga"] < kolicina:
            return redirect(url_for("voziček"))

    for proizvod_id, kolicina in voziček_podatki.items():
        odstej_zalogo(int(proizvod_id), kolicina)

    response = make_response(redirect(url_for("index")))
    response.set_cookie(CART_COOKIE, "", max_age=0)
    return response


if __name__ == "__main__":
    app.run(debug=True)
