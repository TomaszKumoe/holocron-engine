"""Platforma elektroniki: plaska polka na Raspberry Pi i Arduino, stojaca nad
podwoziem na czterech nozkach.

    python robot/platforma_elektroniki.py

Dotychczas znaczniki.py pokazywaly tylko GDZIE na podwoziu maja stanac plyty
(strefa "mozg" w x=-15, y=-55/+55) - same krazki, bez realnego miejsca do
przykrecenia. Ta plyta jest tym realnym miejscem: kolki dystansowe pod obie
plyty plus cztery nozki, ktore podnosza cala polke nad podwozie i licuja z
tymi samymi wspolrzednymi co znaczniki, wiec drugi plik nie klamie.

Dwa poziomy pewnosci wymiarow:
  Raspberry Pi 4B - siatka otworow 58 x 49 mm, otwor 2.7mm, znany, oficjalny
                     rysunek mechaniczny Raspberry Pi Foundation. Mozna ufac.
  Arduino Uno R3  - siatka otworow NIE jest symetryczna i regularnie bywa
                     zrodlem pomylek nawet w gotowych projektach shieldow.
                     Wartosci ponizej to PLACEHOLDER - zmierz swoja plytke
                     suwmiarka przed wierceniem/drukiem, tak jak przy serwie
                     w chwytak.py.
"""

import pathlib

import cadquery as cq

# ── plyta ────────────────────────────────────────────────────────────────
PLYTA_DL = 170.0     # wzdluz Y - mieisci obie plytki jedna za druga
PLYTA_SZER = 90.0    # wzdluz X
PLYTA_GRUBOSC = 3.0
PROMIEN_NAROZY = 6.0

# ── nozki podnoszace polke nad podwozie ─────────────────────────────────
NOZKA_WYS = 15.0          # PLACEHOLDER - tyle, zeby zmiescic zlacza/luty pod plytkami
NOZKA_SREDNICA = 8.0
NOZKA_OTWOR = 3.2         # M3, do przykrecenia w podwozie
# nozki w rogach plyty, z zapasem od krawedzi
NOZKA_ROG_ODSTEP = 10.0

# ── Raspberry Pi 4B - siatka pewna, z oficjalnego rysunku ──────────────────
RPI_PLYTKA = (85.0, 56.0)
RPI_OTWOR_SIATKA = (58.0, 49.0)
RPI_OTWOR_ROG_ODSTEP = 3.5     # od rogu footprintu do najblizszego otworu
RPI_OTWOR = 2.7
RPI_SRODEK_Y = -55.0            # ten sam punkt co U1 w znaczniki.py

# ── Arduino Uno R3 - PLACEHOLDER, zmierz przed wierceniem ─────────────────
ARDUINO_PLYTKA = (68.6, 53.4)
ARDUINO_OTWOR_SIATKA = (50.8, 48.3)   # przyblizone - siatka Uno nie jest symetryczna
ARDUINO_OTWOR_ROG_ODSTEP = (9.0, 2.5)
ARDUINO_OTWOR = 2.8
ARDUINO_SRODEK_Y = 55.0          # ten sam punkt co U2 w znaczniki.py

KOLEK_WYS = 5.0            # wysokosc kolkow dystansowych pod kazda plytka
KOLEK_SREDNICA = 6.0
KOLEK_OTWOR = 2.2           # pilotowy pod wkret samogwintujacy M2.5

# ── pozycja WZGLEDEM MASZTU (nie wzgledem podwozia wprost!) - potrzebna do
# zestaw.py ─────────────────────────────────────────────────────────────
# Platforma stoi w strefie "mozg" ze znaczniki.py, x=-15 WZGLEDEM MASZTU.
# Kiedys maszt siedzial w srodku podwozia (0,0), wiec ten offset byl tez
# pozycja na podwoziu wprost - po dodaniu kosza i ramienia maszt przeniosl
# sie w dostawca.MASZT_X/MASZT_Y, a ta stala zostaje TAKA SAMA (bo liczy sie
# tylko wzgledem masztu). Zestaw.py dodaje dostawca.MASZT_X/Y, zeby dostac
# prawdziwa pozycje na podwoziu.
X_NA_PODWOZIU = -15.0
Y_WZGLEDEM_MASZTU = 0.0
GR_PODWOZIA = 6.0            # ta sama stala co w dostawca.py - podwozie tam jest zrodlem prawdy
Z_NA_PODWOZIU = GR_PODWOZIA + NOZKA_WYS

