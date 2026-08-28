"""Podstawa robota dostawczego: podwozie na kolach plus wysuwany maszt z kamera.

    python robot/dostawca.py

Boks jak u Starshipa dojezdza do krawezni, ale nie zadzwoni do mieszkania na
trzecim pietrze - nie siega domofonu. Ten prototyp odpowiada na jedno pytanie:
czy maszt z kamera, wysuwany recznie i blokowany sruba, w ogole ma sens - zanim
ktokolwiek projektuje silnik do jego automatycznego wysuwania. Manualny maszt
to godziny roboty, motoryzacja to tygodnie; nie warto ich wydawac, dopoki nie
wiadomo, czy sam pomysl dziala.

Dwie czesci do druku:
  podwozie.stl          - rama, mocowania silnikow, kolko samonastawne i RURA
                           zewnetrzna masztu (na sztywno w podwoziu)
  maszt_wewnetrzny.stl   - rura wewnetrzna + platforma na kamere na szczycie,
                           wsuwana w rure zewnetrzna i blokowana sruba z boku

Wymiary silnikow i kamery sa PLACEHOLDERAMI - zmien je na wymiary tego, co
naprawde kupisz, zanim wydrukujesz. Tak jak przy pierscieniu: cala regulacja
siedzi w liczbach na gorze pliku.
"""

import math
import pathlib

import cadquery as cq

# ── podwozie ──────────────────────────────────────────────────────────────
# Powiekszone z pierwotnych 260x180 - robot do zakupow niesie kosz (360x280,
# patrz kosz.py) i ramie z zasiegiem, nie mieszcily sie na malym podwoziu
# zaprojektowanym tylko pod maszt z kamera (widac to bylo na podgladzie
# zestaw.py - kosz byl wiekszy niz cale podwozie).
DL_PODWOZIA = 700.0
SZ_PODWOZIA = 480.0
GR_PODWOZIA = 6.0
PROMIEN_NAROZY = 26.0   # powiekszone z 12mm - gladsze linie nadwozia

# ── kola napedowe (tylne, +X) - PLACEHOLDER, zmien pod swoj silnik/kolo ────
MOTOR_ROZSTAW_OTWOROW = 16.0   # odleglosc miedzy otworami mocujacymi
MOTOR_OTWOR = 3.2              # M3 z luzem
MOTOR_WCIECIE = (24.0, 14.0)   # okno na wal i korpus silnika

KOLO_SREDNICA = 165.0           # troche mniejsze niz 180mm - w polaczeniu z
                                  # wieksza szerokoscia daje bardziej "przysadzista",
                                  # zwarta proporcje (kolo jak z terenowego pojazdu,
                                  # nie jak z roweru)
KOLO_SZEROKOSC = 125.0            # mocno powiekszone z 55->80->125mm - to jest
                                    # glowna zmiana ktora zabija wrazenie "hulajnogi"
KOLO_FAZA = 6.0                   # faza na krawedzi - bez niej to ostry dysk, nie opona
KOLO_OS_Z = GR_PODWOZIA / 2      # os kola na wysokosci srodka plyty podwozia -
                                   # od tego zalezy prawdziwy prosewit pod spodem

# ── dwa kolka samonastawne z przodu (-X), po jednym w kazdym rogu - dwa
# napedzane kola z tylu + dwa bierne z przodu, wciaz rozniczkowe sterowanie
# (oba przednie sie swobodnie obracaja), ale mniej podatne na przechyl na
# bok niz jedno kolko na srodku - wazne przy zaladowanym koszu na jednym
# boku podwozia. Cztery kola, nie cztery napedy. ──────────────────────────
CASTER_SREDNICA_MOCOWANIA = 25.0
CASTER_OTWORY = 3
CASTER_OTWOR = 3.2

KOLKO_SREDNICA = KOLO_SREDNICA    # TAKIE SAME jak kola napedowe - 4 identyczne
                                    # kola, nie kula obok walca (patrz kolka_samonastawne_bryla)
KOLKO_OS_Z = KOLO_OS_Z              # ta sama os co kola napedowe, skoro to ta sama bryla

# ── maszt teleskopowy ────────────────────────────────────────────────────
MAST_ZEW_OD = 24.0
MAST_ZEW_GRUBOSC = 2.0
MAST_ZEW_WYSOKOSC = 200.0      # rura na sztywno w podwoziu

LUZ_TELESKOP = 0.35            # zapas na skurcz wydruku - bez tego sie nie wsunie
MAST_WEWN_GRUBOSC = 1.6
MAST_WEWN_WYSOKOSC = 260.0     # dluzsza niz zewnetrzna - stad bierze sie wysuw

# srednica wewnetrznej rury wynika z zewnetrznej, zeby zawsze pasowaly do siebie
MAST_WEWN_OD = MAST_ZEW_OD - 2 * MAST_ZEW_GRUBOSC - 2 * LUZ_TELESKOP

