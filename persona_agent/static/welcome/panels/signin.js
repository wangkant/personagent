// The signin panel: with OpenRouter chosen, sign in with the account instead of
// pasting a key. The server opens the browser, receives the key and saves it;
// this script only starts, follows and cancels the attempt.
PA.strings({
  en: {
    signin_offer: "Sign in with an OpenRouter account instead of copying a key.",
    signin_offerAgain: "Sign in with OpenRouter again to replace the saved key.",
    signin_button: "Sign in with OpenRouter",
    signin_opening: "Opening the browser…",
    signin_waiting: "Waiting for the approval in the browser…",
    signin_openPage: "Open the OpenRouter page in the browser ↗",
    signin_codeWaiting: "Open the OpenRouter page, approve there, then paste the code it shows.",
    signin_codeLabel: "Code from OpenRouter",
    signin_codeUse: "Use this code",
    signin_code_invalid: "That does not look like a code from OpenRouter. Copy the code as the page shows it.",
    signin_link_invalid: "This sign-in has ended or was replaced. Start the sign-in again.",
    signin_verifying: "Approved. Verifying the key…",
    signin_hint: "OpenRouter creates a key for personagent, which is kept on this computer. Until you remove it at openrouter.ai/keys, the key can spend the credit of your OpenRouter account. The free models need no credit.",
    signin_done: "Signed in with OpenRouter. You can start chatting.",
    signin_denied: "Access was not approved on OpenRouter. Sign in again or paste a key.",
    signin_timeout: "The sign-in was not completed within ten minutes and has expired. Start it again.",
    signin_code_rejected: "OpenRouter did not accept the sign-in code; it may have expired. Start the sign-in again.",
    signin_exchange_failed: "OpenRouter did not return a key. Start the sign-in again, or paste a key.",
    signin_unreachable: "personagent could not reach OpenRouter to collect the key. Check the network connection and try again.",
    signin_key_rejected: "OpenRouter created a key, but it did not pass the check before saving. Start the sign-in again, or paste a key.",
    signin_provider: "Signing in is available for OpenRouter only.",
  },
  zh: {
    signin_offer: "可使用 OpenRouter 账号登录，无需复制密钥。",
    signin_offerAgain: "可重新通过 OpenRouter 登录，以替换已保存的密钥。",
    signin_button: "通过 OpenRouter 登录",
    signin_opening: "正在打开浏览器…",
    signin_waiting: "正在等候浏览器中的批准…",
    signin_openPage: "在浏览器中打开 OpenRouter 页面 ↗",
    signin_codeWaiting: "请打开 OpenRouter 页面并批准，然后粘贴页面上显示的代码。",
    signin_codeLabel: "OpenRouter 显示的代码",
    signin_codeUse: "使用此代码",
    signin_code_invalid: "这不像是 OpenRouter 提供的代码。请按页面显示的内容完整复制。",
    signin_link_invalid: "此次登录已结束或已被新的登录取代。请重新登录。",
    signin_verifying: "已批准，正在验证密钥…",
    signin_hint: "OpenRouter 会为 personagent 创建一个密钥，保存在本机。在 openrouter.ai/keys 删除该密钥之前，它可以使用你的 OpenRouter 账户余额。免费模型无需余额。",
    signin_done: "已通过 OpenRouter 登录，可以开始聊天。",
    signin_denied: "未在 OpenRouter 上批准访问。请重新登录，或填写密钥。",
    signin_timeout: "登录未在十分钟内完成，已失效。请重新开始。",
    signin_code_rejected: "OpenRouter 未接受登录代码，代码可能已过期。请重新登录。",
    signin_exchange_failed: "OpenRouter 未返回密钥。请重新登录，或填写密钥。",
    signin_unreachable: "personagent 无法连接 OpenRouter 以获取密钥。请检查网络连接后重试。",
    signin_key_rejected: "OpenRouter 已创建密钥，但未通过保存前的验证。请重新登录，或填写密钥。",
    signin_provider: "仅 OpenRouter 支持账号登录。",
  },
});
(() => {
  const { $, t } = PA;
  // idle, opening, waiting, verifying or failed, as the server last said.
  let phase = "idle";
  let error = "";
  let url = "";
  // From another device: the person pastes the code OpenRouter shows.
  let byCode = false;
  let timer = 0;
  let shown = "";
  let resumed = false;

  const box = document.createElement("div");
  box.id = "signin-box";
  box.className = "signin-box";
  box.hidden = true;
  $("settings-form").querySelector(".label-line").before(box);

  const row = document.createElement("div");
  row.className = "signin-row";
  const said = document.createElement("span");
  said.className = "signin-text";
  said.setAttribute("aria-live", "polite");
  const button = document.createElement("button");
  button.type = "button";
  button.className = "primary signin-use";
  row.append(said, button);
  const link = document.createElement("a");
  link.className = "signin-link";
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  const paste = document.createElement("form");
  paste.className = "signin-code";
  paste.noValidate = true;
  const pasteLabel = document.createElement("label");
  pasteLabel.htmlFor = "signin-code-input";
  const pasteInput = document.createElement("input");
  pasteInput.id = "signin-code-input";
  pasteInput.autocomplete = "off";
  pasteInput.spellcheck = false;
  const pasteUse = document.createElement("button");
  pasteUse.type = "submit";
  pasteUse.className = "primary";
  paste.append(pasteLabel, pasteInput, pasteUse);
  const failure = document.createElement("div");
  failure.className = "error signin-error";
  failure.setAttribute("role", "alert");
  const hint = document.createElement("p");
  hint.className = "field-note signin-hint";
  box.append(row, link, paste, failure, hint);

  const offered = () => $("provider").value === "openrouter";
  const replacing = () => Boolean(PA.state?.configured) && PA.state.provider === "openrouter";

  function render() {
    const now = [offered(), phase, error, url, byCode, replacing(), PA.lang].join("|");
    if (now === shown) return;
    shown = now;
    box.hidden = !offered() && (phase === "idle" || phase === "failed");
    const busy = phase === "opening" || phase === "verifying";
    const waiting = phase === "waiting";
    said.textContent =
      waiting ? t(byCode ? "signin_codeWaiting" : "signin_waiting")
      : phase === "verifying" ? t("signin_verifying")
      : t(replacing() ? "signin_offerAgain" : "signin_offer");
    button.textContent = waiting || phase === "verifying" ? t("cancel")
      : phase === "opening" ? t("signin_opening") : t("signin_button");
    button.disabled = busy;
    button.setAttribute("aria-busy", busy ? "true" : "false");
    // The way in is the form's main action until it waits; then the button only cancels.
    button.className = waiting || phase === "verifying" ? "secondary signin-use" : "primary signin-use";
    link.hidden = !(waiting && url);
    if (waiting && url) {
      link.href = url;
      link.textContent = t("signin_openPage");
    }
    paste.hidden = !(waiting && byCode);
    pasteLabel.textContent = t("signin_codeLabel");
    pasteUse.textContent = t("signin_codeUse");
    failure.hidden = phase !== "failed";
    failure.textContent = phase === "failed" ? t(error) : "";
    hint.textContent = t("signin_hint");
  }

  function follow(value) {
    phase = value.state === "idle" ? (phase === "opening" ? "opening" : "idle") : value.state;
    error = value.error || "";
    url = value.url || "";
    byCode = Boolean(value.byCode);
    if (phase === "waiting" || phase === "verifying") {
      if (!timer) timer = setInterval(poll, 1500);
    } else if (timer) {
      clearInterval(timer);
      timer = 0;
    }
    if (phase === "done") return finished();
    if (phase === "failed") PA.api("signin/cancel", {}).catch(() => {});
    render();
  }

  async function finished() {
    phase = "idle";
    // The server keeps no finished attempt once the page has seen it.
    PA.api("signin/cancel", {}).catch(() => {});
    try {
      await PA.reload();
    } catch {}
    render();
    PA.showView("chat");
    PA.toast(t("signin_done"));
  }

  paste.addEventListener("submit", async (event) => {
    event.preventDefault();
    const code = pasteInput.value.trim();
    if (!code) {
      pasteInput.focus();
      return;
    }
    pasteUse.disabled = true;
    try {
      const answer = await PA.api("signin/code", { code });
      pasteInput.value = "";
      follow(answer);
    } catch (caught) {
      phase = "failed";
      error = caught.message;
      render();
    } finally {
      pasteUse.disabled = false;
    }
  });

  async function poll() {
    try {
      follow(await PA.api("signin"));
    } catch {
      // The next tick asks again.
    }
  }

  async function start() {
    const state = PA.state || {};
    // A chosen personality replaces a persona the person wrote, as the form's save asks.
    if (
      state.character === "custom" &&
      $("character").value !== "custom" &&
      !(await PA.ask(t("personaReplaceAsk"), t("personaReplaceYes")))
    )
      return;
    phase = "opening";
    error = "";
    render();
    try {
      follow(await PA.api("signin/start", {
        provider: $("provider").value,
        form: PA.formValues(),
        pageLang: PA.lang,
      }));
    } catch (caught) {
      phase = "failed";
      error = caught.message;
      render();
    }
  }

  async function cancel() {
    button.disabled = true;
    try {
      follow(await PA.api("signin/cancel", {}));
    } catch (caught) {
      phase = "failed";
      error = caught.message;
      render();
    }
  }

  button.addEventListener("click", () => {
    if (phase === "waiting") cancel();
    else if (phase === "idle" || phase === "failed") start();
  });
  $("provider").addEventListener("change", render);

  PA.onState(async () => {
    if (!resumed) {
      resumed = true;
      // A page opened again while an attempt still waits picks it up.
      try {
        const value = await PA.api("signin");
        if (value.state === "waiting" || value.state === "verifying") follow(value);
      } catch {}
    }
    render();
  });
  PA.onLanguage(() => {
    shown = "";
    render();
  });
})();
