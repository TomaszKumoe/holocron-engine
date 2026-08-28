"""LLM (Claude Opus przez OpenRouter, ten sam klucz co Holocron Vision)
zamienia opis slowny na geometrie - bezpiecznie: model zwraca dane (JSON:
lista prymitywow/otworow), nie kod Pythona. Zero exec() na tekscie od
modelu - geometrie buduje wylacznie nasz wlasny, deterministyczny kod z
zwalidowanych liczb.

Po zbudowaniu bryly silnik SAM robi sobie zrzut ekranu (headless
przegladarka, ten sam mechanizm co engine/podglad.py) i pyta model o
ocene wizualna zanim pokaze wynik userowi - jedna runda poprawki, nie
zgadywanie za pierwszym razem.

Klucz czytany na zywo z holocron-vision/.env, nie kopiowany do tego repo.
"""

import base64
import json
import pathlib
import re
import tempfile
import urllib.request
from typing import Literal, Optional

import cadquery as cq
from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field, ValidationError, model_validator

ENV_HOLOCRON_VISION = pathlib.Path(r"c:\Users\tomas\holocron-vision\.env")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-opus-5"


class Prymityw(BaseModel):
    typ: Literal["box", "cylinder"]
    dlugosc: Optional[float] = Field(None, gt=0, le=2000)
    szerokosc: Optional[float] = Field(None, gt=0, le=2000)
    promien: Optional[float] = Field(None, gt=0, le=1000)
    wysokosc: float = Field(..., gt=0, le=1000)
    x: float = Field(0, ge=-2000, le=2000)
    y: float = Field(0, ge=-2000, le=2000)
    z: float = Field(0, ge=-1000, le=1000)
    kolor: Optional[str] = Field(
        None, pattern=r"^#[0-9a-fA-F]{6}$",
        description="hex np. #2b2f36 - kolor TEJ bryly w podgladzie (koło != nadwozie)",
    )


class Otwor(BaseModel):
    x: float = Field(..., ge=-2000, le=2000)
    y: float = Field(..., ge=-2000, le=2000)
    srednica: float = Field(..., gt=0, le=200)


class PlanGeometrii(BaseModel):
    bryly: list[Prymityw] = Field(..., min_length=1, max_length=40)
    otwory: list[Otwor] = Field(default_factory=list, max_length=100)
    fillet_promien: Optional[float] = Field(None, gt=0, le=100)


class OdpowiedzModelu(BaseModel):
    """Model wybiera jeden z dwóch trybow: zwykla rozmowa (czat) albo
    projekt czesci (geometria). Dzieki temu 'czesc' czy pytanie nie
    wpada juz na sile w generator CAD."""

    tryb: Literal["czat", "geometria"]
    odpowiedz: Optional[str] = None
    bryly: list[Prymityw] = Field(default_factory=list, max_length=40)
    otwory: list[Otwor] = Field(default_factory=list, max_length=100)
    fillet_promien: Optional[float] = Field(None, gt=0, le=100)

    @model_validator(mode="after")
    def _sprawdz_tryb(self):
        if self.tryb == "czat" and not (self.odpowiedz and self.odpowiedz.strip()):
            raise ValueError("tryb 'czat' wymaga niepustego pola 'odpowiedz'")
        if self.tryb == "geometria" and not self.bryly:
            raise ValueError("tryb 'geometria' wymaga co najmniej jednej bryly")
        return self


class OcenaWizualna(BaseModel):
    """Odpowiedz modelu po obejrzeniu zrzutu ekranu wlasnej geometrii."""

    ocena: Literal["dobrze", "popraw"]
    bryly: list[Prymityw] = Field(default_factory=list, max_length=40)
    otwory: list[Otwor] = Field(default_factory=list, max_length=100)
    fillet_promien: Optional[float] = Field(None, gt=0, le=100)

    @model_validator(mode="after")
    def _sprawdz(self):
        if self.ocena == "popraw" and not self.bryly:
            raise ValueError("ocena 'popraw' wymaga poprawionego pola 'bryly'")
        return self


