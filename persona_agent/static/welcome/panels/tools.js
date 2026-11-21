// The tools panel: MCP servers the admin adds. See PA at the end of welcome.js.
PA.strings({
  en: {
    tools_title: "Tools",
    tools_hint: "Let the character use tools from MCP servers that you add, such as the current time or the text of a web page. It still writes every reply in its own voice: a tool is something it consults along the way, as it does with web search.",
    tools_warning: "Adding a server runs a program on this computer with your own user rights, or connects to the address you enter. What a tool returns is sent to the model service together with the conversation. Add only servers that you trust.",
    tools_cost: "While a tool is on, every message the character is going to answer from someone permitted to use it costs one additional small model request, which decides whether to use a tool or to search the web.",
    tools_apply: "Changes take effect within a few seconds; the character does not need to be restarted.",
    tools_loading: "Reading the tool settings…",
    tools_load_failed: "The tool settings could not be read.",
    tools_none: "No tool servers have been added.",
    tools_starters: "Ready to add. These need only uv, which the personagent installer provides:",
    tools_starter_time: "Time: the current time in any time zone, and conversion between time zones (mcp-server-time)",
    tools_starter_fetch: "Fetch: the text of the web page at a given address (mcp-server-fetch)",
    tools_starter_add: "Add",
    tools_starter_add_label: "Add {name}",
    tools_paste_label: "Configuration from the server's instructions",
    tools_paste_note: "Paste the whole mcpServers block as written for Claude Desktop or Cursor, a single server's entry, or a single server's object.",
    tools_name_label: "Name (optional)",
    tools_name_note: "Used when the pasted text does not name the server. Letters, digits, dots, dashes and underscores.",
    tools_add: "Add server",
    tools_adding: "Adding…",
    tools_added: "{names} was added. Its tools are on for the administrator only.",
    tools_fill: "Enter a program or an address instead",
    tools_kind_program: "A program on this computer",
    tools_kind_address: "An address (Streamable HTTP)",
    tools_command: "Command",
    tools_args: "Arguments, one per line",
    tools_env: "Environment variables, one NAME=value per line",
    tools_url: "Address",
    tools_headers: "Request headers, one Name: value per line",
    tools_secret_note: "Environment variables and request headers are stored privately in this home folder and are not shown again after saving.",
    tools_state_running: "Running",
    tools_state_starting: "Starting",
    tools_state_failed: "Not running",
    tools_state_off: "The character is not running; its servers start together with it.",
    tools_state_waiting: "Waiting for the character to start it",
    tools_program: "Program: {what}",
    tools_address: "Address: {what}",
    tools_secrets_set: "Secret values saved: {names}",
    tools_not_listed: "Its tools have not been read yet. Select Check to read them.",
    tools_no_tools: "This server offers no tools.",
    tools_check: "Check",
    tools_check_label: "Check {name}",
    tools_checking: "Checking…",
    tools_check_ok: "{name} is working and offers {count} tools.",
    tools_remove: "Remove",
    tools_remove_label: "Remove {name}",
    tools_remove_ask: "Remove {name}? Its program stops and its tools are no longer offered to the character.",
    tools_remove_yes: "Remove",
    tools_removed: "{name} was removed.",
    tools_on: "On",
    tools_on_label: "Use the tool {name}",
    tools_who_label: "Who may cause it to be used",
    tools_who_admin: "The administrator only",
    tools_who_anyone: "Anyone the character answers",
    tools_saved: "Saved.",
    tools_try: "Try",
    tools_try_close: "Close",
    tools_try_label: "Try {name}",
    tools_try_args: "Arguments (a JSON object)",
    tools_try_required: "required",
    tools_try_run: "Call the tool",
    tools_trying: "Calling…",
    tools_try_result: "What the character would receive:",
    tools_try_error_result: "The tool reported an error:",
    tools_try_cut: "The answer is longer than shown here.",
    tools_try_left_out: "Left out because it is not text: {kinds}",
    tools_try_bad_json: "The arguments are not a JSON object.",
    tools_try_bad_number: "{field} must be a number.",
    tools_try_note: "Trying a tool starts its program on a connection of its own; the character is not involved.",
    tools_err_not_found: "The program was not found: {detail}. Check that it is installed and that the command is spelled correctly.",
    tools_err_exited: "The program stopped before it was ready. Its last output:",
    tools_exit_code: "Exit code {code}",
    tools_err_refused: "The address refused the connection.",
    tools_err_timeout: "The server did not answer in time.",
    tools_err_oauth: "The server requires signing in through OAuth, which personagent does not support yet. Use a server that accepts a key in a request header.",
    tools_err_http: "The address answered with an error ({detail}).",
    tools_err_protocol: "The answer is not one that an MCP server gives.",
    tools_err_too_large: "The answer is larger than personagent accepts.",
    tools_err_closed: "The connection was closed.",
    tools_err_sse_unsupported: "This server uses the older SSE transport, which personagent does not support. Use its Streamable HTTP address.",
    tools_err_bad_arguments: "The arguments do not match what the tool expects: {detail}",
    tools_bad_snippet: "This is not a server configuration that personagent can read. Paste the block from the server's instructions, or enter a command or an address.",
    tools_bad_name: "A server name has 1 to 40 letters, digits, dots, dashes or underscores, and begins with a letter or digit.",
    tools_bad_url: "The address must begin with http:// or https:// and must not contain a user name or password.",
    tools_name_taken: "A server with this name has already been added. Enter another name.",
    tools_too_many: "No more servers can be added. Remove one first.",
    tools_unknown_server: "This server is no longer in the settings. The list has been read again.",
    tools_unknown_tool: "This tool is not in the server's list. Select Check to read the list again.",
    tools_sse_unsupported: "This server uses the older SSE transport, which personagent does not support. Use its Streamable HTTP address.",
    tools_write_failed: "The tool settings file could not be written. Close any program that is using it, then try again.",
    tools_bad_request: "This request is not valid.",
    tools_destructive: "This tool's server marks it as destructive, so only the admin can cause it to be used.",
    tools_local_address: "An address on this computer or its local network can be added and used only on the computer personagent runs on.",
    tools_file_damaged: "The file mcp.json in the home folder cannot be read as JSON. Correct it or remove it, then try again.",
    tools_state_disabled: "Switched off in mcp.json",
    tools_local_only: "A server that runs a program can be added only on the computer personagent runs on, from its own page or with `personagent tools add`. A server at an address can be added from here.",
  },
  zh: {
    tools_title: "工具",
    tools_hint: "让角色使用你添加的 MCP 服务器提供的工具，例如查询当前时间或读取网页内容。角色仍以自己的口吻撰写每条回复：工具只是回复前查阅的内容，与联网搜索相同。",
    tools_warning: "添加服务器会以你本人的用户权限在本机运行一个程序，或连接到你填写的地址。工具返回的内容会与对话一起发送给模型服务。请只添加你信任的服务器。",
    tools_cost: "开启任一工具后，角色每次准备回复有权使用工具者的消息时，都会额外发出一次小型模型请求，用于判断是否使用工具或联网搜索。",
    tools_apply: "更改在几秒内生效，无需重启角色。",
    tools_loading: "正在读取工具设置…",
    tools_load_failed: "无法读取工具设置。",
    tools_none: "尚未添加工具服务器。",
    tools_starters: "可直接添加。以下服务器只需要 uv，personagent 的安装程序已提供：",
    tools_starter_time: "时间：查询任一时区的当前时间，并在时区之间换算（mcp-server-time）",
    tools_starter_fetch: "网页读取：读取指定地址网页的文字内容（mcp-server-fetch）",
    tools_starter_add: "添加",
    tools_starter_add_label: "添加 {name}",
    tools_paste_label: "服务器说明中的配置",
    tools_paste_note: "可粘贴为 Claude Desktop 或 Cursor 编写的完整 mcpServers 配置、单个服务器的条目，或单个服务器的对象。",
    tools_name_label: "名称（可选）",
    tools_name_note: "粘贴的内容未给出服务器名称时使用。可包含字母、数字、点、短横线和下划线。",
    tools_add: "添加服务器",
    tools_adding: "正在添加…",
    tools_added: "已添加 {names}。其工具已开启，仅限管理员使用。",
    tools_fill: "改为填写程序或地址",
    tools_kind_program: "本机上的程序",
    tools_kind_address: "地址（Streamable HTTP）",
    tools_command: "命令",
    tools_args: "参数，每行一个",
    tools_env: "环境变量，每行一个，格式为 NAME=value",
    tools_url: "地址",
    tools_headers: "请求头，每行一个，格式为 Name: value",
    tools_secret_note: "环境变量和请求头以私密方式保存在此主目录中，保存后不再显示。",
    tools_state_running: "运行中",
    tools_state_starting: "正在启动",
    tools_state_failed: "未运行",
    tools_state_off: "角色未在运行；其服务器会随角色一同启动。",
    tools_state_waiting: "等待角色启动该服务器",
    tools_program: "程序：{what}",
    tools_address: "地址：{what}",
    tools_secrets_set: "已保存的私密值：{names}",
    tools_not_listed: "尚未读取其工具。请点击「检查」读取。",
    tools_no_tools: "该服务器未提供工具。",
    tools_check: "检查",
    tools_check_label: "检查 {name}",
    tools_checking: "正在检查…",
    tools_check_ok: "{name} 工作正常，提供 {count} 个工具。",
    tools_remove: "移除",
    tools_remove_label: "移除 {name}",
    tools_remove_ask: "确定移除 {name}？其程序将停止运行，角色也不再使用其工具。",
    tools_remove_yes: "移除",
    tools_removed: "已移除 {name}。",
    tools_on: "开启",
    tools_on_label: "使用工具 {name}",
    tools_who_label: "可触发使用者",
    tools_who_admin: "仅管理员",
    tools_who_anyone: "角色回复的任何人",
    tools_saved: "已保存。",
    tools_try: "试用",
    tools_try_close: "关闭",
    tools_try_label: "试用 {name}",
    tools_try_args: "参数（JSON 对象）",
    tools_try_required: "必填",
    tools_try_run: "调用工具",
    tools_trying: "正在调用…",
    tools_try_result: "角色将得到的内容：",
    tools_try_error_result: "工具报告了错误：",
    tools_try_cut: "返回内容超出此处显示的长度。",
    tools_try_left_out: "因不是文字而未传递：{kinds}",
    tools_try_bad_json: "参数不是 JSON 对象。",
    tools_try_bad_number: "{field} 须为数字。",
    tools_try_note: "试用时会为该工具单独启动程序并建立连接，与角色无关。",
    tools_err_not_found: "找不到程序：{detail}。请确认已安装该程序，且命令拼写正确。",
    tools_err_exited: "程序在就绪前已停止。其最后输出：",
    tools_exit_code: "退出码 {code}",
    tools_err_refused: "该地址拒绝了连接。",
    tools_err_timeout: "服务器未在规定时间内响应。",
    tools_err_oauth: "该服务器要求通过 OAuth 登录，personagent 暂不支持。请使用可在请求头中填写密钥的服务器。",
    tools_err_http: "该地址返回了错误（{detail}）。",
    tools_err_protocol: "返回的内容不是 MCP 服务器的应答。",
    tools_err_too_large: "返回的内容超出 personagent 可接受的大小。",
    tools_err_closed: "连接已关闭。",
    tools_err_sse_unsupported: "该服务器使用旧版 SSE 传输方式，personagent 不支持。请使用其 Streamable HTTP 地址。",
    tools_err_bad_arguments: "参数与工具的要求不符：{detail}",
    tools_bad_snippet: "personagent 无法读取此服务器配置。请粘贴服务器说明中的配置，或填写命令或地址。",
    tools_bad_name: "服务器名称为 1 至 40 个字母、数字、点、短横线或下划线，并以字母或数字开头。",
    tools_bad_url: "地址须以 http:// 或 https:// 开头，且不得包含用户名或密码。",
    tools_name_taken: "已添加同名服务器，请填写其他名称。",
    tools_too_many: "无法再添加服务器，请先移除一个。",
    tools_unknown_server: "该服务器已不在设置中，列表已重新读取。",
    tools_unknown_tool: "该工具不在服务器的列表中。请点击「检查」重新读取。",
    tools_sse_unsupported: "该服务器使用旧版 SSE 传输方式，personagent 不支持。请使用其 Streamable HTTP 地址。",
    tools_write_failed: "无法写入工具设置文件。请关闭正在使用该文件的程序后重试。",
    tools_bad_request: "该请求无效。",
    tools_destructive: "该工具的服务器将其标记为破坏性工具，因此只有管理员可以让角色使用它。",
    tools_local_address: "本机或局域网中的地址只能在运行 personagent 的电脑上添加和使用。",
    tools_file_damaged: "无法将主目录中的 mcp.json 读取为 JSON。请修正或删除该文件后重试。",
    tools_state_disabled: "已在 mcp.json 中关闭",
    tools_local_only: "运行程序的服务器只能在运行 personagent 的电脑上添加：可使用该电脑上的页面，或运行 `personagent tools add`。通过地址连接的服务器可以在此处添加。",
  },
});
(() => {
  const root = PA.$("tools-root");
  let data = null;
  let shown = "";
  let loadError = false;
  // What is typed survives a rebuild of the panel.
  const draft = { snippet: "", name: "", kind: "program", command: "", args: "", env: "", url: "", headers: "", fillOpen: false };
  let addError = "";
  let busyId = "";
  // Per server: the message under it ({ok, text, lines}); per tool: its open try form.
  const notes = {};
  const tries = {};
  let returnTo = null;

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const slug = (text) => String(text).replace(/[^A-Za-z0-9_-]/g, (c) => `_${c.charCodeAt(0).toString(16)}`);
  const button = (id, className, label, onClick, aria) => {
    const node = make("button", className, label);
    node.type = "button";
    node.id = id;
    if (aria) node.setAttribute("aria-label", aria);
    node.disabled = !!busyId;
    node.addEventListener("click", () => onClick(node));
    return node;
  };
  const errorBox = (text, id) => {
    const box = make("div", "error", text || "");
    box.id = id;
    box.setAttribute("role", "alert");
    box.hidden = !text;
    return box;
  };
  const failure = (code, detail) => {
    const key = `tools_err_${code}`;
    return PA.t(key, { detail: detail || "" });
  };

  function visible() {
    const on = !!(PA.state && PA.state.configured && PA.view === "settings");
    root.hidden = !on;
    return on;
  }

  async function load() {
    try {
      take(await PA.api("tools"));
      loadError = false;
    } catch {
      loadError = !data;
      if (loadError) render();
    }
  }

  // Rebuilt only when what it shows changed, so a poll never takes a click or the keyboard's place.
  function take(next, force = false) {
    const sign = JSON.stringify(next);
    data = next;
    if (force || sign !== shown) {
      shown = sign;
      render();
    }
  }

  async function act(id, label, work) {
    busyId = id;
    returnTo = id;
    render();
    const node = PA.$(id);
    if (node) node.textContent = PA.t(label);
    try {
      await work();
    } finally {
      busyId = "";
      // The busy render dropped the focus from the disabled control: it goes back there.
      if (!returnTo) returnTo = id;
      render();
    }
  }

  function addPayload(starter) {
    if (starter) return { starter };
    if (draft.snippet.trim()) return { snippet: draft.snippet, name: draft.name.trim() };
    if (draft.fillOpen && draft.kind === "program" && draft.command.trim())
      return { name: draft.name.trim(), command: draft.command.trim(), args: draft.args, env: draft.env };
    if (draft.fillOpen && draft.kind === "address" && draft.url.trim())
      return { name: draft.name.trim(), url: draft.url.trim(), headers: draft.headers };
    return null;
  }

  async function add(id, starter) {
    const payload = addPayload(starter);
    addError = "";
    if (!payload) {
      addError = "tools_bad_snippet";
      returnTo = draft.fillOpen ? (draft.kind === "program" ? "tools-command" : "tools-url") : "tools-snippet";
      render();
      return;
    }
    await act(id, "tools_adding", async () => {
      try {
        const result = await PA.api("tools/add", payload);
        if (!starter) Object.assign(draft, { snippet: "", name: "", command: "", args: "", env: "", url: "", headers: "" });
        shown = "";
        data = result;
        PA.toast(PA.t("tools_added", { names: result.added.join(", ") }));
      } catch (error) {
        addError = error.message;
      }
    });
  }

  async function check(server) {
    const id = `tools-check-${slug(server)}`;
    await act(id, "tools_checking", async () => {
      try {
        const result = await PA.api("tools/check", { server });
        data = result.view;
        shown = "";
        notes[server] = result.ok
          ? { ok: true, text: PA.t("tools_check_ok", { name: server, count: String(result.tools) }) }
          : explain(result);
      } catch (error) {
        notes[server] = { ok: false, text: PA.t(error.message) };
        if (error.message === "tools_unknown_server") await load();
      }
    });
  }

  function explain(result) {
    const text = failure(result.error, result.error === "exited" ? "" : result.detail);
    // The program's own output stays as it was written; only the exit code is put in the page's words.
    const lines = result.error === "exited"
      ? String(result.detail || "").replace(/^exit code (-?\d+)/, (_, code) => PA.t("tools_exit_code", { code }))
      : "";
    return { ok: false, text, lines };
  }

  async function remove(server, node) {
    if (!(await PA.ask(PA.t("tools_remove_ask", { name: server }), PA.t("tools_remove_yes")))) {
      node.focus();
      return;
    }
    await act(node.id, "tools_remove", async () => {
      try {
        data = await PA.api("tools/remove", { server });
        shown = "";
        delete notes[server];
        returnTo = "tools-snippet";
        PA.toast(PA.t("tools_removed", { name: server }));
      } catch (error) {
        notes[server] = { ok: false, text: PA.t(error.message) };
      }
    });
  }

  async function setTool(server, tool, change, control) {
    returnTo = control.id;
    control.disabled = true;
    try {
      take(await PA.api("tools/set", { server, tool, ...change }), true);
      PA.toast(PA.t("tools_saved"));
    } catch (error) {
      notes[server] = { ok: false, text: PA.t(error.message) };
      take(data, true);
    }
  }

  // A form from the input schema when every argument is a plain value; a JSON box otherwise.
  function simpleFields(schema) {
    const props = schema && typeof schema === "object" ? schema.properties || {} : {};
    const entries = Object.entries(props);
    if (entries.length > 8) return null;
    for (const [, prop] of entries) {
      const kind = Array.isArray(prop?.type) ? null : prop?.type;
      if (!Array.isArray(prop?.enum) && !["string", "number", "integer", "boolean"].includes(kind)) return null;
    }
    return entries;
  }

  function collect(form, tool) {
    if (!form.fields) {
      let value;
      try {
        value = JSON.parse(form.json || "{}");
      } catch {
        value = null;
      }
      if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(PA.t("tools_try_bad_json"));
      return value;
    }
    const out = {};
    for (const [name, prop] of form.fields) {
      const raw = form.values[name];
      if (prop.type === "boolean") {
        if (raw !== undefined) out[name] = !!raw;
        continue;
      }
      if (raw === undefined || raw === "") continue;
      if (Array.isArray(prop.enum)) {
        out[name] = prop.enum[Number(raw)];
      } else if (prop.type === "number" || prop.type === "integer") {
        const number = Number(raw);
        if (!Number.isFinite(number)) throw new Error(PA.t("tools_try_bad_number", { field: name }));
        out[name] = number;
      } else out[name] = raw;
    }
    return out;
  }

  async function runTry(server, tool, node) {
    const key = `${server}\u0000${tool.name}`;
    const form = tries[key];
    form.result = null;
    form.error = "";
    let args;
    try {
      args = collect(form, tool);
    } catch (error) {
      form.error = error.message;
      returnTo = node.id;
      render();
      return;
    }
    await act(node.id, "tools_trying", async () => {
      try {
        const result = await PA.api("tools/call", { server, tool: tool.name, arguments: args });
        if (result.ok) form.result = result;
        else {
          const said = explain(result);
          form.error = said.text + (said.lines ? `\n${said.lines}` : "");
        }
      } catch (error) {
        form.error = PA.t(error.message);
      }
    });
  }

  function tryForm(server, tool) {
    const key = `${server}\u0000${tool.name}`;
    const form = tries[key];
    const base = `tools-try-${slug(server)}-${slug(tool.name)}`;
    const box = make("div", "tools-try");
    box.id = `${base}-box`;
    if (form.fields === undefined) form.fields = simpleFields(tool.inputSchema);
    const required = new Set(tool.inputSchema?.required || []);
    if (form.fields) {
      for (const [name, prop] of form.fields) {
        const id = `${base}-f-${slug(name)}`;
        if (prop.type === "boolean" && !Array.isArray(prop.enum)) {
          const label = make("label", "check");
          const input = make("input");
          input.type = "checkbox";
          input.id = id;
          input.checked = !!form.values[name];
          input.addEventListener("change", () => (form.values[name] = input.checked));
          label.append(input, make("span", "", name));
          box.append(label);
        } else {
          const label = make("label", "", required.has(name) ? `${name} (${PA.t("tools_try_required")})` : name);
          label.htmlFor = id;
          let input;
          if (Array.isArray(prop.enum)) {
            input = make("select");
            input.append(make("option", "", ""));
            prop.enum.forEach((value, index) => {
              const option = make("option", "", String(value));
              option.value = String(index);
              input.append(option);
            });
          } else {
            input = make("input");
            input.autocomplete = "off";
            input.spellcheck = false;
            if (prop.type === "number" || prop.type === "integer") input.inputMode = "decimal";
          }
          input.id = id;
          input.value = form.values[name] ?? "";
          input.addEventListener("input", () => (form.values[name] = input.value));
          input.addEventListener("change", () => (form.values[name] = input.value));
          box.append(label, input);
          if (prop.description) box.append(make("p", "field-note", String(prop.description).slice(0, 300)));
        }
      }
    } else {
      const label = make("label", "", PA.t("tools_try_args"));
      label.htmlFor = `${base}-json`;
      const area = make("textarea", "tools-json");
      area.id = `${base}-json`;
      area.rows = 5;
      area.spellcheck = false;
      area.value = form.json ?? "{}";
      area.addEventListener("input", () => (form.json = area.value));
      box.append(label, area);
    }
    const line = make("div", "tools-try-actions");
    line.append(
      button(`${base}-run`, "secondary", PA.t("tools_try_run"), (self) => runTry(server, tool, self)),
      button(`${base}-close`, "quiet", PA.t("tools_try_close"), () => {
        delete tries[key];
        returnTo = `${base}-open`;
        render();
      }),
    );
    box.append(line, make("p", "field-note", PA.t("tools_try_note")));
    if (form.result) {
      const out = make("div", `tools-result${form.result.isError ? " is-error" : ""}`);
      out.setAttribute("role", "status");
      out.append(make("p", "tools-result-head", PA.t(form.result.isError ? "tools_try_error_result" : "tools_try_result")));
      out.append(make("pre", "tools-result-text", form.result.text || ""));
      if (form.result.cut) out.append(make("p", "field-note", PA.t("tools_try_cut")));
      if (form.result.leftOut?.length)
        out.append(make("p", "field-note", PA.t("tools_try_left_out", { kinds: form.result.leftOut.join(", ") })));
      box.append(out);
    }
    const error = errorBox(form.error, `${base}-error`);
    error.classList.add("tools-pre");
    box.append(error);
    box.addEventListener("keydown", (event) => {
      if (event.key === "Escape") PA.$(`${base}-close`)?.click();
    });
    return box;
  }

  function toolRow(server, tool) {
    const base = `tools-t-${slug(server.name)}-${slug(tool.name)}`;
    const row = make("li", "tools-tool");
    const head = make("div", "tools-tool-head");
    head.append(make("code", "tools-tool-name", tool.name));
    if (tool.title && tool.title !== tool.name) head.append(make("span", "tools-tool-title", tool.title));
    row.append(head);
    if (tool.description) row.append(make("p", "tools-tool-desc", tool.description));
    const controls = make("div", "tools-tool-controls");
    const label = make("label", "check");
    const box = make("input");
    box.type = "checkbox";
    box.id = `${base}-on`;
    box.checked = tool.enabled;
    box.disabled = !!busyId;
    box.setAttribute("aria-label", PA.t("tools_on_label", { name: tool.name }));
    box.addEventListener("change", () => setTool(server.name, tool.name, { enabled: box.checked }, box));
    label.append(box, make("span", "", PA.t("tools_on")));
    const whoLabel = make("label", "tools-who-label", PA.t("tools_who_label"));
    whoLabel.htmlFor = `${base}-who`;
    const who = make("select", "tools-who");
    who.id = `${base}-who`;
    who.disabled = !!busyId;
    for (const value of ["admin", "anyone"]) {
      const option = make("option", "", PA.t(`tools_who_${value}`));
      option.value = value;
      who.append(option);
    }
    who.value = tool.who;
    who.addEventListener("change", () => setTool(server.name, tool.name, { who: who.value }, who));
    const key = `${server.name}\u0000${tool.name}`;
    const open = button(`tools-try-${slug(server.name)}-${slug(tool.name)}-open`, "quiet", PA.t("tools_try"), () => {
      if (tries[key]) delete tries[key];
      else {
        tries[key] = { values: {}, json: undefined, result: null, error: "" };
        returnTo = `tools-try-${slug(server.name)}-${slug(tool.name)}-run`;
      }
      render();
    }, PA.t("tools_try_label", { name: tool.name }));
    open.setAttribute("aria-expanded", String(!!tries[key]));
    const whoWrap = make("div", "tools-who-wrap");
    whoWrap.append(whoLabel, who);
    controls.append(label, whoWrap, open);
    row.append(controls);
    if (tries[key]) row.append(tryForm(server.name, tool));
    return row;
  }

  function stateLine(server) {
    if (server.disabled) return make("span", "feature-state", PA.t("tools_state_disabled"));
    if (!data.running) return make("span", "feature-state", PA.t("tools_state_off"));
    const word = { running: "tools_state_running", starting: "tools_state_starting", failed: "tools_state_failed" }[server.state]
      || "tools_state_waiting";
    const line = make("span", `feature-state tools-state is-${server.state || "waiting"}`, PA.t(word));
    return line;
  }

  function serverBlock(server) {
    const box = make("div", "feature tools-server");
    box.id = `tools-s-${slug(server.name)}`;
    const head = make("div", "feature-head tools-server-head");
    head.append(make("strong", "", server.name), stateLine(server));
    box.append(head);
    const what = server.kind === "program" ? [server.command, ...server.args].join(" ") : server.url;
    box.append(make("p", "tools-where", PA.t(server.kind === "program" ? "tools_program" : "tools_address", { what })));
    const secrets = [...server.env, ...server.headers].filter((item) => item.set).map((item) => item.name);
    if (secrets.length) box.append(make("p", "field-note", PA.t("tools_secrets_set", { names: secrets.join(", ") })));
    if (data.running && server.state === "failed" && server.error) {
      const said = explain({ error: server.error, detail: server.detail });
      const err = errorBox(said.text + (said.lines ? `\n${said.lines}` : ""), `tools-s-${slug(server.name)}-state`);
      err.classList.add("tools-pre");
      box.append(err);
    }
    const actions = make("div", "tools-server-actions");
    actions.append(
      button(`tools-check-${slug(server.name)}`, "secondary", PA.t("tools_check"), () => check(server.name),
        PA.t("tools_check_label", { name: server.name })),
      button(`tools-remove-${slug(server.name)}`, "quiet", PA.t("tools_remove"), (self) => remove(server.name, self),
        PA.t("tools_remove_label", { name: server.name })),
    );
    box.append(actions);
    const note = notes[server.name];
    if (note) {
      if (note.ok) {
        const done = make("p", "tools-done", note.text);
        done.setAttribute("role", "status");
        box.append(done);
      } else {
        const err = errorBox(note.text + (note.lines ? `\n${note.lines}` : ""), `tools-s-${slug(server.name)}-note`);
        err.classList.add("tools-pre");
        box.append(err);
      }
    }
    if (!server.listed) box.append(make("p", "field-note", PA.t("tools_not_listed")));
    else if (!server.tools.length) box.append(make("p", "field-note", PA.t("tools_no_tools")));
    else {
      const list = make("ul", "tools-list");
      list.append(...server.tools.map((tool) => toolRow(server, tool)));
      box.append(list);
    }
    return box;
  }

  function field(id, label, value, onInput, { area = false, rows = 3, note = "" } = {}) {
    const wrap = make("div", "tools-field");
    const head = make("label", "", PA.t(label));
    head.htmlFor = id;
    const input = make(area ? "textarea" : "input");
    input.id = id;
    input.spellcheck = false;
    input.autocomplete = "off";
    if (area) input.rows = rows;
    input.value = value;
    input.addEventListener("input", () => onInput(input.value));
    wrap.append(head, input);
    if (note) wrap.append(make("p", "field-note", PA.t(note)));
    return wrap;
  }

  function adder() {
    const part = make("div", "tools-add");
    if (data.starters.length) {
      part.append(make("p", "tools-lead", PA.t("tools_starters")));
      const list = make("ul", "tools-starters");
      for (const starter of data.starters) {
        const item = make("li", "tools-starter");
        item.append(make("span", "", PA.t(`tools_starter_${starter.id}`)),
          button(`tools-starter-${starter.id}`, "secondary", PA.t("tools_starter_add"), (self) => add(self.id, starter.id),
            PA.t("tools_starter_add_label", { name: starter.id })));
        list.append(item);
      }
      part.append(list);
    }
    part.append(field("tools-snippet", "tools_paste_label", draft.snippet, (v) => (draft.snippet = v),
      { area: true, rows: 6, note: "tools_paste_note" }));
    part.append(field("tools-name", "tools_name_label", draft.name, (v) => (draft.name = v), { note: "tools_name_note" }));
    const fill = make("details", "tools-fill");
    fill.id = "tools-fill";
    fill.open = draft.fillOpen;
    fill.addEventListener("toggle", () => (draft.fillOpen = fill.open));
    const summary = make("summary", "", PA.t("tools_fill"));
    summary.id = "tools-fill-summary";
    fill.append(summary);
    const kinds = make("div", "tools-kinds");
    kinds.setAttribute("role", "radiogroup");
    for (const kind of ["program", "address"]) {
      const label = make("label", "check");
      const radio = make("input");
      radio.type = "radio";
      radio.name = "tools-kind";
      radio.id = `tools-kind-${kind}`;
      radio.checked = draft.kind === kind;
      radio.addEventListener("change", () => {
        draft.kind = kind;
        returnTo = radio.id;
        render();
      });
      label.append(radio, make("span", "", PA.t(`tools_kind_${kind}`)));
      kinds.append(label);
    }
    fill.append(kinds);
    if (draft.kind === "program") {
      fill.append(field("tools-command", "tools_command", draft.command, (v) => (draft.command = v)),
        field("tools-args", "tools_args", draft.args, (v) => (draft.args = v), { area: true }),
        field("tools-env", "tools_env", draft.env, (v) => (draft.env = v), { area: true, note: "tools_secret_note" }));
    } else {
      fill.append(field("tools-url", "tools_url", draft.url, (v) => (draft.url = v)),
        field("tools-headers", "tools_headers", draft.headers, (v) => (draft.headers = v), { area: true, note: "tools_secret_note" }));
    }
    part.append(fill);
    const actions = make("div", "card-actions");
    actions.append(button("tools-add", "primary", PA.t("tools_add"), (self) => add(self.id)));
    part.append(errorBox(addError ? PA.t(addError) : "", "tools-add-error"), actions);
    return part;
  }

  function render() {
    if (!visible()) return;
    const parts = [make("h2", "", PA.t("tools_title"))];
    parts.push(make("p", "field-note", PA.t("tools_hint")));
    const warn = make("p", "tools-warning", PA.t("tools_warning"));
    parts.push(warn);
    if (!data) {
      const wait = make("p", "field-note", PA.t(loadError ? "tools_load_failed" : "tools_loading"));
      wait.setAttribute("role", loadError ? "alert" : "status");
      parts.push(wait);
    } else {
      parts.push(make("p", "field-note", PA.t("tools_cost") + " " + PA.t("tools_apply")));
      if (!data.servers.length) parts.push(make("p", "field-note tools-none", PA.t("tools_none")));
      for (const server of data.servers) parts.push(serverBlock(server));
      parts.push(adder());
    }
    // Focus, and where the caret was, stay with the control the person used.
    const active = document.activeElement;
    const caret = active && root.contains(active) && "selectionStart" in active
      ? [active.selectionStart, active.selectionEnd] : null;
    const wanted = active && root.contains(active) && active.id ? [active.id, returnTo]
      : !active || active === document.body ? [returnTo] : [];
    returnTo = null;
    root.replaceChildren(...parts);
    for (const id of wanted) {
      const target = id && PA.$(id);
      if (target && root.contains(target) && !target.disabled) {
        target.focus();
        if (caret && id === active?.id && "setSelectionRange" in target && target.type !== "checkbox"
          && target.type !== "radio") {
          try {
            target.setSelectionRange(caret[0], caret[1]);
          } catch {}
        }
        break;
      }
    }
  }

  PA.onShow("settings", () => {
    if (visible()) load();
  });
  PA.onState(() => {
    if (visible() && !busyId) load();
  });
  PA.onLanguage(() => data && render());
  render();
})();
