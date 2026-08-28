"""Kosz na zakupy: otwarta skrzynka, glowny element robota - nie dodatek do
podwozia, tylko odwrotnie: to podwozie jest pod koszem. Wymiary PLACEHOLDER,
ale celowo maksymalnie duze w granicach podwozia (patrz dostawca.py) - do
korekty po ustaleniu, ile realnie ma sie miescic za jednym kursem.

    python robot/kosz.py

Nozki sa wysokie (NOZKA_WYS) nie bez powodu - pod koszem, w tej przestrzeni,
stoi elektronika (platforma_elektroniki.py) i akumulator (patrz zestaw.py).
Kosz jest oslona dla nich, nie tylko pojemnikiem na zakupy.
"""

import pathlib

import cadquery as cq

KOSZ_ZEW = (540.0, 480.0, 240.0)   # dlugosc, szerokosc, wysokosc - u DOLU (podstawa)
                                     # szerokosc = SZ_PODWOZIA z dostawca.py -
                                     # DOL kosza ma byc DOKLADNIE tak szeroki
                                     # jak podwozie, zeby zaslaniac elektronike
                                     # pod spodem, nie zostawiac jej widocznej z boku
SCIANKA = 3.0

# Kliny zamiast prostego pudelka: PELNA szerokosc u dolu (zaslania elektronike,
# rowna sie podwoziu), lekko zwezone u gory (mniej "regularny", ostrzejsza
# sylwetka - jak wiadro/skrzynia, nie karton). Odwrotnie niz pierwsza wersja,
# ktora zwezala DOL - to zostawialo elektronike widoczna z boku, zle.
GORA_SKALA = 0.86
CHAMFER_GORA = 8.0   # tylko krawedz otworu (bezpieczenstwo reki), nie rogi pionowe

NOZKA_WYS = 90.0             # wysoko - pod koszem stoi elektronika + akumulator
NOZKA_SREDNICA = 14.0
NOZKA_OTWOR = 4.2
NOZKA_ROG_ODSTEP = 26.0


def _lofta(dl_dol, szer_dol, dl_gora, szer_gora, wys, z0=0.0):
    return (
        cq.Workplane("XY", origin=(0, 0, z0))
        .rect(dl_dol, szer_dol)
        .workplane(offset=wys)
        .rect(dl_gora, szer_gora)
        .loft(combine=True)
    )


def kosz():
    dl_gora = KOSZ_ZEW[0] * GORA_SKALA
    szer_gora = KOSZ_ZEW[1] * GORA_SKALA

    bryla = _lofta(KOSZ_ZEW[0], KOSZ_ZEW[1], dl_gora, szer_gora, KOSZ_ZEW[2])
    bryla = bryla.faces(">Z").edges().chamfer(CHAMFER_GORA)

    wnetrze = _lofta(
        KOSZ_ZEW[0] - 2 * SCIANKA,
        KOSZ_ZEW[1] - 2 * SCIANKA,
        dl_gora - 2 * SCIANKA,
        szer_gora - 2 * SCIANKA,
        KOSZ_ZEW[2],
        z0=SCIANKA,
    )
    bryla = bryla.cut(wnetrze)

    for dx in (-1, 1):
        for dy in (-1, 1):
            # nozki licza sie od PELNEJ podstawy (dol kosza = szerokosc
            # podwozia), tak samo jak krawedz dna
            x = dx * (KOSZ_ZEW[0] / 2 - NOZKA_ROG_ODSTEP)
            y = dy * (KOSZ_ZEW[1] / 2 - NOZKA_ROG_ODSTEP)
            nozka = (
                cq.Workplane("XY")
                .circle(NOZKA_SREDNICA / 2)
                .extrude(NOZKA_WYS)
                .translate((x, y, -NOZKA_WYS))
            )
            otwor = (
                cq.Workplane("XY")
                .circle(NOZKA_OTWOR / 2)
                .extrude(NOZKA_WYS + 2)
                .translate((x, y, -NOZKA_WYS - 1))
            )
            nozka = nozka.cut(otwor)
            bryla = bryla.union(nozka)

    return bryla


# ── klapa - przykrywa gorny otwor, zawieszona na jednej (dluzszej) krawedzi.
# Plaska plyta w WLASNYM ZERZE ZAWIASU (krawedz na y=0, lokalnie), tak samo
# jak bark_lokalny w ramie.py - kat otwarcia ustawia sie przez obrot przy
# wstawianiu, nie jest wpieczony w siatke. ──────────────────────────────────
KLAPA_GRUBOSC = 4.0
KLAPA_ZAPAS = 2.0   # odstep od krawedzi otworu, zeby klapa nie ocierala o scianki


def klapa():
    # pasuje do GORNEGO otworu (wezszego, GORA_SKALA), nie do pelnej podstawy
    dl = KOSZ_ZEW[0] * GORA_SKALA - 2 * KLAPA_ZAPAS
    szer = KOSZ_ZEW[1] * GORA_SKALA - 2 * KLAPA_ZAPAS
    # hinge (os obrotu przy otwieraniu) siedzi w lokalnym y=0 - box zaczyna sie
    # dokladnie tam (centered=(True, False, False)), zeby placement w
    # zestaw/FreeCAD mogl obracac wokol tej krawedzi bez dodatkowych przesuniec
    return (
        cq.Workplane("XY")
        .box(dl, szer, KLAPA_GRUBOSC, centered=(True, False, False))
        .edges("|Z")
        .chamfer(3)
    )


if __name__ == "__main__":
    katalog = pathlib.Path(__file__).parent
    model = kosz()
    cq.exporters.export(model, str(katalog / "kosz.stl"))
    cq.exporters.export(model, str(katalog / "kosz.step"))
    klapa_model = klapa()
    cq.exporters.export(klapa_model, str(katalog / "klapa.stl"))
    cq.exporters.export(klapa_model, str(katalog / "klapa.step"))
    poj = (KOSZ_ZEW[0] - 2 * SCIANKA) * (KOSZ_ZEW[1] - 2 * SCIANKA) * KOSZ_ZEW[2] / 1e6
    print(f"kosz zewnetrznie: {KOSZ_ZEW[0]:.0f} x {KOSZ_ZEW[1]:.0f} x {KOSZ_ZEW[2]:.0f} mm")
    print(f"pojemnosc ~{poj:.1f} litra (PLACEHOLDER - do korekty)")
    print("zapisano -> kosz.stl/.step")