SYSTEM_PROMPT = """Jestes asystentem w Holocron Engine - projektujesz czesci
robotow/dronow, ale umiesz tez normalnie porozmawiac (przywitanie, pytanie
o mozliwosci, cokolwiek co nie jest prosba o zaprojektowanie czesci).

Odpowiadasz WYLACZNIE jednym obiektem JSON (zaden markdown, zaden komentarz).
Sa dwa mozliwe ksztalty odpowiedzi - wybierz jeden, w zaleznosci od tego
czego chce uzytkownik:

1) Zwykla rozmowa (przywitanie, pytanie, cokolwiek bez konkretnej czesci
do zaprojektowania):
{"tryb": "czat", "odpowiedz": "krotka, naturalna odpowiedz po polsku"}

2) Prosba o zaprojektowanie konkretnej czesci:
{
  "tryb": "geometria",
  "bryly": [
    {"typ": "box", "dlugosc": 220, "szerokosc": 160, "wysokosc": 5, "x": 0, "y": 0, "z": 0, "kolor": "#2b2f36"},
    {"typ": "cylinder", "promien": 15, "wysokosc": 20, "x": 100, "y": 0, "z": 5, "kolor": "#1a1a1a"}
  ],
  "otwory": [{"x": 90, "y": 60, "srednica": 4}],
  "fillet_promien": 8
}

Dla trybu "geometria": jednostki to milimetry. "box" wymaga
dlugosc+szerokosc+wysokosc, "cylinder" wymaga promien+wysokosc. x/y/z to
srodek bryly u podstawy. Wszystkie bryly sklejaja sie w jedna (suma) w
pliku STEP, ale w podglacie kazda bryla renderuje sie swoim kolorem.
otwory przewiercaja cala grubosc od gory w punkcie x,y. fillet_promien
zaokragla pionowe krawedzie calosci (pomin jesli niepotrzebne). Kola
projektuj ZAWSZE jako "cylinder", nigdy jako "box" - kwadratowe kolo to
blad. Trzymaj sie realistycznych wymiarow dla robotyki/dronow.

"kolor" (opcjonalny hex, np. "#2b2f36") - nadaj sensowna, spojna
kolorystyke: kola/opony ciemniejszy/gumowy odcien, nadwozie/obudowa
inny kolor niz kola, akcenty (np. logo, listwy) mozesz wyroznic trzecim
kolorem. Nie generuj przypadkowych, niespojnych kolorow - trzymaj sie
malej, przemyslanej palety (2-3 kolory na czesc). Jesli user wprost
poda kolor ("czerwony robot"), uzyj go dla nadwozia.

WAZNE: domyslnie PROJEKTUJ, nie dopytuj. Jesli user nie poda wymiaru,
dobierz sam sensowna, typowa wartosc dla tego typu czesci (kolo robota:
~60-100mm srednicy; plyta montazowa: ~100-250mm; itd) i napisz w
odpowiedzi jakie zalozenia przyjales - nie blokuj generowania pytaniem.
Wybierz "czat" (pytanie) TYLKO gdy prosba jest tak niejasna ze nie da sie
zrobic zadnego rozsadnego zalozenia (np. w ogole nie wiadomo jaki to typ
czesci). Gdy user pisze "na oko"/"jak uwazasz"/"ty zdecyduj" - to wprost
zakaz pytania, zawsze wybierz "geometria" z twoimi wlasnymi zalozeniami.
Masz dostep do historii rozmowy - jesli user odnosi sie do czegos co juz
zaprojektowales ("popraw kola", "zrob wieksze"), uzyj poprzedniego planu
z historii jako punktu startowego, nie pytaj co to za projekt."""

SYSTEM_PROMPT_OCENA = """Widzisz zrzut ekranu bryly ktora sam przed chwila
zaprojektowales (ten sam format JSON co poprzednio) na prosbe uzytkownika.
Ocen szczerze czy wyglada dobrze - proporcje, czy nie jest przypadkowo
plaska/pusta/rozjechana, czy pasuje do opisu uzytkownika.

Odpowiedz WYLACZNIE jednym obiektem JSON:
- jesli wyglada dobrze: {"ocena": "dobrze"}
- jesli trzeba poprawic: {"ocena": "popraw", "bryly": [...], "otwory": [...],
  "fillet_promien": ...} - PELNY nowy plan w tym samym formacie co za
  pierwszym razem, z poprawiona geometria. Nie opisuj slownie co zle -
  od razu daj poprawiony plan."""


def _wczytaj_klucz() -> str:
    if not ENV_HOLOCRON_VISION.exists():
        return ""
    for linia in ENV_HOLOCRON_VISION.read_text(encoding="utf-8").splitlines():
        if linia.strip().startswith("OPENROUTER_API_KEY"):
            return linia.split("=", 1)[1].strip()
    return ""


def _wyciagnij_json(tekst: str) -> str:
    dopasowanie = re.search(r"```(?:json)?\s*(.*?)```", tekst, re.DOTALL)
    if dopasowanie:
        return dopasowanie.group(1).strip()
    poczatek = tekst.find("{")
    koniec = tekst.rfind("}")
    return tekst[poczatek:koniec + 1] if poczatek != -1 else tekst


