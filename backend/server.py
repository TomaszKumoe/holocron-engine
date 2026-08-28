"""Backend Holocron Engine: serwuje frontend, konwertuje STEP->STL do
podgladu 3D w przegladarce, i podpina czat pod prawdziwy silnik (na razie
tylko mass_properties - liczy prawdziwa mase/bezwladnosc, nie zmyslone
odpowiedzi).

    python server.py
    -> http://localhost:8300
"""

import json
import os
import pathlib
import re
import sys
import time
import uuid
from datetime import datetime, timezone

import cadquery as cq
import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

KATALOG = pathlib.Path(__file__).parent
FRONTEND = KATALOG.parent / "frontend"
CACHE_STL = KATALOG / "static_models"
CACHE_STL.mkdir(exist_ok=True)

load_dotenv(KATALOG / ".env")
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

sys.path.insert(0, str(KATALOG.parent / "engine"))
import mass_properties  # noqa: E402
import layout  # noqa: E402
import generuj  # noqa: E402
import llm_cad  # noqa: E402

# Twoj robot-hobby to dane TESTOWE silnika, nie produkt (patrz
# holocron-robotics-narodziny w pamieci). WYGENEROWANE_DIR to prawdziwy
# produkt: czesci ktore silnik SAM tworzy z parametrow (generuj.py),
# nie gotowe pliki ktore ktos juz zaprojektowal recznie.
ROBOT_DIR = pathlib.Path(r"c:\Users\tomas\holocron-vision\robot")
WYGENEROWANE_DIR = KATALOG.parent / "wygenerowane"

# System projektow: kazdy nowy projekt startuje PUSTY - bez robota-hobby,
# bez niczyich cudzych czesci. To jest realny produkt (patrz strona
# projekty.html); /api/uklad, /api/model, /api/chat powyzej zostaja jako
# byly-globalny widok testowy, nietkniete.
PROJEKTY_DIR = KATALOG.parent / "projekty"
PROJEKTY_DIR.mkdir(exist_ok=True)
HISTORIE_PROJEKTOW: dict[str, list[dict]] = {}

app = FastAPI()

# Frontend na Vercel woła /api/* przez rewrite (ten sam origin z perspektywy
# przegladarki), ale CORS zostaje jako siatka bezpieczenstwa - np. do
# recznego testowania backendu spod innego originu.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://holocron-engine.com", "http://localhost:8300", "http://127.0.0.1:8300"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pamiec rozmowy z LLM (llm_cad.py) - jedna, dzielona sesja (narzedzie
# lokalne, jednoosobowe). Bez tego kazde zapytanie do modelu jest "pierwsze",
# wiec "popraw kola z poprzedniego projektu" nie ma jak zadzialac. Ograniczone
# do ostatnich N wymian, zeby nie rosla bez konca.
HISTORIA_LLM: list[dict] = []
HISTORIA_MAKS_WYMIAN = 8


def dostepne_czesci() -> dict[str, pathlib.Path]:
    czesci = {p.stem: p for p in ROBOT_DIR.glob("*.step")}
    czesci.update({p.stem: p for p in WYGENEROWANE_DIR.glob("*.step")})
    return czesci


@app.get("/", response_class=HTMLResponse)
def index():
    # Jeden link - localhost:8300 - i wszystko pod nim: logowanie,
    # wylogowanie, lista projektow. To jest "/" bo projekty.html samo
    # przekierowuje na /login gdy nikt nie jest zalogowany (patrz
    # wymagajLogowania() w assets/auth.js) - wiec ten sam link dziala
    # i dla niezalogowanego (dostaje login), i dla zalogowanego (dostaje
    # liste projektow), bez osobnych "stron startowych".
    return (FRONTEND / "projekty.html").read_text(encoding="utf-8")


@app.get("/global", response_class=HTMLResponse)
def index_global():
    """Stary, dzielony widok testowy (robot-hobby + wygenerowane/) - bez
    logowania, celowo nietkniety, dostepny pod osobna sciezka zeby nic z
    wczesniejszej pracy nie zniknelo."""
    return (FRONTEND / "index.html").read_text(encoding="utf-8")


