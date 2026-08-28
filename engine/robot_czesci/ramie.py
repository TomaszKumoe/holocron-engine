"""Ramie robota (v0 - PIERWSZY SZKIC GEOMETRII, nie gotowa kinematyka):
obrotowa podstawa + dwa czlony, konczace sie plytka pod chwytak.py.

    python robot/ramie.py

Dlaczego ramie a nie jeden maszt: maszt w dostawca.py tylko WYSTAWIA kamere
na wysokosc - nie sięga W GLAB polki ani nie zmienia kata podejscia do
produktu. Ramie z dwoma czlonami (bark + przedramie) dodaje wlasnie to: zasieg
w gleb i regulacje wysokosci niezaleznie od pozycji podwozia.

Co to NIE jest: to nie jest policzona kinematyka pod realny udzwig czy realny
zasieg polki sklepowej - dlugosci czlonow sa PIERWSZYM ZALOZENIEM do reakcji,
tak jak przy kazdej innej czesci w tym katalogu (patrz chwytak.py, dostawca.py).
Model pokazuje ramie w JEDNEJ przykladowej pozycji (wyciagniete), nie pelny
zakres ruchu - to statyczny rysunek geometrii, nie symulacja.

Napep stawow (serwa/silniki krokowe) to PLACEHOLDER - trzy stawy tej wielkosci
to realnie sila/moment obrotowy wiekszy niz hobbystyczne SG90 z chwytak.py;
dobor napedu zostaje na pozniej, po ustaleniu docelowego udzwigu.

Interfejs do chwytak.py: plytka na koncu przedramienia ma ta sama siatke
otworow co SERWO_UCHO_ROZSTAW w chwytak.py (28mm) - chwytak_obudowa.step
przykreca sie do niej od spodu, tak jak do wlasnej obudowy.
"""

import pathlib

import cadquery as cq

# ── maszt - podnosi CALA podstawe ramienia nad podwozie. PIERWSZA WERSJA byla
# cienka okragla rura (50mm) - z daleka czytala sie jak kolumna hulajnogi, nie
# czesc robota. Ta wersja to gruby, szescioscienny, zwezajacy sie ku gorze
# slup (loft miedzy dwoma szesciokatami) - kanciasty przekroj zamiast kola
# zabija skojarzenie z "rurka", zwezenie ku gorze daje wrazenie masywnej,
# scelowanej kolumny (jak podstawa drona/statku, nie maszt flagi). Kanal w
# srodku nadal prowadzi kable - "specjalne miejsce" na nie, nie tylko podpora.
MASZT_WYSOKOSC = 380.0
MASZT_SZEROKOSC_DOL = 130.0     # "srednica" szesciokata (rozstaw plaskich scianek) u dolu
MASZT_SZEROKOSC_GORA = 92.0      # wezszy u gory - efekt zwezajacej sie kolumny
MASZT_SCIANKA = 6.0
MASZT_OTWOR_MOCUJACY = 4.2
MASZT_OTWOR_ROZSTAW = 70.0

# ── podstawa obrotowa - stoi na SZCZYCIE masztu, obraca cale ramie wokol Z ─
# Powiekszona (70->130mm), zeby wizualnie pasowala do grubszego masztu i
# obudow przegubow - inaczej maly krazek na grubym slupie wygladalby zle.
BAZA_SREDNICA = 130.0
BAZA_WYSOKOSC = 55.0
BAZA_OTWOR_MOCUJACY = 3.2       # M3 do podwozia, 4 sztuki
BAZA_OTWOR_ROZSTAW = 100.0

OBROT_SREDNICA = 12.0            # trzpien obrotu podstawy, os Z

# ── bark - pierwszy czlon, unosi ramie ─────────────────────────────────────
# Przekroj mocno pogrubiony (55x42 -> 95x75) - cienki dlugi patyk czytal sie
# jak antena/kij, nie mechaniczne ramie. Grubszy przekroj + obudowy przegubow
# (JOINT_HOUSING nizej) razem daja wrazenie ciezkiego, napedzanego czlonu.
BARK_DLUGOSC = 600.0
BARK_SZEROKOSC = 95.0
BARK_GRUBOSC = 75.0
BARK_KAT = 55.0                   # stopnie od pionu w pozycji "wyciagniete"

PRZEGUB_SREDNICA = 8.0           # os stawu bark/przedramie (mechanizm wewnatrz obudowy)

# ── obudowy przegubow - widoczne "pody" napedu na kazdym stawie, jak w
# prawdziwym robocie przemyslowym/droidzie, nie goly zgiety pret ───────────
JOINT_HOUSING_SREDNICA = 130.0
JOINT_HOUSING_WYSOKOSC = 80.0

