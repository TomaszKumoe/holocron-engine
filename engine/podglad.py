"""Mechanizm 'renderuj i spojrz' - ten sam co widac w historii czatu Claude
Design ("Slimming fenders...", "Finishing up"): zamiast jednego strzalu na
slepo, kazda zmiana geometrii/materialu/oswietlenia dostaje zrzut ekranu,
ktory agent MOZE ocenic zanim uzna cos za gotowe. To czesc silnika, nie
recznie powtarzany nawyk w czacie - moze wywolac to kazdy przyszly proces,
nie tylko ja w tej rozmowie.

    python podglad.py [url] [plik_wyjsciowy.png]

Domyslnie: http://localhost:8300 -> zrzuty/podglad.png
"""

import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

KATALOG = pathlib.Path(__file__).parent
ZRZUTY = KATALOG / "zrzuty"
ZRZUTY.mkdir(exist_ok=True)


def zrob_zrzut(url: str = "http://localhost:8300", plik: str | None = None, czekaj_s: float = 2.0) -> pathlib.Path:
    """Otwiera url w headless przegladarce, czeka az sceny/modele sie
    zaladuja, zapisuje zrzut ekranu. Zwraca sciezke do pliku - Claude
    (lub inny agent) czyta go narzedziem Read, zeby ocenic wynik."""
    sciezka = pathlib.Path(plik) if plik else ZRZUTY / "podglad.png"

    with sync_playwright() as p:
        przegladarka = p.chromium.launch()
        strona = przegladarka.new_page(viewport={"width": 1600, "height": 1000})
        bledy_konsoli = []
        strona.on("console", lambda msg: bledy_konsoli.append(msg.text) if msg.type == "error" else None)
        strona.goto(url)
        time.sleep(czekaj_s)  # czas na fetch modeli STL + pierwszy render
        strona.screenshot(path=str(sciezka))
        przegladarka.close()

    if bledy_konsoli:
        print("UWAGA - bledy w konsoli strony:")
        for b in bledy_konsoli:
            print(" ", b)

    return sciezka


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8300"
    plik = sys.argv[2] if len(sys.argv) > 2 else None
    wynik = zrob_zrzut(url, plik)
    print(f"zapisano -> {wynik}")
