"""Dowod ze silnik GENERUJE geometrie z parametrow, nie tylko wczytuje
gotowe pliki. Nic tu nie jest skopiowane z robot/ - inne wymiary, inny
uklad, napisane od zera jako przyklad.

    python generuj.py

Zapisuje STEP do wygenerowane/przyklad_baza.step, gotowe do wczytania
przez ten sam viewer co reszta silnika.
"""

import pathlib

import cadquery as cq

WYJscie = pathlib.Path(__file__).parent.parent / "wygenerowane"
WYJscie.mkdir(exist_ok=True)

# Domyslne parametry - uzywane tylko gdy baza() wywolywana bez argumentow
# (np. z linii komend). Chat woloa baza(dlugosc, szerokosc, ...) z tym co
# napisze user.
DLUGOSC = 220.0
SZEROKOSC = 160.0
GRUBOSC = 5.0
SR_OTWORU_SILNIKA = 3.2
ROZSTAW_SILNIKOW_X = 70.0
PROMIEN_NAROZNIKA = 12.0


def baza(dlugosc=DLUGOSC, szerokosc=SZEROKOSC, grubosc=GRUBOSC,
          rozstaw_silnikow_x=ROZSTAW_SILNIKOW_X, promien_naroznika=PROMIEN_NAROZNIKA):
    """Rzuca ValueError z czytelnym komunikatem po polsku przy zlych
    wymiarach - to idzie prosto do czatu, nie ma byc surowym tracebackiem."""
    if dlugosc <= 0 or szerokosc <= 0 or grubosc <= 0:
        raise ValueError("długość/szerokość/grubość muszą być dodatnie")
    promien_max = min(dlugosc, szerokosc) / 2 - 1
    if promien_naroznika > promien_max:
        raise ValueError(
            f"promień narożnika {promien_naroznika}mm za duży na płytę {dlugosc}x{szerokosc}mm "
            f"(maks. {promien_max:.1f}mm)"
        )
    if rozstaw_silnikow_x >= dlugosc - 10:
        raise ValueError(
            f"rozstaw otworów {rozstaw_silnikow_x}mm nie mieści się w długości {dlugosc}mm płyty"
        )

    plyta = (
        cq.Workplane("XY")
        .box(dlugosc, szerokosc, grubosc, centered=(True, True, False))
        .edges("|Z")
        .fillet(promien_naroznika)
    )

    # 4 otwory montazowe silnikow, w rogach prostokata wewnatrz plyty
    for x in (-rozstaw_silnikow_x / 2, rozstaw_silnikow_x / 2):
        for y in (-szerokosc / 2 + 20, szerokosc / 2 - 20):
            plyta = (
                plyta.faces(">Z")
                .workplane()
                .center(x, y)
                .hole(SR_OTWORU_SILNIKA * 2)
            )

    return plyta


def zapisz(bryla, nazwa="przyklad_baza"):
    sciezka = WYJscie / f"{nazwa}.step"
    cq.exporters.export(bryla, str(sciezka))
    return sciezka


def zapisz_do(bryla, sciezka_step):
    """Jak zapisz(), ale pod dowolna, pelna sciezke - do zapisu w folderze
    konkretnego projektu (holocron-robotics/projekty/<id>/), nie zawsze
    do globalnego wygenerowane/."""
    cq.exporters.export(bryla, str(sciezka_step))
    return sciezka_step


if __name__ == "__main__":
    print(f"zapisano -> {zapisz(baza())}")
