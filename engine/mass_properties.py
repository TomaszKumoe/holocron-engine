"""Prawdziwa masa i tensor bezwaldnosci z bryly STEP, zamiast placeholderow.

Test na pytanie: czy da sie to policzyc poprawnie bez AI, samą geometrią.

    python mass_properties.py <plik.step> [gestosc_g_cm3]

Wspolrzedne w pliku STEP sa w mm (jak caly katalog robot/). Wynik w
jednostkach URDF: kg dla masy, kg*m^2 dla bezwladnosci, m dla srodka masy.
"""

import sys

import cadquery as cq
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps

MM3_TO_M3 = 1e-9  # mm^3 -> m^3
MM_TO_M = 1e-3


def policz(sciezka_step: str, gestosc_g_cm3: float = 1.24, infill_procent: float = 100.0):
    """gestosc domyslna 1.24 g/cm3 = PLA, typowy filament do druku 3D.

    infill_procent skaluje objetosc/masa/bezwladnosc liniowo wg wypelnienia
    druku (np. 20 dla typowych 20%). To PRZYBLIZENIE z jedna wada w dol:
    ignoruje pelne, lite scianki (perimeter/top/bottom layers) drukarki -
    prawdziwa wydrukowana czesc jest ciezsza niz ten wynik, bo scianki sa
    zawsze 100% lite niezaleznie od infillu. Podaj 100 (domyslnie) dla
    gornej granicy (lita bryla), nizsza wartosc dla dolnej granicy.
    """
    shape = cq.importers.importStep(sciezka_step).val()

    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape.wrapped, props)

    objetosc_mm3 = props.Mass()  # dla VolumeProperties "Mass" to objetosc
    gestosc_kg_m3 = gestosc_g_cm3 * 1000.0 * (infill_procent / 100.0)
    masa_kg = objetosc_mm3 * MM3_TO_M3 * gestosc_kg_m3

    com = props.CentreOfMass()
    srodek_masy_m = (com.X() * MM_TO_M, com.Y() * MM_TO_M, com.Z() * MM_TO_M)

    inercja_wzgledem_com = GProp_GProps(com)
    BRepGProp.VolumeProperties_s(shape.wrapped, inercja_wzgledem_com)
    macierz = inercja_wzgledem_com.MatrixOfInertia()

    # OCC liczy bezwladnosc dla jednostkowej gestosci * objetosc w mm^5,
    # przeskalowanie: mm^2 -> m^2 (bo to juz jest * masa mm^3) razy gestosc
    skala = MM3_TO_M3 * (MM_TO_M ** 2) * gestosc_kg_m3
    ixx = macierz.Value(1, 1) * skala
    iyy = macierz.Value(2, 2) * skala
    izz = macierz.Value(3, 3) * skala
    ixy = macierz.Value(1, 2) * skala
    ixz = macierz.Value(1, 3) * skala
    iyz = macierz.Value(2, 3) * skala

    return {
        "masa_kg": masa_kg,
        "objetosc_mm3": objetosc_mm3,
        "srodek_masy_m": srodek_masy_m,
        "ixx": ixx, "iyy": iyy, "izz": izz,
        "ixy": ixy, "ixz": ixz, "iyz": iyz,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uzycie: python mass_properties.py <plik.step> [gestosc_g_cm3] [infill_procent]")
        sys.exit(1)

    sciezka = sys.argv[1]
    gestosc = float(sys.argv[2]) if len(sys.argv) > 2 else 1.24
    infill = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0

    gora = policz(sciezka, gestosc, 100.0)
    print(f"plik: {sciezka}  (gestosc={gestosc} g/cm3)")
    print(f"  objetosc bryly: {gora['objetosc_mm3']:.1f} mm^3")
    print(f"  masa (gorna granica, lita bryla): {gora['masa_kg']:.4f} kg")

    if infill < 100.0:
        dol = policz(sciezka, gestosc, infill)
        print(f"  masa (dolna granica, {infill:.0f}% infill, ignoruje lite scianki): {dol['masa_kg']:.4f} kg")
        print(f"  -> prawdziwa wydrukowana masa jest miedzy tymi dwiema wartosciami")
        wynik = dol
    else:
        wynik = gora

    print(f"  srodek masy (m): {wynik['srodek_masy_m']}")
    print(f"  inertia <inertial> do URDF (dla wybranej masy):")
    print(
        f'  <inertia ixx="{wynik["ixx"]:.6e}" ixy="{wynik["ixy"]:.6e}" '
        f'ixz="{wynik["ixz"]:.6e}" iyy="{wynik["iyy"]:.6e}" '
        f'iyz="{wynik["iyz"]:.6e}" izz="{wynik["izz"]:.6e}"/>'
    )
