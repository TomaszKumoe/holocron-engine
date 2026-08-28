"""Pokazuje bryle na ekranie w interaktywnym oknie 3D (VTK) - nie tekst
w terminalu. To pierwsza odpowiedz na "brak petli wizualnej": zanim
cokolwiek policzymy o czesci, mamy ja zobaczyc.

    python viewer.py <plik.step> [<plik2.step> ...]
"""

import sys

import cadquery as cq
import cadquery.vis as vis


def pokaz(sciezki_step: list[str]):
    bryly = [cq.importers.importStep(s).val() for s in sciezki_step]
    print(f"otwieram okno 3D z {len(bryly)} bryla/bryłami - obracaj myszka, zamknij X")
    vis.show(*bryly)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uzycie: python viewer.py <plik.step> [<plik2.step> ...]")
        sys.exit(1)
    pokaz(sys.argv[1:])