# sruba blokujaca wysokosc - dokrecana z boku rury zewnetrznej, jak w nodze statywu
SRUBA_BLOKUJACA_OTWOR = 3.2
SRUBA_BLOKUJACA_WYSOKOSC = 170.0   # jak wysoko na rurze zewnetrznej

# ── platforma na kamere - PLACEHOLDER, dopasuj do wlasnej kamery ──────────
KAMERA_PLYTKA = (36.0, 28.0, 3.0)
KAMERA_ROZSTAW_X = 21.0
KAMERA_ROZSTAW_Y = 13.0
KAMERA_OTWOR = 2.2

# Maszt przesuniety z (0,0) w bok (patrz zestaw.py) - na wiekszym podwoziu
# (kosz + ramie) nie ma juz sensu trzymac go w geometrycznym srodku. Kazdy,
# kto uzywa tej wspolrzednej (platforma_elektroniki.py, zestaw.py), bierze
# ja stad, wiec zmiana tu automatycznie przesuwa i maszt, i otwor na niego
# w platformie - nie trzeba pamietac o dwoch miejscach naraz.
MASZT_X = -280.0
MASZT_Y = 0.0


# pozycje mocowan - policzone raz tutaj, zeby kola (nizej) i zestaw.py
# uzywaly DOKLADNIE tych samych liczb co same otwory w podwoziu
MOTOR_X = DL_PODWOZIA / 2 - 30
MOTOR_Y = SZ_PODWOZIA / 2 - 20
CASTER_X = -DL_PODWOZIA / 2 + 26
CASTER_Y = SZ_PODWOZIA / 2 - 40   # wciety od krawedzi mniej niz silniki - kolko jest mniejsze


def podwozie():
    """Rama z zaokraglonymi rogami, mocowaniami silnikow i kolka, plus rura masztu."""
    baza = (
        cq.Workplane("XY")
        .box(DL_PODWOZIA, SZ_PODWOZIA, GR_PODWOZIA, centered=(True, True, False))
        .edges("|Z")
        .fillet(PROMIEN_NAROZY)
    )

    for znak in (-1, 1):
        x = MOTOR_X
        y = znak * MOTOR_Y
        wciecie = (
            cq.Workplane("XY")
            .box(*MOTOR_WCIECIE, GR_PODWOZIA + 2, centered=(True, True, False))
            .translate((x, y, -1))
        )
        baza = baza.cut(wciecie)
        for dx in (-MOTOR_ROZSTAW_OTWOROW / 2, MOTOR_ROZSTAW_OTWOROW / 2):
            otwor = (
                cq.Workplane("XY")
                .circle(MOTOR_OTWOR / 2)
                .extrude(GR_PODWOZIA + 2)
                .translate((x + dx, y, -1))
            )
            baza = baza.cut(otwor)

    # dwa kolka samonastawne - kazde na trzech otworach w okregu, typowy
    # wzorzec mocowania kulki/kolka skretnego
    for znak in (-1, 1):
        yc = znak * CASTER_Y
        for i in range(CASTER_OTWORY):
            kat = 2 * math.pi * i / CASTER_OTWORY
            ox = CASTER_X + (CASTER_SREDNICA_MOCOWANIA / 2) * math.cos(kat)
            oy = yc + (CASTER_SREDNICA_MOCOWANIA / 2) * math.sin(kat)
            otwor = (
                cq.Workplane("XY")
                .circle(CASTER_OTWOR / 2)
                .extrude(GR_PODWOZIA + 2)
                .translate((ox, oy, -1))
            )
            baza = baza.cut(otwor)

    # rura zewnetrzna masztu - na sztywno w podwoziu, w niej chowa sie maszt
    rura_zew = (
        cq.Workplane("XY")
        .circle(MAST_ZEW_OD / 2)
        .circle(MAST_ZEW_OD / 2 - MAST_ZEW_GRUBOSC)
        .extrude(MAST_ZEW_WYSOKOSC)
        .translate((MASZT_X, MASZT_Y, GR_PODWOZIA))
    )
    # otwor na sruba blokujaca, w poprzek rury
    otwor_sruby = (
        cq.Workplane("YZ")
        .circle(SRUBA_BLOKUJACA_OTWOR / 2)
        .extrude(MAST_ZEW_OD)
        .translate((MASZT_X - MAST_ZEW_OD / 2, MASZT_Y, SRUBA_BLOKUJACA_WYSOKOSC))
    )

    return baza.union(rura_zew).cut(otwor_sruby)


