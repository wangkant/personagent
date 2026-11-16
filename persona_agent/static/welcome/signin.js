// The sign-in page another device sees before the page itself.
"use strict";
const STRINGS = {
  en: {
    signin_language: "Language",
    signin_title: "Sign in to personagent",
    signin_lead: "This page manages personagent running on another computer. Enter the page password set there.",
    signin_password: "Page password",
    signin_show: "Show",
    signin_hide: "Hide",
    signin_submit: "Sign in",
    signin_working: "Signing in…",
    signin_opening_page: "Signed in. Opening the page…",
    signin_empty: "Enter the page password.",
    signin_wrong: "The password is not correct. {left} more attempts are allowed from this device before sign-in is paused for 15 minutes.",
    signin_wrong_last: "The password is not correct. One more attempt is allowed from this device before sign-in is paused for 15 minutes.",
    signin_locked: "Too many attempts from this device. Sign-in is paused; try again in {minutes} minutes.",
    signin_failed: "The page could not be reached. Check the connection, then try again.",
    signin_forgot: "To set a new password, run personagent page password on the computer personagent runs on.",
    signin_http:
      "This connection is not encrypted: on a shared network, the password and the session can be read in transit. Reach the page through an SSH tunnel, a VPN such as Tailscale, or a reverse proxy with HTTPS.",
  },
  zh: {
    signin_language: "语言",
    signin_title: "登录 personagent",
    signin_lead: "此页面用于管理运行在另一台电脑上的 personagent。请输入在该电脑上设置的页面密码。",
    signin_password: "页面密码",
    signin_show: "显示",
    signin_hide: "隐藏",
    signin_submit: "登录",
    signin_working: "正在登录…",
    signin_opening_page: "已登录，正在打开页面…",
    signin_empty: "请输入页面密码。",
    signin_wrong: "密码不正确。此设备还可尝试 {left} 次，之后登录将暂停 15 分钟。",
    signin_wrong_last: "密码不正确。此设备还可尝试 1 次，之后登录将暂停 15 分钟。",
    signin_locked: "此设备尝试次数过多，登录已暂停，请在 {minutes} 分钟后重试。",
    signin_failed: "无法连接到页面。请检查网络连接后重试。",
    signin_forgot: "如需设置新密码，请在运行 personagent 的电脑上运行 personagent page password。",
    signin_http:
      "此连接未加密：在共享网络中，密码与登录状态可能在传输途中被读取。请通过 SSH 隧道、Tailscale 等 VPN，或启用 HTTPS 的反向代理访问此页面。",
  },
};
const LANGS = {
  en: "en",
  zh: "zh-CN",
  "zh-TW": "zh-TW",
  ja: "ja",
  ko: "ko",
  es: "es",
  fr: "fr",
  de: "de",
  "pt-BR": "pt-BR",
  ru: "ru",
};
// Shared with the page, so both speak the language chosen on either.
const LANG_KEY = "personagent-page-language";
const loaded = { en: STRINGS.en, zh: STRINGS.zh };
const $ = (id) => document.getElementById(id);
function storedLang() {
  try {
    const code = localStorage.getItem(LANG_KEY);
    return code && LANGS[code] ? code : "";
  } catch {
    return "";
  }
}
function browserLang() {
  for (const tag of navigator.languages || [navigator.language || ""]) {
    const low = tag.toLowerCase();
    if (low.startsWith("zh")) return /^zh-(tw|hk|mo|hant)/.test(low) ? "zh-TW" : "zh";
    if (low.startsWith("pt")) return "pt-BR";
    const base = low.split("-")[0];
    if (LANGS[base]) return base;
  }
  return "";
}
let lang = storedLang() || browserLang() || "en";
// The message now showing, as a key and its fields, so it follows a language change.
let shown = null;
let busy = false;
const t = (key, fields = {}) =>
  Object.entries(fields).reduce(
    (text, [name, value]) => text.replaceAll(`{${name}}`, () => String(value)),
    (loaded[lang] || {})[key] || STRINGS.en[key] || key,
  );
async function load(code) {
  if (loaded[code]) return;
  try {
    const response = await fetch(`/assets/i18n/${code}.json`, { credentials: "same-origin" });
    loaded[code] = (await response.json()).strings || {};
  } catch {
    loaded[code] = {};
  }
}
function render() {
  document.documentElement.lang = LANGS[lang] || "en";
  $("signin-language").value = lang;
  for (const node of document.querySelectorAll("[data-t]")) node.textContent = t(node.dataset.t);
  for (const node of document.querySelectorAll("[data-t-aria]"))
    node.setAttribute("aria-label", t(node.dataset.tAria));
  const visible = $("signin-password").type === "text";
  $("signin-show").textContent = t(visible ? "signin_hide" : "signin_show");
  if (busy) $("signin-submit").textContent = t("signin_working");
  say(shown);
}
// One message at a time: an error in the alert box, progress in the status line.
function say(message) {
  shown = message;
  const error = $("signin-error");
  const status = $("signin-status");
  error.hidden = status.hidden = true;
  if (!message) return;
  const box = message.error ? error : status;
  box.textContent = t(message.key, message.fields);
  box.hidden = false;
}
$("signin-language").addEventListener("change", async (event) => {
  lang = event.target.value;
  try {
    localStorage.setItem(LANG_KEY, lang);
  } catch {
    /* storage is off: the choice lasts for this visit */
  }
  await load(lang);
  render();
});
$("signin-show").addEventListener("click", () => {
  const field = $("signin-password");
  field.type = field.type === "password" ? "text" : "password";
  $("signin-show").setAttribute("aria-pressed", String(field.type === "text"));
  render();
  field.focus();
});
$("signin-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (busy) return;
  const field = $("signin-password");
  if (!field.value) {
    say({ error: true, key: "signin_empty" });
    field.focus();
    return;
  }
  busy = true;
  const submit = $("signin-submit");
  submit.disabled = true;
  submit.textContent = t("signin_working");
  say(null);
  let signedIn = false;
  try {
    const response = await fetch("/auth/signin", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: field.value }),
      credentials: "same-origin",
    });
    const value = await response.json().catch(() => ({}));
    if (response.ok) {
      signedIn = true;
      say({ key: "signin_opening_page" });
      location.replace("/");
      return;
    }
    if (value.error === "signin_locked") {
      say({ error: true, key: "signin_locked", fields: { minutes: Math.max(1, Math.ceil((value.seconds || 60) / 60)) } });
    } else if (value.error === "signin_wrong") {
      say({ error: true, key: value.left === 1 ? "signin_wrong_last" : "signin_wrong", fields: { left: value.left } });
    } else {
      say({ error: true, key: "signin_failed" });
    }
  } catch {
    say({ error: true, key: "signin_failed" });
  } finally {
    busy = false;
    // Kept disabled while the page opens.
    if (!signedIn) {
      submit.disabled = false;
      submit.textContent = t("signin_submit");
      field.select();
      field.focus();
    }
  }
});
(async () => {
  // Plain HTTP beyond this computer: said once, here.
  $("signin-http").hidden = location.protocol !== "http:";
  await load(lang);
  render();
  $("signin-password").focus();
})();