# ── przedramie - drugi czlon, konczy sie plytka pod chwytak ────────────────
PRZEDRAMIE_DLUGOSC = 500.0     # razem z bark daje zasieg ~1100mm wyprostowane
PRZEDRAMIE_SZEROKOSC = 80.0
PRZEDRAMIE_GRUBOSC = 62.0
PRZEDRAMIE_KAT = -70.0            # stopnie wzgledem barku, zgiecie w strone chwytu

# ── plytka montazowa pod chwytak.py - ta sama siatka co SERWO_UCHO_ROZSTAW ─
PLYTKA_CHWYTAKA = (50.0, 40.0, 4.0)
PLYTKA_OTWOR_ROZSTAW = 28.0       # = SERWO_UCHO_ROZSTAW w chwytak.py
PLYTKA_OTWOR = 3.2


def maszt():
    """Gruby, szesciokatny, zwezajacy sie ku gorze slup - nie okragla rura.
    Drazony w srodku (kanal na kable), niosacy podstawe ramienia na szczycie."""
    zewn = (
        cq.Workplane("XY")
        .polygon(6, MASZT_SZEROKOSC_DOL)
        .workplane(offset=MASZT_WYSOKOSC)
        .polygon(6, MASZT_SZEROKOSC_GORA)
        .loft(combine=True)
    )
    wewn = (
        cq.Workplane("XY")
        .polygon(6, MASZT_SZEROKOSC_DOL - 2 * MASZT_SCIANKA)
        .workplane(offset=MASZT_WYSOKOSC)
        .polygon(6, MASZT_SZEROKOSC_GORA - 2 * MASZT_SCIANKA)
        .loft(combine=True)
        .translate((0, 0, -1))
    )
    rura = zewn.cut(wewn)

    # kolnierz mocujacy u dolu, 4 otwory do podwozia
    kolnierz = (
        cq.Workplane("XY")
        .polygon(6, MASZT_SZEROKOSC_DOL + 16)
        .extrude(6)
    )
    for kat in (45, 135, 225, 315):
        import math

        x = (MASZT_OTWOR_ROZSTAW / 2) * math.cos(math.radians(kat))
        y = (MASZT_OTWOR_ROZSTAW / 2) * math.sin(math.radians(kat))
        otwor = (
            cq.Workplane("XY")
            .circle(MASZT_OTWOR_MOCUJACY / 2)
            .extrude(8)
            .translate((x, y, -1))
        )
        kolnierz = kolnierz.cut(otwor)

    return rura.union(kolnierz)


def podstawa():
    baza = (
        cq.Workplane("XY")
        .circle(BAZA_SREDNICA / 2)
        .extrude(BAZA_WYSOKOSC)
        .edges(">Z")
        .chamfer(2)
    )
    otwor_obrotu = cq.Workplane("XY").circle(OBROT_SREDNICA / 2).extrude(BAZA_WYSOKOSC + 2).translate((0, 0, -1))
    baza = baza.cut(otwor_obrotu)

    for kat in (45, 135, 225, 315):
        import math

        x = (BAZA_OTWOR_ROZSTAW / 2) * math.cos(math.radians(kat))
        y = (BAZA_OTWOR_ROZSTAW / 2) * math.sin(math.radians(kat))
        otwor = (
            cq.Workplane("XY")
            .circle(BAZA_OTWOR_MOCUJACY / 2)
            .extrude(BAZA_WYSOKOSC + 2)
            .translate((x, y, -1))
        )
        baza = baza.cut(otwor)

    return baza


def _obudowa_przegubu(z):
    """Cylindryczna 'obudowa napedu' na stawie - to co sprawia ze przejscie
    podstawa->bark->przedramie wyglada jak napedzany przegub (jak w prawdziwym
    ramieniu przemyslowym/droidzie), nie jak zgiecie golego preta."""
    bryla = (
        cq.Workplane("XY")
        .circle(JOINT_HOUSING_SREDNICA / 2)
        .extrude(JOINT_HOUSING_WYSOKOSC)
        .translate((0, 0, z - JOINT_HOUSING_WYSOKOSC / 2))
    )
    bryla = bryla.faces(">Z").edges().chamfer(4)
    bryla = bryla.faces("<Z").edges().chamfer(4)
    return bryla


def bark_lokalny():
    """Sama geometria barku w JEGO WLASNYM zerze stawu (bez przesuniecia na
    podstawe i bez obrotu o BARK_KAT) - do URDF, gdzie kat stawu ustawia
    <joint>, nie mesh. Ostre fazowane krawedzie (nie zaokraglone) + obudowy
    przegubow na obu koncach - ciezki, mechaniczny czlon, nie zgiety pret."""
    czlon = (
        cq.Workplane("XY")
        .box(BARK_SZEROKOSC, BARK_GRUBOSC, BARK_DLUGOSC, centered=(True, True, False))
        .edges("|X")
        .chamfer(10)
    )
    otwor = (
        cq.Workplane("XZ")
        .circle(PRZEGUB_SREDNICA / 2)
        .extrude(BARK_SZEROKOSC + 2)
        .translate((-BARK_SZEROKOSC / 2 - 1, 0, BARK_DLUGOSC))
    )
    czlon = czlon.cut(otwor)
    czlon = czlon.union(_obudowa_przegubu(0)).union(_obudowa_przegubu(BARK_DLUGOSC))
    return czlon