def kolo_napedowe():
    """Jedno kolo napedowe - cylinder z faza na obu krawedziach, os wzdluz Y
    (uwaga: 'XZ' ma normalna wzdluz Y w cadquery, stad wyciagniecie idzie w
    Y, nie w X). Bez fazy plaski krazek wygladal jak moneta doklejona do
    boku, nie jak kolo - sama faza to tansze przyblizenie opony niz pelny
    bieznik, ale wystarcza, zeby sie tak CZYTALO na pierwszy rzut oka.
    PLACEHOLDER: nadal bez biezniku/piasty - to obwiednia rozmiaru, nie
    gotowa czesc do druku (opona to gotowy kupny element)."""
    kolo = cq.Workplane("XZ").circle(KOLO_SREDNICA / 2).extrude(KOLO_SZEROKOSC)
    kolo = kolo.faces(">Y").edges().chamfer(KOLO_FAZA)
    kolo = kolo.faces("<Y").edges().chamfer(KOLO_FAZA)
    return kolo


def kola_napedowe():
    """Dwa kola napedowe na wlasciwych miejscach - ta sama pozycja X co
    otwory mocujace silnik, oparte wewnetrzna sciana o krawedz podwozia i
    wystajace na zewnatrz."""
    kolo = kolo_napedowe()
    bryla = None
    for znak in (-1, 1):
        # Workplane("XZ").extrude(+) w cadquery idzie w -Y, nie +Y - stad ta
        # pozornie "odwrotna" przypisanie wzgledem znak; sprawdzone dopiero
        # po eksporcie (bounds w Y wyszly przesuniete o cala szerokosc kola).
        y = (SZ_PODWOZIA / 2 + KOLO_SZEROKOSC) if znak > 0 else (-SZ_PODWOZIA / 2)
        k = kolo.translate((MOTOR_X, y, KOLO_OS_Z))
        bryla = k if bryla is None else bryla.union(k)
    return bryla


def kolka_samonastawne_bryla():
    """Dwa przednie kolka - TA SAMA bryla co kolo_napedowe(), nie kulka. Cztery
    identyczne kola czytaja sie jako zaprojektowany produkt; kula obok walca
    wygladala jak dwa przypadkowe klocki. Mechanizm skretu (widelka) to
    osobny, kupny element - to nadal obwiednia rozmiaru, nie gotowa czesc."""
    kolo = kolo_napedowe()
    bryla = None
    for znak in (-1, 1):
        y = (CASTER_Y + KOLO_SZEROKOSC) if znak > 0 else -CASTER_Y
        k = kolo.translate((CASTER_X, y, KOLO_OS_Z))
        bryla = k if bryla is None else bryla.union(k)
    return bryla


def maszt_wewnetrzny():
    """Rura wsuwana w podwozie plus platforma na kamere na szczycie."""
    rura = (
        cq.Workplane("XY")
        .circle(MAST_WEWN_OD / 2)
        .circle(MAST_WEWN_OD / 2 - MAST_WEWN_GRUBOSC)
        .extrude(MAST_WEWN_WYSOKOSC)
    )

    platforma = (
        cq.Workplane("XY")
        .box(*KAMERA_PLYTKA, centered=(True, True, False))
        .translate((0, 0, MAST_WEWN_WYSOKOSC))
        .edges("|Z")
        .fillet(3)
    )

    for dx in (-KAMERA_ROZSTAW_X / 2, KAMERA_ROZSTAW_X / 2):
        for dy in (-KAMERA_ROZSTAW_Y / 2, KAMERA_ROZSTAW_Y / 2):
            otwor = (
                cq.Workplane("XY")
                .circle(KAMERA_OTWOR / 2)
                .extrude(KAMERA_PLYTKA[2] + 2)
                .translate((dx, dy, MAST_WEWN_WYSOKOSC - 1))
            )
            platforma = platforma.cut(otwor)

    # platforma jest szersza niz rura, wiec stoi na jej scianie jak grzybek
    return rura.union(platforma)


if __name__ == "__main__":
    katalog = pathlib.Path(__file__).parent

    p = podwozie()
    m = maszt_wewnetrzny()

    cq.exporters.export(p, str(katalog / "podwozie.stl"))
    cq.exporters.export(p, str(katalog / "podwozie.step"))
    cq.exporters.export(m, str(katalog / "maszt_wewnetrzny.stl"))
    cq.exporters.export(m, str(katalog / "maszt_wewnetrzny.step"))

    wysuw_max = MAST_ZEW_WYSOKOSC + MAST_WEWN_WYSOKOSC - 60   # 60mm minimalnego zakladu
    print(f"podwozie: {DL_PODWOZIA:.0f} x {SZ_PODWOZIA:.0f} mm")
    print(f"maszt zlozony: {MAST_ZEW_WYSOKOSC:.0f} mm nad podwoziem")
    print(f"maszt wysuniety maksymalnie: ~{wysuw_max:.0f} mm nad podwoziem")
    print("zapisano -> podwozie.stl, podwozie.step, maszt_wewnetrzny.stl, maszt_wewnetrzny.step")