app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")


@app.get("/login", response_class=HTMLResponse)
def strona_login():
    return (FRONTEND / "login.html").read_text(encoding="utf-8")


@app.get("/api/config")
def api_config():
    """Frontend (bez build-stepu) pobiera stad URL/anon-key Supabase zamiast
    trzymac je zahardkodowane w kazdym pliku HTML - jedno zrodlo prawdy to
    backend/.env. Anon key jest z zalozenia publiczny (tak dziala Supabase),
    wiec zwracanie go w tym endpointcie nie jest wyciekiem sekretu."""
    return {"url": SUPABASE_URL, "anonKey": SUPABASE_ANON_KEY}


# ── logowanie (Supabase Auth) ──────────────────────────────────────────
# Token z frontendu weryfikujemy odpytujac prawdziwe Supabase (auth/v1/user)
# zamiast lokalnie dekodowac JWT - nie trzeba trzymac JWT-secretu w
# backendzie, a Supabase samo pilnuje wygasania/odwolania sesji. Krotki
# cache (30s) zeby seria zadan (np. ladowanie kilku plikow STL) nie biła
# do Supabase przy kazdym requescie.
_WERYFIKACJA_CACHE: dict[str, tuple[dict, float]] = {}
_WERYFIKACJA_TTL_S = 30.0


def _zweryfikuj_token(token: str) -> dict:
    teraz = time.monotonic()
    wpis = _WERYFIKACJA_CACHE.get(token)
    if wpis and wpis[1] > teraz:
        return wpis[0]
    try:
        odp = httpx.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"nie mozna polaczyc sie z Supabase: {e}")
    if odp.status_code != 200:
        raise HTTPException(status_code=401, detail="nieprawidlowa lub wygasla sesja - zaloguj sie ponownie")
    uzytkownik = odp.json()
    _WERYFIKACJA_CACHE[token] = (uzytkownik, teraz + _WERYFIKACJA_TTL_S)
    return uzytkownik


def wymagaj_uzytkownika(request: Request) -> dict:
    naglowek = request.headers.get("authorization", "")
    if not naglowek.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="brak tokenu logowania")
    return _zweryfikuj_token(naglowek[7:])


class DaneRejestracji(BaseModel):
    email: str
    haslo: str


@app.post("/api/auth/rejestracja")
def api_rejestracja(dane: DaneRejestracji):
    """Rejestracja przez Admin API (service_role key) zamiast klienckiego
    supabase.auth.signUp(). signUp() zawsze probuje wyslac maila
    potwierdzajacego i pada na rate-limit wbudowanego SMTP Supabase (2-4
    maile/h) - admin.createUser z email_confirm=True tworzy konto od razu
    jako potwierdzone, bez wysylki zadnego maila. Frontend potem loguje
    sie normalnie przez signInWithPassword (anon key)."""
    try:
        odp = httpx.post(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json",
            },
            json={"email": dane.email, "password": dane.haslo, "email_confirm": True},
            timeout=10.0,
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"nie mozna polaczyc sie z Supabase: {e}")
    if odp.status_code >= 400:
        try:
            szczegoly = odp.json().get("msg") or odp.json().get("message") or odp.text
        except ValueError:
            szczegoly = odp.text
        raise HTTPException(status_code=odp.status_code, detail=szczegoly)
    return {"ok": True}


@app.get("/api/czesci")
def api_czesci():
    return sorted(dostepne_czesci().keys())


@app.get("/api/uklad")
def api_uklad():
    """Pozycje/rotacje czesci w zlozeniu - do ustawienia osobnych, klikalnych
    mesh-y we frontendzie (zamiast jednej zlaczonej bryly zestaw.step).
    Zawiera dwa zrodla: robot-hobby (dane testowe) i wygenerowane (to co
    silnik SAM tworzy z parametrow - prawdziwy produkt)."""
    return layout.uklad() + layout.uklad_wygenerowane()


