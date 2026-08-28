// Wspolny modul logowania (Supabase Auth) dla wszystkich stron frontendu.
// Klucz anon i URL projektu Supabase NIE sa hardkodowane tutaj - backend
// trzyma je w backend/.env i serwuje przez /api/config, zeby byl jeden
// zrodlo prawdy zamiast kopiowania sekretu do kazdego pliku HTML.

let _clientPromise = null;

async function getClient() {
  if (!_clientPromise) {
    _clientPromise = (async () => {
      const cfg = await fetch("/api/config").then((r) => r.json());
      const { createClient } = await import("https://esm.sh/@supabase/supabase-js@2");
      return createClient(cfg.url, cfg.anonKey);
    })();
  }
  return _clientPromise;
}

export async function getSession() {
  const supabase = await getClient();
  const { data: { session } } = await supabase.auth.getSession();
  return session;
}

// Wywolaj na starcie kazdej chronionej strony: przekierowuje na /login
// jesli nikt nie jest zalogowany, inaczej zwraca sesje.
export async function wymagajLogowania() {
  const session = await getSession();
  if (!session) {
    window.location.href = "/login";
    return null;
  }
  return session;
}

export async function wyloguj() {
  try {
    const supabase = await getClient();
    await supabase.auth.signOut();
  } finally {
    // przekieruj zawsze, nawet jesli signOut() rzuci (np. sesja juz
    // niewazna po stronie Supabase) - inaczej przycisk "Wyloguj" nic nie robi
    window.location.href = "/login";
  }
}

export async function zaloguj(email, haslo) {
  const supabase = await getClient();
  return supabase.auth.signInWithPassword({ email, password: haslo });
}

// Rejestracja idzie przez backend (Admin API + service_role key), nie
// klienckie supabase.auth.signUp() - signUp() zawsze probuje wyslac maila
// potwierdzajacego i pada na rate-limit wbudowanego SMTP Supabase.
// Backend tworzy konto od razu jako potwierdzone, wiec od razu potem
// mozna sie zwyczajnie zalogowac (signInWithPassword).
export async function zarejestruj(email, haslo) {
  const r = await fetch("/api/auth/rejestracja", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, haslo }),
  });
  if (!r.ok) {
    const dane = await r.json().catch(() => ({}));
    throw new Error(dane.detail || "nie udało się utworzyć konta");
  }
  return zaloguj(email, haslo);
}

// fetch() ktory sam dokleja token zalogowanego uzytkownika - backend
// weryfikuje go przez Supabase i filtruje projekty po wlascicielu.
export async function authFetch(url, opts = {}) {
  const session = await getSession();
  const headers = new Headers(opts.headers || {});
  if (session) headers.set("Authorization", `Bearer ${session.access_token}`);
  return fetch(url, { ...opts, headers });
}

export { getClient };
