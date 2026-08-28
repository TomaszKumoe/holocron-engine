"""Pozycje poszczegolnych czesci robota w zlozeniu - te same liczby co w
export_urdf.py (jedno zrodlo prawdy: dostawca.py/ramie.py/kosz.py/...),
ale jako plaska lista JSON do ustawienia osobnych mesh-y we frontendzie,
zamiast jednej zlaczonej bryly ktorej nie da sie rozbic na czesci do
przesuwania/obracania.

    python layout.py   -> drukuje JSON

Rotacje tylko tam gdzie geometria czesci jest "lokalna" (zerowana we
wlasnym stawie, patrz naglowek export_urdf.py) - bark/przedramie ramienia.
Reszta to zwykle przesuniecie XYZ w mm.
"""

import json
import pathlib
import sys

KATALOG_ROBOT = pathlib.Path(__file__).parent / "robot_czesci"
sys.path.insert(0, str(KATALOG_ROBOT))
import dostawca  # noqa: E402
import ramie  # noqa: E402
import kosz as kosz_modul  # noqa: E402
import platforma_elektroniki as elektronika  # noqa: E402

RAMIE_X, RAMIE_Y = -280.0, 150.0
KOSZ_X, KOSZ_Y = 60.0, 0.0
AKUM_X, AKUM_Y = 190.0, 0.0


def uklad() -> list[dict]:
    kosz_z = dostawca.GR_PODWOZIA + kosz_modul.NOZKA_WYS

    czesci = [
        {"nazwa": "podwozie", "x": 0, "y": 0, "z": 0},
        {"nazwa": "kosz", "x": KOSZ_X, "y": KOSZ_Y, "z": kosz_z},
        {"nazwa": "platforma_elektroniki", "x": KOSZ_X, "y": KOSZ_Y, "z": elektronika.Z_NA_PODWOZIU},
        {
            # prawdziwy model Arduino Uno R3 (GLB, skala 1:1, ~350 nazwanych
            # siatek) zamiast dawnej makiety-bryly. GLB jest eksportowany
            # Y-up w metrach (standard glTF) - frontend przelicza na
            # Z-up/mm sam (patrz wczytajCzescGlb w index.html), stad
            # rot_deg=90 (koryguje os "gora") i skala=1000 (m -> mm).
            # Pozycja to ta sama matematyka co w arduino_makieta()
            # w platforma_elektroniki.py: origin GLB siedzi w srodku
            # plytki/na jej spodzie, wiec doklejamy y=ARDUINO_SRODEK_Y i
            # z=grubosc plyty + kolki dystansowe, tak samo jak tam.
            "nazwa": "arduino_uno_r3",
            "x": KOSZ_X, "y": KOSZ_Y + elektronika.ARDUINO_SRODEK_Y,
            "z": elektronika.Z_NA_PODWOZIU + elektronika.PLYTA_GRUBOSC + elektronika.KOLEK_WYS,
            "rot_os": "x", "rot_deg": 90,
            "format": "glb", "sciezka": "assets/arduino-uno-r3.glb", "skala": 1000,
        },
        {
            # prawdziwy model Raspberry Pi 4B (GLB, skala 1:1) zamiast dawnej
            # makiety-bryly - ta sama matematyka pozycji co arduino_uno_r3
            # powyzej (origin GLB w srodku plytki/na jej spodzie).
            "nazwa": "raspberry_pi_4b",
            "x": KOSZ_X, "y": KOSZ_Y + elektronika.RPI_SRODEK_Y,
            "z": elektronika.Z_NA_PODWOZIU + elektronika.PLYTA_GRUBOSC + elektronika.KOLEK_WYS,
            "rot_os": "x", "rot_deg": 90,
            "format": "glb", "sciezka": "assets/raspberry-pi-4b.glb", "skala": 1000,
        },
        {"nazwa": "akumulator", "x": AKUM_X, "y": AKUM_Y, "z": dostawca.GR_PODWOZIA},
        {"nazwa": "kola_napedowe", "x": dostawca.MOTOR_X, "y": -dostawca.SZ_PODWOZIA / 2, "z": dostawca.KOLO_OS_Z},
        {"nazwa": "ramie_maszt", "x": RAMIE_X, "y": RAMIE_Y, "z": dostawca.GR_PODWOZIA},
        {
            "nazwa": "ramie_podstawa",
            "x": RAMIE_X, "y": RAMIE_Y, "z": dostawca.GR_PODWOZIA + ramie.MASZT_WYSOKOSC,
        },
        {
            # bark jest "lokalny" (zerowany we wlasnym stawie) - stawiamy go
            # na szczycie podstawy i obracamy o BARK_KAT wokol osi X, tak jak
            # robi to prawdziwy staw (patrz ramie.py: bark() vs bark_lokalny())
            "nazwa": "ramie_bark",
            "x": RAMIE_X, "y": RAMIE_Y, "z": dostawca.GR_PODWOZIA + ramie.MASZT_WYSOKOSC + ramie.BAZA_WYSOKOSC,
            "rot_os": "x", "rot_deg": ramie.BARK_KAT,
        },
        {
            # przedramie startuje na koncu barku (dlugosc BARK_DLUGOSC wzdluz
            # OBROCONEJ osi Z barku) - przyblizenie: przesuwamy wzdluz kierunku
            # nachylenia barku, tak jak liczy to ramie.py (przedramie_polozenie)
            "nazwa": "ramie_przedramie",
            "x": RAMIE_X - ramie.BARK_DLUGOSC * __import__("math").sin(__import__("math").radians(ramie.BARK_KAT)),
            "y": RAMIE_Y,
            "z": (
                dostawca.GR_PODWOZIA + ramie.MASZT_WYSOKOSC + ramie.BAZA_WYSOKOSC
                + ramie.BARK_DLUGOSC * __import__("math").cos(__import__("math").radians(ramie.BARK_KAT))
            ),
            "rot_os": "x", "rot_deg": ramie.BARK_KAT + ramie.PRZEDRAMIE_KAT,
        },
    ]
    return czesci


def uklad_wygenerowane() -> list[dict]:
    """Czesci ktore silnik SAM wygenerowal z parametrow (generuj.py) -
    odsuniete od robota-hobby, zeby bylo jasne ze to nie ten sam material."""
    czesci = [
        {"nazwa": "przyklad_baza", "x": 600.0, "y": 0.0, "z": 0.0},
        {"nazwa": "dron_v1", "x": 600.0, "y": 500.0, "z": 0.0},
    ]
    # llm_wynik powstaje dopiero na zadanie z czatu (llm_cad.py) - dodajemy
    # do ukladu tylko jesli plik juz istnieje.
    wygenerowane_dir = pathlib.Path(__file__).parent.parent / "wygenerowane"
    if (wygenerowane_dir / "llm_wynik.step").exists():
        czesci.append({"nazwa": "llm_wynik", "x": 600.0, "y": -500.0, "z": 0.0})
    return czesci


if __name__ == "__main__":
    print(json.dumps(uklad() + uklad_wygenerowane(), indent=2))