@app.get("/api/model/{nazwa}.stl")
def api_model_stl(nazwa: str):
    czesci = dostepne_czesci()
    if nazwa not in czesci:
        return HTMLResponse(f"nieznana czesc: {nazwa}", status_code=404)

    stl_path = CACHE_STL / f"{nazwa}.stl"
    if not stl_path.exists():
        shape = cq.importers.importStep(str(czesci[nazwa])).val()
        cq.exporters.export(shape, str(stl_path))

    return FileResponse(stl_path, media_type="model/stl")


class WiadomoscCzatu(BaseModel):
    tekst: str


@app.post("/api/chat")
def api_chat(wiad: WiadomoscCzatu):
    """Na razie rozumie tylko 'masa <czesc>' i pyta prawdziwy silnik.
    To NIE jest LLM jeszcze - jawnie ograniczone, zeby nie zmyslac
    odpowiedzi ktorych nie policzylismy naprawde."""
    tekst = wiad.tekst.strip().lower()
    czesci = dostepne_czesci()

    dopasowanie = re.match(r"masa\s+(\S+)", tekst)
    if dopasowanie:
        nazwa = dopasowanie.group(1)
        if nazwa in czesci:
            wynik = mass_properties.policz(str(czesci[nazwa]), gestosc_g_cm3=1.24, infill_procent=20)
            return {
                "odpowiedz": (
                    f"{nazwa}: masa {wynik['masa_kg']*1000:.1f} g (20% infill, PLA), "
                    f"srodek masy {tuple(round(v, 4) for v in wynik['srodek_masy_m'])} m"
                )
            }
        return {"odpowiedz": f"nie znam czesci '{nazwa}'. dostepne: {', '.join(sorted(czesci))}"}

    dopasowanie = re.match(r"baza\s+(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)(?:\s+grubosc\s+(\d+(?:\.\d+)?))?", tekst)
    if dopasowanie:
        dlugosc = float(dopasowanie.group(1))
        szerokosc = float(dopasowanie.group(2))
        grubosc = float(dopasowanie.group(3)) if dopasowanie.group(3) else generuj.GRUBOSC
        try:
            bryla = generuj.baza(dlugosc=dlugosc, szerokosc=szerokosc, grubosc=grubosc)
        except ValueError as e:
            return {"odpowiedz": f"nie da się: {e}"}
        generuj.zapisz(bryla, "przyklad_baza")
        stl_stary = CACHE_STL / "przyklad_baza.stl"
        if stl_stary.exists():
            stl_stary.unlink()  # wymusza ponowna konwersje STEP->STL swiezych wymiarow
        return {
            "odpowiedz": f"przeliczone: baza {dlugosc:.0f}x{szerokosc:.0f}x{grubosc:.0f}mm, otwory na silniki w rogach",
            "przeladuj": "przyklad_baza",
        }

    # wszystko inne idzie do LLM (Claude Opus 5) - model sam wybiera
    # czy to zwykla rozmowa (tryb "czat") czy prosba o czesc (tryb
    # "geometria"). W obu przypadkach model zwraca dane, NIE kod - zero
    # exec() na tekscie od modelu, geometrie sklada nasz wlasny
    # deterministyczny kod w llm_cad.py. Po zbudowaniu geometrii silnik
    # sam robi sobie zrzut i pyta model o ocene - "poprawiono" mowi czy
    # ta runda faktycznie cos zmienila.
    try:
        wynik = llm_cad.generuj_z_opisu(wiad.tekst, historia=HISTORIA_LLM)
    except (RuntimeError, ValueError) as e:
        return {"odpowiedz": f"nie udało się wygenerować: {e}"}
    except Exception as e:
        return {"odpowiedz": f"błąd modelu/sieci: {e}"}

    # zapisz wymiane w historii (dla kolejnych "popraw kola" itp.), obcinajac
    # do ostatnich HISTORIA_MAKS_WYMIAN par
    HISTORIA_LLM.append({"role": "user", "content": wiad.tekst})
    HISTORIA_LLM.append({"role": "assistant", "content": wynik["surowa_tresc"]})
    del HISTORIA_LLM[:-2 * HISTORIA_MAKS_WYMIAN]

    if wynik["tryb"] == "czat":
        return {"odpowiedz": wynik["odpowiedz"]}

    generuj.zapisz(wynik["bryla"], "llm_wynik")
    stl_stary = CACHE_STL / "llm_wynik.stl"
    if stl_stary.exists():
        stl_stary.unlink()
    dopisek = " (poprawione po własnej ocenie zrzutu)" if wynik.get("poprawiono") else ""
    return {
        "odpowiedz": f"wygenerowano z opisu (Claude Opus 5){dopisek}, plan geometrii:\n{wynik['plan_json']}",
        "przeladuj": "llm_wynik",
        "nowa_czesc": "llm_wynik",
    }


