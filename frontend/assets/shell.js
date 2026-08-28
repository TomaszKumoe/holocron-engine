// Wspolna logika "szkieletu" ekranow za logowaniem: menu Ustawienia w
// prawym gornym rogu (motyw/jezyk/wyloguj) i lewe menu nawigacyjne
// (Moje projekty / Czaty / Plan), zbieranie tego w jednym miejscu zamiast
// kopiowania tej samej obslugi klikniec do kazdego pliku HTML.

import { wyloguj } from "/static/assets/auth.js";
import { applyLang, toggleLang } from "/static/assets/i18n.js";

export function initShell(activeKey) {
  applyLang();

  const leftnavEl = document.getElementById("leftnav");
  const leftnavToggleBtn = document.getElementById("leftnav-toggle");
  let leftnavOtwarty = true;

  function ustawLeftnav(otwarty) {
    leftnavOtwarty = otwarty;
    if (leftnavEl) leftnavEl.classList.toggle("collapsed", !otwarty);
  }
  if (leftnavToggleBtn) leftnavToggleBtn.onclick = () => ustawLeftnav(!leftnavOtwarty);

  document.querySelectorAll(".leftnav-item[data-key]").forEach((el) => {
    el.classList.toggle("active", el.dataset.key === activeKey);
  });

  const settingsBtn = document.getElementById("settings-btn");
  const settingsMenu = document.getElementById("settings-menu");
  if (settingsBtn && settingsMenu) {
    settingsBtn.onclick = (e) => { e.stopPropagation(); settingsMenu.classList.toggle("open"); };
    document.addEventListener("click", (e) => {
      if (!settingsMenu.contains(e.target) && e.target !== settingsBtn) settingsMenu.classList.remove("open");
    });
  }

  const langToggleBtn = document.getElementById("lang-toggle");
  if (langToggleBtn) langToggleBtn.onclick = toggleLang;

  const wylogujBtn = document.getElementById("wyloguj-btn");
  if (wylogujBtn) wylogujBtn.onclick = wyloguj;

  return { ustawLeftnav, isOpen: () => leftnavOtwarty };
}
