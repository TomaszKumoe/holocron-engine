// Wspolny modul tlumaczen PL/EN dla wszystkich stron frontendu. Ten sam
// wzorzec co przelacznik motywu w auth.js/*.html: stan w localStorage,
// przelacznik dziala nawet gdy inne moduly (three.js, auth.js) padna.

const DICT = {
  pl: {
    nav_projects: "Moje projekty",
    nav_chats: "Czaty",
    nav_plan: "Plan",
    nav_open_project_for_chat: "Otwórz projekt, aby zobaczyć czat",
    settings: "Ustawienia",
    theme_toggle: "☀︎/☾ przełącz motyw",
    lang_toggle: "🌐 język: polski",
    logout: "Wyloguj",
    back_to_projects: "← Projekty",
    base_robot_link: "Robot bazowy",

    new_project_placeholder: "nazwa nowego projektu (np. dron wyścigowy)",
    new_project_btn: "+ Nowy projekt",
    empty_state: "Brak projektów — utwórz pierwszy powyżej.",
    rename_title: "Zmień nazwę",
    delete_title: "Usuń projekt",
    delete_confirm: "Usunąć ten projekt na stałe?",
    projects_heading: "Moje projekty",

    selected_part_title: "Zaznaczona część",
    no_selection: "-- kliknij część w widoku --",
    mode_translate: "przesuń",
    mode_rotate: "obróć",
    hint: "klik na część: zaznacz i manipuluj gizmo · puste miejsce: obrót/przesuw kamery (LPM/PPM) · scroll: zoom",
    empty_project_state: "Ten projekt jest jeszcze pusty.<br>Opisz w czacie po prawej co chcesz zaprojektować.",
    chat_placeholder: "np. koła do robota",
    send: "Wyślij",
    rename_tooltip: "Kliknij, aby zmienić nazwę",
    part_color: "Kolor bryły",
    initial_bot_msg: "Opisz część do zaprojektowania (np. \"koła do robota\") - dobiorę sensowne wymiary sam, chyba że podasz swoje. Kliknij część w widoku, żeby ją zaznaczyć i przesunąć/obrócić gizmem.",

    plan_title: "Plan",
    plan_subtitle: "Wybierz sposób rozliczania.",
    plan_monthly_name: "Miesięczny",
    plan_monthly_price: "99 zł",
    plan_monthly_period: "/ miesiąc",
    plan_yearly_name: "Roczny",
    plan_yearly_price: "990 zł",
    plan_yearly_period: "/ rok",
    plan_yearly_badge: "2 miesiące gratis",
    plan_feature_1: "Nielimitowana liczba projektów",
    plan_feature_2: "Generowanie części przez czat AI",
    plan_feature_3: "Eksport STL / STEP",
    plan_cta: "Wybierz",
    plan_soon: "Płatności będą dostępne wkrótce.",

    login_tab: "Zaloguj się",
    signup_tab: "Zarejestruj się",
    email_label: "E-mail",
    password_label: "Hasło",
    submit_login: "Zaloguj się",
    submit_signup: "Utwórz konto",
    generic_error: "Coś poszło nie tak.",
  },
  en: {
    nav_projects: "My projects",
    nav_chats: "Chats",
    nav_plan: "Plan",
    nav_open_project_for_chat: "Open a project to see its chat",
    settings: "Settings",
    theme_toggle: "☀︎/☾ toggle theme",
    lang_toggle: "🌐 language: English",
    logout: "Log out",
    back_to_projects: "← Projects",
    base_robot_link: "Base robot",

    new_project_placeholder: "new project name (e.g. racing drone)",
    new_project_btn: "+ New project",
    empty_state: "No projects yet — create your first one above.",
    rename_title: "Rename",
    delete_title: "Delete project",
    delete_confirm: "Delete this project permanently?",
    projects_heading: "My projects",

    selected_part_title: "Selected part",
    no_selection: "-- click a part in the view --",
    mode_translate: "move",
    mode_rotate: "rotate",
    hint: "click a part: select and drag the gizmo · empty space: orbit/pan camera (LMB/RMB) · scroll: zoom",
    empty_project_state: "This project is still empty.<br>Describe what you want to design in the chat on the right.",
    chat_placeholder: "e.g. wheels for the robot",
    send: "Send",
    rename_tooltip: "Click to rename",
    part_color: "Solid color",
    initial_bot_msg: "Describe the part you want to design (e.g. \"wheels for the robot\") - I'll pick sensible dimensions myself unless you give your own. Click a part in the view to select it and move/rotate it with the gizmo.",

    plan_title: "Plan",
    plan_subtitle: "Choose your billing option.",
    plan_monthly_name: "Monthly",
    plan_monthly_price: "99 zł",
    plan_monthly_period: "/ month",
    plan_yearly_name: "Yearly",
    plan_yearly_price: "990 zł",
    plan_yearly_period: "/ year",
    plan_yearly_badge: "2 months free",
    plan_feature_1: "Unlimited projects",
    plan_feature_2: "AI chat part generation",
    plan_feature_3: "STL / STEP export",
    plan_cta: "Choose",
    plan_soon: "Payments will be available soon.",

    login_tab: "Log in",
    signup_tab: "Sign up",
    email_label: "E-mail",
    password_label: "Password",
    submit_login: "Log in",
    submit_signup: "Create account",
    generic_error: "Something went wrong.",
  },
};

const KLUCZ = "holocron-engine-lang";

export function getLang() {
  return localStorage.getItem(KLUCZ) || "pl";
}

export function t(klucz) {
  const lang = getLang();
  return DICT[lang]?.[klucz] ?? DICT.pl[klucz] ?? klucz;
}

export function applyLang() {
  const lang = getLang();
  document.documentElement.setAttribute("lang", lang);
  document.documentElement.setAttribute("data-lang", lang);
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.innerHTML = t(el.getAttribute("data-i18n"));
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    el.placeholder = t(el.getAttribute("data-i18n-ph"));
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.getAttribute("data-i18n-title"));
  });
}

export function setLang(lang) {
  localStorage.setItem(KLUCZ, lang);
  applyLang();
  window.dispatchEvent(new CustomEvent("langchange", { detail: lang }));
}

export function toggleLang() {
  setLang(getLang() === "pl" ? "en" : "pl");
}