MASZT_ZEW_OD = 24.0           # ta sama stala co w dostawca.py
MASZT_LUZ = 3.0                # promien otworu > promien rury, zeby plyta na nia nie napierala
MASZT_OTWOR_SREDNICA = MASZT_ZEW_OD + 2 * MASZT_LUZ
MASZT_OTWOR_X = -X_NA_PODWOZIU   # = 15.0 - lokalny x, ktory trafia w pozycje masztu
MASZT_OTWOR_Y = -Y_WZGLEDEM_MASZTU


def kolki_pod_plytke(srodek_x, srodek_y, footprint, siatka, rog_odstep):
    """Cztery kolki dystansowe + otwory pilotowe pod jedna plytke (RPi/Arduino).

    rog_odstep moze byc liczba (ten sam odstep w X i Y) albo para (x, y) -
    Arduino potrzebuje pary, bo jego siatka nie jest symetryczna.
    """
    if isinstance(rog_odstep, tuple):
        odstep_x, odstep_y = rog_odstep
    else:
        odstep_x = odstep_y = rog_odstep

    naroznik_x = srodek_x - footprint[0] / 2
    naroznik_y = srodek_y - footprint[1] / 2

    bryla = None
    for dx in (0, siatka[0]):
        for dy in (0, siatka[1]):
            x = naroznik_x + odstep_x + dx
            y = naroznik_y + odstep_y + dy
            kolek = (
                cq.Workplane("XY")
                .circle(KOLEK_SREDNICA / 2)
                .extrude(KOLEK_WYS)
                .translate((x, y, PLYTA_GRUBOSC))
            )
            otwor = (
                cq.Workplane("XY")
                .circle(KOLEK_OTWOR / 2)
                .extrude(KOLEK_WYS + PLYTA_GRUBOSC + 2)
                .translate((x, y, -1))
            )
            kolek = kolek.cut(otwor)
            bryla = kolek if bryla is None else bryla.union(kolek)
    return bryla


def platforma():
    plyta = (
        cq.Workplane("XY")
        .box(PLYTA_SZER, PLYTA_DL, PLYTA_GRUBOSC, centered=(True, True, False))
        .edges("|Z")
        .fillet(PROMIEN_NAROZY)
    )

    # cztery nozki w rogach, licza sie od krawedzi plyty w dol do podwozia
    for dx in (-1, 1):
        for dy in (-1, 1):
            x = dx * (PLYTA_SZER / 2 - NOZKA_ROG_ODSTEP)
            y = dy * (PLYTA_DL / 2 - NOZKA_ROG_ODSTEP)
            nozka = (
                cq.Workplane("XY")
                .circle(NOZKA_SREDNICA / 2)
                .extrude(NOZKA_WYS)
                .translate((x, y, -NOZKA_WYS))
            )
            otwor = (
                cq.Workplane("XY")
                .circle(NOZKA_OTWOR / 2)
                .extrude(NOZKA_WYS + PLYTA_GRUBOSC + 2)
                .translate((x, y, -NOZKA_WYS - 1))
            )
            nozka = nozka.cut(otwor)
            plyta = plyta.union(nozka)

    # przeswit na rure masztu (dostawca.py) - bez tego maszt przebijalby plyte
    maszt_otwor = (
        cq.Workplane("XY")
        .circle(MASZT_OTWOR_SREDNICA / 2)
        .extrude(PLYTA_GRUBOSC + KOLEK_WYS + 2)
        .translate((MASZT_OTWOR_X, MASZT_OTWOR_Y, -1))
    )
    plyta = plyta.cut(maszt_otwor)

    plyta = plyta.union(
        kolki_pod_plytke(0, RPI_SRODEK_Y, RPI_PLYTKA, RPI_OTWOR_SIATKA, RPI_OTWOR_ROG_ODSTEP)
    )
    plyta = plyta.union(
        kolki_pod_plytke(
            0, ARDUINO_SRODEK_Y, ARDUINO_PLYTKA, ARDUINO_OTWOR_SIATKA, ARDUINO_OTWOR_ROG_ODSTEP
        )
    )

    return plyta


# ── makieta Arduino - sylwetka do sprawdzania kolizji, NIE dokladny model.
# Sam prostokat plytki byl mylacy (wygladal jak dowolna plyta, nie jak
# Arduino) - port USB-B i gniazdo zasilania sterczace POZA krawedz plytki to
# jest wlasnie to, co realnie moze sie z czyms zderzyc, wiec to one sa tu
# najwazniejsze, nie estetyka. Pozycje portow - przyblizone z pamieci wygladu
# Uno R3, NIE zmierzone z rysunku - traktuj jak PLACEHOLDER tak samo jak
# siatke otworow powyzej. ────────────────────────────────────────────────
ARDUINO_GRUBOSC_PLYTKI = 1.6   # typowa grubosc PCB