# ══════════════════════════════════════════════════════════════════════
# System projektow - wchodzisz na "/", widzisz liste, tworzysz nowy = pusta
# scena, generujesz w niej swoje czesci. Osobny od wszystkiego powyzej.
# ══════════════════════════════════════════════════════════════════════

def _folder_projektu(pid: str) -> pathlib.Path:
    return PROJEKTY_DIR / pid


def _wczytaj_meta(pid: str) -> dict | None:
    plik = _folder_projektu(pid) / "meta.json"
    return json.loads(plik.read_text(encoding="utf-8")) if plik.exists() else None


def _zapisz_meta(pid: str, meta: dict) -> None:
    (_folder_projektu(pid) / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _czesci_projektu(pid: str) -> dict[str, pathlib.Path]:
    folder = _folder_projektu(pid)
    if not folder.exists():
        return {}
    return {p.stem: p for p in folder.glob("*.step")}


def _sprawdz_wlasciciela(pid: str, uzytkownik: dict) -> dict:
    """404 zamiast 403 gdy projekt nie istnieje LUB nalezy do kogos innego -
    zeby nie zdradzac przez kod bledu, czy dany id w ogole istnieje."""
    meta = _wczytaj_meta(pid)
    if meta is None or meta.get("wlasciciel") != uzytkownik["id"]:
        raise HTTPException(status_code=404, detail="nie znam tego projektu")
    return meta


@app.get("/projekty", response_class=HTMLResponse)
def strona_projekty():
    return (FRONTEND / "projekty.html").read_text(encoding="utf-8")


@app.get("/projekt", response_class=HTMLResponse)
def strona_projekt():
    return (FRONTEND / "projekt.html").read_text(encoding="utf-8")


@app.get("/plan", response_class=HTMLResponse)
def strona_plan():
    return (FRONTEND / "plan.html").read_text(encoding="utf-8")


@app.get("/api/projekty")
def api_lista_projektow(uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    wynik = []
    for folder in PROJEKTY_DIR.iterdir():
        if not folder.is_dir():
            continue
        meta = _wczytaj_meta(folder.name) or {}
        if meta.get("wlasciciel") != uzytkownik["id"]:
            continue
        wynik.append({
            "id": folder.name,
            "nazwa": meta.get("nazwa", folder.name),
            "utworzono": meta.get("utworzono", ""),
            "liczba_czesci": len(list(folder.glob("*.step"))),
        })
    wynik.sort(key=lambda p: p["utworzono"], reverse=True)
    return wynik


class NowyProjekt(BaseModel):
    nazwa: str = ""


@app.post("/api/projekty")
def api_nowy_projekt(dane: NowyProjekt, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    pid = uuid.uuid4().hex[:8]
    _folder_projektu(pid).mkdir(parents=True)
    meta = {
        "nazwa": dane.nazwa.strip() or "Bez nazwy",
        "utworzono": datetime.now(timezone.utc).isoformat(),
        "wlasciciel": uzytkownik["id"],
        "polozenia": {},
    }
    _zapisz_meta(pid, meta)
    return {"id": pid, **meta}


class ZmianaNazwy(BaseModel):
    nazwa: str


@app.patch("/api/projekty/{pid}")
def api_zmien_nazwe_projektu(pid: str, dane: ZmianaNazwy, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    meta = _sprawdz_wlasciciela(pid, uzytkownik)
    nazwa = dane.nazwa.strip()
    if not nazwa:
        raise HTTPException(status_code=422, detail="nazwa nie moze byc pusta")
    meta["nazwa"] = nazwa
    _zapisz_meta(pid, meta)
    return {"id": pid, **meta}


@app.delete("/api/projekty/{pid}")
def api_usun_projekt(pid: str, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    import shutil
    _sprawdz_wlasciciela(pid, uzytkownik)
    shutil.rmtree(_folder_projektu(pid))
    HISTORIE_PROJEKTOW.pop(pid, None)
    return {"usunieto": pid}


@app.get("/api/projekty/{pid}/uklad")
def api_uklad_projektu(pid: str, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    meta = _sprawdz_wlasciciela(pid, uzytkownik)
    polozenia = meta.get("polozenia", {})
    return [
        {"nazwa": nazwa, **polozenia.get(nazwa, {"x": 0.0, "y": 0.0, "z": 0.0})}
        for nazwa in _czesci_projektu(pid)
    ]


@app.get("/api/projekty/{pid}/model/{nazwa}.stl")
def api_model_projektu(pid: str, nazwa: str, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    _sprawdz_wlasciciela(pid, uzytkownik)
    czesci = _czesci_projektu(pid)
    if nazwa not in czesci:
        return HTMLResponse(f"nieznana czesc: {nazwa}", status_code=404)
    cache_dir = _folder_projektu(pid) / "_cache"
    cache_dir.mkdir(exist_ok=True)
    stl_path = cache_dir / f"{nazwa}.stl"
    if not stl_path.exists():
        shape = cq.importers.importStep(str(czesci[nazwa])).val()
        cq.exporters.export(shape, str(stl_path))
    return FileResponse(stl_path, media_type="model/stl")


def _wczytaj_plan(pid: str, nazwa: str) -> dict | None:
    plik = _folder_projektu(pid) / f"{nazwa}.plan.json"
    return json.loads(plik.read_text(encoding="utf-8")) if plik.exists() else None


@app.get("/api/projekty/{pid}/plan/{nazwa}")
def api_plan_czesci(pid: str, nazwa: str, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    """Lista brył (typ/wymiary/kolor) danej części - front renderuje po
    jednym mesh na bryłę zamiast jednej zlanej, żeby dało się pokolorować
    koła inaczej niż nadwozie. Części sprzed tej funkcji (bez sidecar
    pliku) nie mają planu - front wtedy wraca do starego, jednolitego
    mesh-a z STEP-a."""
    _sprawdz_wlasciciela(pid, uzytkownik)
    if nazwa not in _czesci_projektu(pid):
        return HTMLResponse(f"nieznana czesc: {nazwa}", status_code=404)
    plan = _wczytaj_plan(pid, nazwa)
    if plan is None:
        return HTMLResponse("brak planu dla tej czesci (stara czesc sprzed tej funkcji)", status_code=404)
    return plan


@app.get("/api/projekty/{pid}/model/{nazwa}/bryla/{indeks}.stl")
def api_bryla_stl(pid: str, nazwa: str, indeks: int, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    """STL pojedynczej bryły z planu (nieotworowana, nieocięta) - do
    kolorowego podglądu. Plik do druku/produkcji to nadal cały
    {nazwa}.step (zlana bryła z otworami), ten endpoint służy tylko
    widokowi."""
    _sprawdz_wlasciciela(pid, uzytkownik)
    plan = _wczytaj_plan(pid, nazwa)
    if plan is None or not (0 <= indeks < len(plan.get("bryly", []))):
        return HTMLResponse("nieznana bryla", status_code=404)

    cache_dir = _folder_projektu(pid) / "_cache"
    cache_dir.mkdir(exist_ok=True)
    stl_path = cache_dir / f"{nazwa}_{indeks}.stl"
    if not stl_path.exists():
        p = llm_cad.Prymityw.model_validate(plan["bryly"][indeks])
        shape = llm_cad.zbuduj_pojedyncza_bryle(p)
        cq.exporters.export(shape, str(stl_path))
    return FileResponse(stl_path, media_type="model/stl")


class ZmianaKoloruBryly(BaseModel):
    indeks: int
    kolor: str


@app.patch("/api/projekty/{pid}/plan/{nazwa}")
def api_zmien_kolor_bryly(pid: str, nazwa: str, dane: ZmianaKoloruBryly, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    """Zmiana koloru JEDNEJ bryły bez wracania do LLM - user klika bryłę
    w podglądzie i przestawia suwak koloru, to leci prosto tutaj."""
    _sprawdz_wlasciciela(pid, uzytkownik)
    if not re.match(r"^#[0-9a-fA-F]{6}$", dane.kolor):
        raise HTTPException(status_code=422, detail="kolor musi byc hex, np. #2b2f36")

    plan = _wczytaj_plan(pid, nazwa)
    if plan is None or not (0 <= dane.indeks < len(plan.get("bryly", []))):
        raise HTTPException(status_code=404, detail="nieznana bryla")

    plan["bryly"][dane.indeks]["kolor"] = dane.kolor
    (_folder_projektu(pid) / f"{nazwa}.plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # STL tej bryly w cache jest nadal aktualny geometrycznie (kolor nie
    # zmienia ksztaltu) - nie ma potrzeby go kasowac.
    return {"ok": True, "indeks": dane.indeks, "kolor": dane.kolor}


@app.post("/api/projekty/{pid}/chat")
def api_chat_projektu(pid: str, wiad: WiadomoscCzatu, uzytkownik: dict = Depends(wymagaj_uzytkownika)):
    _sprawdz_wlasciciela(pid, uzytkownik)

    historia = HISTORIE_PROJEKTOW.setdefault(pid, [])
    try:
        wynik = llm_cad.generuj_z_opisu(wiad.tekst, historia=historia)
    except (RuntimeError, ValueError) as e:
        return {"odpowiedz": f"nie udało się wygenerować: {e}"}
    except Exception as e:
        return {"odpowiedz": f"błąd modelu/sieci: {e}"}

    historia.append({"role": "user", "content": wiad.tekst})
    historia.append({"role": "assistant", "content": wynik["surowa_tresc"]})
    del historia[:-2 * HISTORIA_MAKS_WYMIAN]

    if wynik["tryb"] == "czat":
        return {"odpowiedz": wynik["odpowiedz"]}

    czesci_teraz = _czesci_projektu(pid)
    nazwa = f"czesc_{len(czesci_teraz) + 1}"
    generuj.zapisz_do(wynik["bryla"], _folder_projektu(pid) / f"{nazwa}.step")
    # plan.json obok STEP-a: lista brył (z kolorem per-bryła) do
    # kolorowego podglądu w przeglądarce - STEP zostaje jedną zlaną
    # bryłą (do druku/produkcji), ale front renderuje osobny mesh na
    # bryłę, więc koła mogą mieć inny kolor niż nadwozie.
    (_folder_projektu(pid) / f"{nazwa}.plan.json").write_text(wynik["plan_json"], encoding="utf-8")

    meta = _wczytaj_meta(pid) or {"nazwa": pid, "utworzono": "", "polozenia": {}}
    meta.setdefault("polozenia", {})[nazwa] = {"x": 0.0, "y": 0.0, "z": 0.0}
    _zapisz_meta(pid, meta)

    dopisek = " (poprawione po własnej ocenie zrzutu)" if wynik.get("poprawiono") else ""
    return {
        "odpowiedz": f"wygenerowano \"{nazwa}\" z opisu (Claude Opus 5){dopisek}, plan geometrii:\n{wynik['plan_json']}",
        "przeladuj": nazwa,
        "nowa_czesc": nazwa,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8300))
    uvicorn.run(app, host="0.0.0.0", port=port)