def bark():
    """Pierwszy czlon - od osi podstawy, pochylony o BARK_KAT od pionu."""
    czlon = bark_lokalny()
    czlon = czlon.translate((0, 0, BAZA_WYSOKOSC))
    # os obrotu to dwa punkty ROWNOLEGLE do X - musza miec ta sama wysokosc Z
    # co pivot, inaczej to nie jest os X tylko przekrzywiona linia do (0,0,0)
    return czlon.rotate((0, 0, BAZA_WYSOKOSC), (1, 0, BAZA_WYSOKOSC), BARK_KAT)


def przedramie_lokalny():
    """Geometria przedramienia w jego wlasnym zerze stawu (lokciowym) - do
    URDF, analogicznie do bark_lokalny(). Ostre fazy + obudowa przegubu u
    nasady (lokciowa) - koniec z plytka chwytaka zostaje bez obudowy, to
    punkt montazu narzedzia, nie napedzany staw."""
    czlon = (
        cq.Workplane("XY")
        .box(PRZEDRAMIE_SZEROKOSC, PRZEDRAMIE_GRUBOSC, PRZEDRAMIE_DLUGOSC, centered=(True, True, False))
        .edges("|X")
        .chamfer(8)
    )
    plytka = (
        cq.Workplane("XY")
        .box(*PLYTKA_CHWYTAKA, centered=(True, True, False))
        .translate((0, 0, PRZEDRAMIE_DLUGOSC))
    )
    for dx in (-PLYTKA_OTWOR_ROZSTAW / 2, PLYTKA_OTWOR_ROZSTAW / 2):
        otwor = (
            cq.Workplane("XY")
            .circle(PLYTKA_OTWOR / 2)
            .extrude(PLYTKA_CHWYTAKA[2] + 2)
            .translate((dx, 0, PRZEDRAMIE_DLUGOSC - 1))
        )
        plytka = plytka.cut(otwor)
    czlon = czlon.union(plytka).union(_obudowa_przegubu(0))
    return czlon


def przedramie():
    """Drugi czlon - osadzony na koncu barku, zgiety o PRZEDRAMIE_KAT."""
    czlon = przedramie_lokalny()

    # Lancuch kinematyczny: przedramie budujemy z wlasnym stawem (barkowym
    # tu, lokciowym) w lokalnym zerze, obracamy o SUME katow barku i lokcia
    # (obie osie rownolegle do X, wiec katy sie po prostu dodaja), i dopiero
    # POTEM przesuwamy do prawdziwej pozycji konca barku w przestrzeni.
    # Wczesniejsza wersja przesuwala przed obrotem o nieobrocona dlugosc
    # barku - to dawalo punkt ~340mm od prawdziwego lokcia (widac to bylo
    # dopiero na podgladzie bounds, nie w samych wzorach).
    import math

    czlon = czlon.rotate((0, 0, 0), (1, 0, 0), BARK_KAT + PRZEDRAMIE_KAT)

    punkt_lokcia = (
        0,
        -BARK_DLUGOSC * math.sin(math.radians(BARK_KAT)),
        BAZA_WYSOKOSC + BARK_DLUGOSC * math.cos(math.radians(BARK_KAT)),
    )
    czlon = czlon.translate(punkt_lokcia)

    return czlon


if __name__ == "__main__":
    katalog = pathlib.Path(__file__).parent

    maszt_ = maszt()
    baza_ = podstawa()
    bark_ = bark()
    przedramie_ = przedramie()

    cq.exporters.export(maszt_, str(katalog / "ramie_maszt.stl"))
    cq.exporters.export(maszt_, str(katalog / "ramie_maszt.step"))
    cq.exporters.export(baza_, str(katalog / "ramie_podstawa.stl"))
    cq.exporters.export(baza_, str(katalog / "ramie_podstawa.step"))
    cq.exporters.export(bark_, str(katalog / "ramie_bark.stl"))
    cq.exporters.export(bark_, str(katalog / "ramie_bark.step"))
    cq.exporters.export(przedramie_, str(katalog / "ramie_przedramie.stl"))
    cq.exporters.export(przedramie_, str(katalog / "ramie_przedramie.step"))

    zasieg = BARK_DLUGOSC + PRZEDRAMIE_DLUGOSC
    print(f"dlugosc wyprostowana bark+przedramie: {zasieg:.0f}mm (nie = realny zasieg w pozycji zgietej)")
    print("pozycja pokazana: 'wyciagniete' - jedna przykladowa poza, nie pelny zakres ruchu")
    print("zapisano -> ramie_podstawa/bark/przedramie .stl/.step")