USB_ROZMIAR = (12.0, 16.0, 11.0)   # glebokosc (poza krawedz), szerokosc, wysokosc
USB_Y_OFFSET = -14.0                # od srodka krotszej krawedzi plytki

ZASILANIE_SREDNICA = 9.0
ZASILANIE_GLEBOKOSC = 9.0
ZASILANIE_Y_OFFSET = 4.0

# rzedy pinow - gora i dol plytki, jako uproszczone listwy (nie pojedyncze nozki)
PIN_LISTWA_WYS = 2.5
PIN_LISTWA_GLEBOKOSC = 2.5


def arduino_makieta():
    z_spod = PLYTA_GRUBOSC + KOLEK_WYS
    x0 = -ARDUINO_PLYTKA[0] / 2   # krawedz, z ktorej sterczy USB/zasilanie
    srodek_y = ARDUINO_SRODEK_Y

    plytka = cq.Workplane("XY").box(
        ARDUINO_PLYTKA[0], ARDUINO_PLYTKA[1], ARDUINO_GRUBOSC_PLYTKI, centered=(True, True, False)
    )

    usb = (
        cq.Workplane("XY")
        .box(*USB_ROZMIAR, centered=(False, True, False))
        .translate((x0 - USB_ROZMIAR[0], USB_Y_OFFSET, ARDUINO_GRUBOSC_PLYTKI))
    )
    # cylinder wzdluz X, wystaje na zewnatrz (w -X) poza krawedz plytki x0
    zasilanie = (
        cq.Workplane("YZ")
        .circle(ZASILANIE_SREDNICA / 2)
        .extrude(-ZASILANIE_GLEBOKOSC)
        .translate((x0, ZASILANIE_Y_OFFSET, ARDUINO_GRUBOSC_PLYTKI + ZASILANIE_SREDNICA / 2))
    )

    # dwie listwy pinow wzdluz dluzszych krawedzi, na gornej stronie plytki
    piny = None
    for y_krawedz in (-ARDUINO_PLYTKA[1] / 2, ARDUINO_PLYTKA[1] / 2 - PIN_LISTWA_GLEBOKOSC):
        listwa = (
            cq.Workplane("XY")
            .box(
                ARDUINO_PLYTKA[0] * 0.75,
                PIN_LISTWA_GLEBOKOSC,
                PIN_LISTWA_WYS,
                centered=(True, False, False),
            )
            .translate((0, y_krawedz, ARDUINO_GRUBOSC_PLYTKI))
        )
        piny = listwa if piny is None else piny.union(listwa)

    calosc = plytka.union(usb).union(zasilanie).union(piny)
    return calosc.translate((0, srodek_y, z_spod))


# ── makieta Raspberry Pi 4B - sylwetka do sprawdzania kolizji i do tego,
# zeby na pierwszy rzut oka bylo widac "to jest RPi", nie plaski prostokat.
# Ulozenie portow jak w prawdziwym RPi 4B: GPIO wzdluz jednej dluzszej
# krawedzi, Ethernet+USB wzdluz przeciwnej, USB-C zasilania i 2x micro-HDMI
# na jednej krotszej krawedzi. Wymiary portow - przyblizone z wygladu
# plytki, PLACEHOLDER tak jak w arduino_makieta, wymiary samej plytki i
# siatki otworow (RPI_PLYTKA/RPI_OTWOR_SIATKA) sa pewne (patrz naglowek). ──
RPI_GRUBOSC_PLYTKI = 1.4

RPI_GPIO_ROZMIAR = (51.0, 5.0, 8.5)   # dlugosc wzdluz krawedzi, glebokosc, wysokosc
RPI_GPIO_Y_OFFSET = 3.5                 # od krawedzi do srodka listwy

RPI_ETH_ROZMIAR = (16.0, 13.5, 13.5)   # RJ45, na dolnej krawedzi (dluzszej), lewa strona
RPI_ETH_X_OFFSET = -22.0

RPI_USB_ROZMIAR = (15.0, 13.5, 15.5)   # stos 2xUSB3+2xUSB2, ta sama krawedz co Ethernet, prawa strona
RPI_USB_X_OFFSET = 8.0

RPI_USBC_ROZMIAR = (9.0, 7.5, 3.2)     # zasilanie, krotsza krawedz
RPI_USBC_Y_OFFSET = -19.0