def _zapytaj_model(system_prompt: str, tresc_uzytkownika, historia: Optional[list[dict]] = None) -> str:
    """tresc_uzytkownika: str (zwykly tekst) albo lista bloków (tekst+obraz).
    historia: poprzednie wymiany [{"role": "user"/"assistant", "content": str}, ...]
    - bez tego kazde zapytanie jest "pierwsze", model nie wie o czym mowa
    "popraw kola z poprzedniego projektu"."""
    klucz = _wczytaj_klucz()
    if not klucz:
        raise RuntimeError("brak OPENROUTER_API_KEY w holocron-vision/.env")

    wiadomosci = [{"role": "system", "content": system_prompt}]
    wiadomosci.extend(historia or [])
    wiadomosci.append({"role": "user", "content": tresc_uzytkownika})

    zapytanie = json.dumps({
        "model": MODEL,
        "messages": wiadomosci,
        "max_tokens": 4000,
        "temperature": 0.3,
    }).encode()

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=zapytanie,
        headers={
            "Authorization": f"Bearer {klucz}",
            "Content-Type": "application/json",
            "X-Title": "Holocron Engine",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as odp:
        wynik = json.loads(odp.read())

    tresc = wynik["choices"][0]["message"].get("content")
    powod = wynik["choices"][0].get("finish_reason")
    if not tresc:
        raise RuntimeError(
            f"model nie dokończył odpowiedzi (finish_reason={powod}) - "
            "spróbuj opisać część prościej albo w mniejszych krokach"
        )
    return tresc


def zbuduj_pojedyncza_bryle(p: Prymityw):
    """Buduje geometrie JEDNEJ bryly z planu - bez laczenia z reszta.
    Uzywane zarowno przy sklejaniu calosci (_zbuduj_bryle) jak i przy
    eksporcie osobnych STL-i do podgladu kolorowego (server.py), zeby
    kazda bryla renderowala sie wlasnym kolorem zamiast jednym zlaczonym
    szarym meshem."""
    if p.typ == "box":
        if not p.dlugosc or not p.szerokosc:
            raise ValueError("box wymaga dlugosc i szerokosc")
        return (
            cq.Workplane("XY")
            .center(p.x, p.y)
            .box(p.dlugosc, p.szerokosc, p.wysokosc, centered=(True, True, False))
            .translate((0, 0, p.z))
        )
    if not p.promien:
        raise ValueError("cylinder wymaga promien")
    return (
        cq.Workplane("XY")
        .center(p.x, p.y)
        .circle(p.promien)
        .extrude(p.wysokosc)
        .translate((0, 0, p.z))
    )


def _zbuduj_bryle(bryly: list[Prymityw], otwory: list[Otwor], fillet_promien: Optional[float]):
    """Deterministyczne, nasze wlasne skladanie geometrii z juz
    zwalidowanych liczb - model nie wykonuje tu zadnego kodu."""
    model = None
    for p in bryly:
        czesc = zbuduj_pojedyncza_bryle(p)
        model = czesc if model is None else model.union(czesc)

    for o in otwory:
        model = model.faces(">Z").workplane().center(o.x, o.y).hole(o.srednica)

    if fillet_promien:
        try:
            model = model.edges("|Z").fillet(fillet_promien)
        except Exception:
            # OpenCASCADE potrafi odmowic (BRep_API: command not done) na
            # zlozonej geometrii - np. kola (walce) zlaczone z podwoziem
            # tworza krawedzie ktorych nie da sie zaokraglic tym promieniem.
            # Lepiej pokazac bryle bez zaokraglenia niz wywalic cala prosbe.
            pass

    return model


def _zrzut_do_oceny(bryla) -> bytes:
    """Renderuje bryle w headless przegladarce (Three.js, samodzielna
    strona bez zaleznosci od dzialajacego serwera) i zwraca PNG jako bajty."""
    with tempfile.TemporaryDirectory() as tmp:
        stl_path = pathlib.Path(tmp) / "ocena.stl"
        cq.exporters.export(bryla, str(stl_path))
        stl_b64 = base64.b64encode(stl_path.read_bytes()).decode()

        bb = bryla.val().BoundingBox()
        srodek = ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2)
        rozmiar = max(bb.xlen, bb.ylen, bb.zlen, 1.0)
        dystans = rozmiar * 2.2

        html = f"""<!doctype html><html><head><meta charset="utf-8"></head>
<body style="margin:0"><div id="v" style="width:900px;height:700px"></div>
<script type="importmap">{{"imports":{{"three":"https://unpkg.com/three@0.160.0/build/three.module.js",
"three/addons/":"https://unpkg.com/three@0.160.0/examples/jsm/"}}}}</script>
<script type="module">
import * as THREE from "three";
import {{ STLLoader }} from "three/addons/loaders/STLLoader.js";
const el = document.getElementById("v");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xe8e8ec);
const camera = new THREE.PerspectiveCamera(45, 900/700, 0.1, 100000);
camera.position.set({dystans:.1}, {dystans:.1}, {dystans:.1});
camera.lookAt({srodek[0]:.1}, {srodek[1]:.1}, {srodek[2]:.1});
const renderer = new THREE.WebGLRenderer({{antialias:true}});
renderer.setSize(900,700);
el.appendChild(renderer.domElement);
scene.add(new THREE.AmbientLight(0xffffff, 0.7));
const d = new THREE.DirectionalLight(0xffffff, 1.0);
d.position.set(1,1.5,1);
scene.add(d);
const b64 = "{stl_b64}";
const bin = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
const geometry = new STLLoader().parse(bin.buffer);
geometry.computeVertexNormals();
const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({{color:0x9a9aa2, metalness:0.2, roughness:0.5}}));
scene.add(mesh);
renderer.render(scene, camera);
window.__gotowe = true;
</script></body></html>"""

        with sync_playwright() as p:
            przegladarka = p.chromium.launch()
            strona = przegladarka.new_page(viewport={"width": 900, "height": 700})
            strona.set_content(html)
            strona.wait_for_function("window.__gotowe === true", timeout=15000)
            png = strona.screenshot()
            przegladarka.close()
        return png


