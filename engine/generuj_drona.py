"""Pierwsza proba: rama drona wyscigowego, X-frame, 4 ramiona + korpus
centralny + mocowania silnikow. Pisane na zywo, sprawdzane renderem po
kazdej wersji - nie jeden strzal.

    python generuj_drona.py
"""

import math
import pathlib

import cadquery as cq

WYJscie = pathlib.Path(__file__).parent.parent / "wygenerowane"
WYJscie.mkdir(exist_ok=True)

ROZSTAW_SILNIKOW = 220.0   # mm, przekatna X-frame miedzy osiami silnikow
SZER_RAMIENIA = 18.0
GRUB_RAMIENIA = 6.0
SR_KORPUSU = 55.0
GRUB_KORPUSU = 8.0
SR_MOCOWANIA_SILNIKA = 8.0


def rama():
    r = ROZSTAW_SILNIKOW / 2

    korpus = (
        cq.Workplane("XY")
        .circle(SR_KORPUSU)
        .extrude(GRUB_KORPUSU)
    )

    model = korpus
    for znak_x, znak_y in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        kat = math.atan2(znak_y, znak_x)
        dx, dy = r * math.cos(kat), r * math.sin(kat)

        ramie = (
            cq.Workplane("XY")
            .center((dx) / 2, (dy) / 2)
            .transformed(rotate=(0, 0, math.degrees(kat)))
            .rect(math.hypot(dx, dy) + 20, SZER_RAMIENIA)
            .extrude(GRUB_RAMIENIA)
        )
        model = model.union(ramie)

        mocowanie = (
            cq.Workplane("XY")
            .center(dx, dy)
            .circle(SR_MOCOWANIA_SILNIKA * 1.8)
            .extrude(GRUB_RAMIENIA)
            .faces(">Z")
            .workplane()
            .polygon(4, SR_MOCOWANIA_SILNIKA * 1.6)
            .vertices()
            .hole(3.2)
        )
        model = model.union(mocowanie)

    model = model.edges("|Z").fillet(3.0)
    return model


if __name__ == "__main__":
    bryla = rama()
    sciezka = WYJscie / "dron_v1.step"
    cq.exporters.export(bryla, str(sciezka))
    print(f"zapisano -> {sciezka}")