RPI_HDMI_ROZMIAR = (7.0, 5.5, 3.5)     # 2x micro-HDMI, ta sama krotsza krawedz co USB-C
RPI_HDMI_Y_OFFSETY = (-8.0, 1.0)


def rpi_makieta():
    z_spod = PLYTA_GRUBOSC + KOLEK_WYS
    srodek_y = RPI_SRODEK_Y
    x_lewa = -RPI_PLYTKA[0] / 2   # krawedz z USB-C/HDMI
    y_dol = -RPI_PLYTKA[1] / 2     # krawedz z Ethernet/USB, przeciwna do GPIO
    y_gora = RPI_PLYTKA[1] / 2     # krawedz z GPIO

    plytka = cq.Workplane("XY").box(
        RPI_PLYTKA[0], RPI_PLYTKA[1], RPI_GRUBOSC_PLYTKI, centered=(True, True, False)
    )

    gpio = (
        cq.Workplane("XY")
        .box(RPI_GPIO_ROZMIAR[0], RPI_GPIO_ROZMIAR[1], RPI_GPIO_ROZMIAR[2], centered=(True, False, False))
        .translate((0, y_gora - RPI_GPIO_Y_OFFSET - RPI_GPIO_ROZMIAR[1], RPI_GRUBOSC_PLYTKI))
    )

    eth = (
        cq.Workplane("XY")
        .box(RPI_ETH_ROZMIAR[1], RPI_ETH_ROZMIAR[0], RPI_ETH_ROZMIAR[2], centered=(True, False, False))
        .translate((RPI_ETH_X_OFFSET, y_dol - RPI_ETH_ROZMIAR[1], RPI_GRUBOSC_PLYTKI))
    )

    usb = (
        cq.Workplane("XY")
        .box(RPI_USB_ROZMIAR[1], RPI_USB_ROZMIAR[0], RPI_USB_ROZMIAR[2], centered=(True, False, False))
        .translate((RPI_USB_X_OFFSET, y_dol - RPI_USB_ROZMIAR[1], RPI_GRUBOSC_PLYTKI))
    )

    usbc = (
        cq.Workplane("YZ")
        .rect(RPI_USBC_ROZMIAR[1], RPI_USBC_ROZMIAR[2])
        .extrude(-RPI_USBC_ROZMIAR[0])
        .translate((x_lewa, RPI_USBC_Y_OFFSET, RPI_GRUBOSC_PLYTKI + RPI_USBC_ROZMIAR[2] / 2))
    )

    hdmi = None
    for y_off in RPI_HDMI_Y_OFFSETY:
        port = (
            cq.Workplane("YZ")
            .rect(RPI_HDMI_ROZMIAR[1], RPI_HDMI_ROZMIAR[2])
            .extrude(-RPI_HDMI_ROZMIAR[0])
            .translate((x_lewa, y_off, RPI_GRUBOSC_PLYTKI + RPI_HDMI_ROZMIAR[2] / 2))
        )
        hdmi = port if hdmi is None else hdmi.union(port)

    calosc = plytka.union(gpio).union(eth).union(usb).union(usbc).union(hdmi)
    return calosc.translate((0, srodek_y, z_spod))


if __name__ == "__main__":
    katalog = pathlib.Path(__file__).parent

    model = platforma()
    cq.exporters.export(model, str(katalog / "platforma_elektroniki.stl"))
    cq.exporters.export(model, str(katalog / "platforma_elektroniki.step"))

    arduino = arduino_makieta()
    cq.exporters.export(arduino, str(katalog / "arduino_makieta.stl"))
    cq.exporters.export(arduino, str(katalog / "arduino_makieta.step"))

    rpi = rpi_makieta()
    cq.exporters.export(rpi, str(katalog / "rpi_makieta.stl"))
    cq.exporters.export(rpi, str(katalog / "rpi_makieta.step"))

    print(f"plyta: {PLYTA_SZER:.0f} x {PLYTA_DL:.0f} x {PLYTA_GRUBOSC:.0f} mm")
    print(f"nozki podnosza polke {NOZKA_WYS:.0f}mm nad podwozie, otwory pod M3")
    print(f"RPi 4B: siatka {RPI_OTWOR_SIATKA[0]:.0f}x{RPI_OTWOR_SIATKA[1]:.0f}mm - pewne wymiary")
    print(f"Arduino Uno: siatka {ARDUINO_OTWOR_SIATKA[0]:.1f}x{ARDUINO_OTWOR_SIATKA[1]:.1f}mm - PLACEHOLDER, zmierz plytke")
    print("zapisano -> platforma_elektroniki.stl/.step, arduino_makieta.stl/.step (makieta - nie prawdziwy model)")