def _ocen_wizualnie(opis_uzytkownika: str, plan_json: str, png: bytes) -> Optional[OcenaWizualna]:
    """Zwraca None jesli ocena sie nie udala (np. brak sieci) - wtedy po
    prostu pokazujemy pierwszy wynik, nie blokujemy calosci na tym kroku."""
    try:
        b64 = base64.b64encode(png).decode()
        tresc = _zapytaj_model(
            SYSTEM_PROMPT_OCENA,
            [
                {"type": "text", "text": f"Prosba uzytkownika: {opis_uzytkownika}\n\nTwoj plan:\n{plan_json}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        )
        dane = json.loads(_wyciagnij_json(tresc))
        return OcenaWizualna.model_validate(dane)
    except Exception:
        return None


def generuj_z_opisu(opis: str, historia: Optional[list[dict]] = None) -> dict:
    """Zwraca slownik:
    - tryb "czat": {"tryb": "czat", "odpowiedz": str, "surowa_tresc": str}
    - tryb "geometria": {"tryb": "geometria", "bryla": cq.Workplane,
      "plan_json": str, "poprawiono": bool, "surowa_tresc": str}
    "surowa_tresc" to dokladnie to co model odpowiedzial - do zapisania w
    historii rozmowy przez wywolujacego (backend), zeby kolejne zapytania
    ("popraw kola") mialy kontekst tego co juz zaprojektowano.
    Rzuca RuntimeError/ValueError/ValidationError z czytelnym powodem -
    idzie prosto do czatu, nigdy surowy traceback."""
    tresc = _zapytaj_model(SYSTEM_PROMPT, opis, historia)
    surowy_json = _wyciagnij_json(tresc)

    try:
        dane = json.loads(surowy_json)
        plan = OdpowiedzModelu.model_validate(dane)
    except (json.JSONDecodeError, ValidationError) as e:
        raise ValueError(f"model zwrocil nieprawidlowe dane: {e}")

    if plan.tryb == "czat":
        return {"tryb": "czat", "odpowiedz": plan.odpowiedz, "surowa_tresc": tresc}

    bryla = _zbuduj_bryle(plan.bryly, plan.otwory, plan.fillet_promien)
    plan_json = json.dumps(
        {"bryly": [b.model_dump() for b in plan.bryly],
         "otwory": [o.model_dump() for o in plan.otwory],
         "fillet_promien": plan.fillet_promien},
        indent=2,
    )

    poprawiono = False
    try:
        png = _zrzut_do_oceny(bryla)
        ocena = _ocen_wizualnie(opis, plan_json, png)
        if ocena and ocena.ocena == "popraw":
            bryla = _zbuduj_bryle(ocena.bryly, ocena.otwory, ocena.fillet_promien)
            plan_json = json.dumps(
                {"bryly": [b.model_dump() for b in ocena.bryly],
                 "otwory": [o.model_dump() for o in ocena.otwory],
                 "fillet_promien": ocena.fillet_promien},
                indent=2,
            )
            poprawiono = True
    except Exception:
        pass  # brak samo-oceny nie blokuje pokazania pierwszego wyniku

    return {
        "tryb": "geometria", "bryla": bryla, "plan_json": plan_json,
        "poprawiono": poprawiono,
        # ostateczny plan (po ewentualnej poprawce), nie surowa pierwsza
        # odpowiedz - zeby historia rozmowy zgadzala sie z tym co user widzi
        "surowa_tresc": json.dumps({"tryb": "geometria", **json.loads(plan_json)}),
    }
