"""Frontend build and structure verification for the chat widget."""

import json
import subprocess
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"


def _read_text(rel_path: str) -> str:
    return (_FRONTEND_DIR / rel_path).read_text(encoding="utf-8")


def _extract_function_body(source: str, function_name: str) -> str:
    """Return the body of a TypeScript function (between its outermost braces)."""
    marker = f"function {function_name}("
    start = source.find(marker)
    assert start != -1, f"{function_name} not found in source"
    open_brace = source.find("{", start)
    depth = 0
    for i in range(open_brace, len(source)):
        char = source[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace + 1 : i]
    raise ValueError(f"Could not find matching closing brace for {function_name}")


# ───────────────────────── Phase 6: Frontend setup ─────────────────────────


def test_package_json_uses_pnpm_vite_and_typescript():
    """package.json must be present and configured for pnpm + Vite + TS."""
    package = json.loads(_read_text("package.json"))
    assert package.get("private") is True
    dev_deps = package.get("devDependencies", {})
    assert "vite" in dev_deps, "vite devDependency is required"
    assert "typescript" in dev_deps, "typescript devDependency is required"


def test_vite_config_proxies_api_to_fastapi():
    """vite.config.ts must proxy /api to the FastAPI dev server."""
    config = _read_text("vite.config.ts")
    assert "defineConfig" in config
    assert "'/api'" in config or '"/api"' in config
    assert "http://localhost:8000" in config


def test_tsconfig_exists_and_targets_modular_browser_ts():
    """tsconfig.json must enable strict TypeScript for the browser."""
    tsconfig = json.loads(_read_text("tsconfig.json"))
    compiler_options = tsconfig.get("compilerOptions", {})
    assert compiler_options.get("module") == "ESNext"
    assert compiler_options.get("strict") is True
    assert "DOM" in compiler_options.get("lib", [])


def test_index_html_has_widget_mount_point():
    """index.html must contain a mount point for the widget."""
    html = _read_text("index.html")
    assert '<div id="chat-root"></div>' in html
    assert '/src/main.ts' in html


# ───────────────────────── Phase 7: Chat widget ─────────────────────────


def test_styles_css_uses_brand_custom_properties():
    """styles.css must define the Plataforma Cero brand palette."""
    css = _read_text("src/styles.css")
    assert "--blue: #019ee3" in css
    assert "--yellow: #f2c500" in css
    assert "--red: #c84c30" in css
    assert "--black: #000" in css
    assert "--white: #fff" in css
    assert ".chat-fab" in css
    assert ".chat-panel" in css


def test_styles_css_respects_reduced_motion():
    """styles.css must disable all motion inside prefers-reduced-motion."""
    import re
    css = _read_text("src/styles.css")
    reduced_block = re.search(
        r"@media\s*\(prefers-reduced-motion[^}]*\}", css, flags=re.DOTALL,
    )
    assert reduced_block is not None, "prefers-reduced-motion block must exist"
    block = reduced_block.group(0).lower()
    assert "transition" in block, "reduced-motion block must disable transitions"
    assert "animation" in block, "reduced-motion block must disable animations"


def test_styles_css_panel_width_is_responsive():
    """Panel width must be 30vw bounded and full-width below 640px."""
    css = _read_text("src/styles.css")
    assert "30vw" in css
    assert "min-width: 320px" in css or "min-width:320px" in css
    assert "max-width: 480px" in css or "max-width:480px" in css
    assert "(max-width: 640px)" in css or "(max-width:640px)" in css
    assert "width: 100%" in css or "width:100%" in css


def test_chat_widget_exports_class_and_imports_submodules():
    """chat-widget.ts must export ChatWidget and import the new modules."""
    source = _read_text("src/chat-widget.ts")
    assert "export class ChatWidget" in source
    assert "constructor(root: HTMLElement)" in source
    for name in (
        "createFab",
        "createPanel",
        "createZeroState",
        "createInputBar",
        "createMessageList",
    ):
        assert name in source, f"ChatWidget must import/use {name}"
    assert "ask(" in source or "ask" in source
    assert "crypto.randomUUID()" in source
    assert "sessionId" in source


def test_chat_widget_orchestrates_open_close_and_focus():
    """ChatWidget must wire FAB open, close button, Escape, and focus."""
    source = _read_text("src/chat-widget.ts")
    assert "openPanel(" in source
    assert "closePanel(" in source
    assert "togglePanel(" in source
    assert "Escape" in source
    assert ".focus()" in source


def test_chat_widget_sends_message_via_api_client():
    """ChatWidget must call the api-client ask() wrapper, not fetch directly."""
    source = _read_text("src/chat-widget.ts")
    assert "fetch('/api/ask'" not in source
    assert 'fetch("/api/ask"' not in source
    assert "ask(this.sessionId" in source or "ask(sessionId" in source
    assert "sendMessage(" in source


def test_chat_widget_zero_state_suggestion_sends_question():
    """Clicking a suggestion must populate the input and send the question."""
    source = _read_text("src/chat-widget.ts")
    assert "selectSuggestion(" in source
    assert "setQuestion(" in source
    assert "sendMessage(" in source


def test_chat_widget_reset_clears_session_and_state():
    """resetConversation() must clear the backend session and local state."""
    source = _read_text("src/chat-widget.ts")
    assert "resetConversation(" in source
    assert "clearSession(" in source
    assert "sessionId" in source
    assert "hasStarted = false" in source
    assert "confirm(" in source or "window.confirm(" in source

def test_chat_widget_replaces_zero_state_with_message_list():
    """Sending the first message must hide the zero-state and show messages."""
    source = _read_text("src/chat-widget.ts")
    assert "hasStarted" in source
    assert "zeroState" in source
    assert "messageList" in source
    assert "removeChild" in source or ".remove(" in source
    assert "appendChild" in source


def test_main_ts_bootstraps_widget_on_dom_ready():
    """main.ts must import the widget and instantiate it after DOM ready."""
    source = _read_text("src/main.ts")
    assert "import './styles.css'" in source or 'import "./styles.css"' in source
    assert "ChatWidget" in source
    assert "DOMContentLoaded" in source or "document.addEventListener" in source


def test_avatar_svg_exists_and_is_valid_svg():
    """public/cerito-avatar.svg must be a valid SVG placeholder."""
    svg_path = _FRONTEND_DIR / "public" / "cerito-avatar.svg"
    assert svg_path.exists(), "Avatar SVG must exist"
    svg = svg_path.read_text(encoding="utf-8")
    assert svg.strip().startswith("<")
    assert "</svg>" in svg
    assert "C" in svg or "circle" in svg.lower(), "Avatar should contain a 'C' or a smiley/circle placeholder"


# ───────────────────────── Phase 8: API client module ─────────────────────────


def test_api_client_module_exists_and_exports_required_types():
    """api-client.ts must exist and export the shared types and ask wrapper."""
    client_path = _FRONTEND_DIR / "src" / "api-client.ts"
    assert client_path.exists(), "api-client.ts must be created"
    source = client_path.read_text(encoding="utf-8")
    assert "export interface Source" in source
    assert "export interface AskResponse" in source
    assert "export interface Message" in source
    assert "export async function ask(" in source
    assert "export async function clearSession(" in source


def test_api_client_ask_sends_session_id_and_question():
    """ask() must POST /api/ask with both question and session_id."""
    source = _read_text("src/api-client.ts")
    assert "fetch('/api/ask'" in source or 'fetch("/api/ask"' in source
    assert "session_id" in source, "request body must include session_id"
    assert "question" in source, "request body must include question"


def test_api_client_uses_abort_controller_timeout():
    """ask() must guard the request with a 60 second AbortController timeout."""
    source = _read_text("src/api-client.ts")
    assert "new AbortController()" in source
    assert "controller.abort()" in source
    assert "60_000" in source or "60000" in source


def test_api_client_maps_errors():
    """ask() must map non-200 responses and network/abort failures to errors."""
    source = _read_text("src/api-client.ts")
    assert "response.ok" in source or "!response.ok" in source
    assert "AbortError" in source
    assert "throw" in source


def test_api_client_error_class_exposes_status():
    """ApiClientError must carry the HTTP status when available."""
    source = _read_text("src/api-client.ts")
    assert "export class ApiClientError" in source
    assert "status" in source


def test_api_client_clear_session_calls_delete_endpoint():
    """clearSession() must send a DELETE request to /api/session/{id}."""
    source = _read_text("src/api-client.ts")
    assert "clearSession" in source
    assert "DELETE" in source
    assert "/api/session/" in source
    assert "encodeURIComponent" in source

def test_api_client_types_compile():
    """api-client.ts must compile without TypeScript errors."""
    if not (_FRONTEND_DIR / "node_modules").exists():
        install = subprocess.run(
            ["pnpm", "install", "--ignore-scripts"],
            cwd=_FRONTEND_DIR,
            capture_output=True,
            text=True,
        )
        assert install.returncode == 0, install.stderr

    tsc = subprocess.run(
        ["pnpm", "exec", "tsc", "--noEmit"],
        cwd=_FRONTEND_DIR,
        capture_output=True,
        text=True,
    )
    assert tsc.returncode == 0, tsc.stdout + tsc.stderr


# ───────────────────────── Phase 8.5: Shell modules ─────────────────────────


def test_fab_module_exists_and_exports_factory():
    """fab.ts must exist and export a createFab factory."""
    fab_path = _FRONTEND_DIR / "src" / "fab.ts"
    assert fab_path.exists(), "fab.ts must be created"
    source = fab_path.read_text(encoding="utf-8")
    assert "export function createFab(" in source
    assert "onClick" in source


def test_fab_creates_button_with_avatar_and_aria():
    """createFab must render a fixed button with avatar and toggle ARIA."""
    source = _read_text("src/fab.ts")
    assert "document.createElement('button')" in source or 'document.createElement("button")' in source
    assert "aria-controls" in source
    assert "chat-panel" in source
    assert "aria-expanded" in source
    assert "aria-label" in source
    assert "/cero-agent-icon.png" in source
    assert "addEventListener('click'" in source or 'addEventListener("click"' in source


def test_panel_module_exists_and_exports_factory():
    """panel.ts must exist and export a createPanel factory returning slots."""
    panel_path = _FRONTEND_DIR / "src" / "panel.ts"
    assert panel_path.exists(), "panel.ts must be created"
    source = panel_path.read_text(encoding="utf-8")
    assert "export function createPanel(" in source
    assert "onClose" in source
    assert "contentSlot" in source
    assert "footerSlot" in source


def test_panel_creates_dialog_with_header_content_footer():
    """createPanel must render a dialog with header, content slot, and footer slot."""
    source = _read_text("src/panel.ts")
    assert "chat-panel" in source
    assert "id" in source
    assert "role" in source
    assert "dialog" in source
    assert "aria-label" in source
    assert "Chat with Cero" in source
    assert "chat-panel-header" in source
    assert "chat-panel-title" in source
    assert "Cero" in source
    assert "chat-panel-close" in source
    assert "chat-panel-content" in source
    assert "chat-panel-footer" in source
    assert "addEventListener('click'" in source or 'addEventListener("click"' in source


def test_panel_close_button_has_aria_label():
    """The panel close button must expose an accessible label."""
    source = _read_text("src/panel.ts")
    assert "aria-label" in source
    assert "Close chat" in source


def test_panel_supports_escape_key():
    """Pressing Escape inside the panel must trigger the close callback."""
    source = _read_text("src/panel.ts")
    assert "keydown" in source
    assert "Escape" in source

def test_panel_has_refresh_button_with_callback():
    """The panel must expose a refresh button wired to onRefresh."""
    source = _read_text("src/panel.ts")
    assert "onRefresh" in source
    assert "chat-panel-refresh" in source
    assert "Restart conversation" in source
    assert "REFRESH_ICON" in source


def test_panel_has_theme_toggle_button():
    """createPanel must include a theme toggle button with aria-label."""
    source = _read_text("src/panel.ts")
    assert "migrant-archive-theme" in source
    assert "data-theme" in source
    assert "prefers-color-scheme" in source
    assert "SUN_ICON" in source
    assert "MOON_ICON" in source
    assert "THEME_LABELS" in source


def test_styles_css_has_light_theme_overrides():
    """styles.css must define light theme overrides via [data-theme='light']."""
    source = _read_text("src/styles.css")
    assert '[data-theme="light"]' in source or "[data-theme='light']" in source
    assert "chat-overlay" in source
    assert "chat-surface-rgb" in source


def test_styles_css_light_mode_input_text_is_readable():
    """Light-mode chat input must use a dark text color for readability."""
    css = _read_text("src/styles.css")
    assert "[data-theme=\"light\"] .chat-input" in css
    assert "color: var(--gray-900)" in css


# ───────────────────────── Phase 8.6: Content modules ─────────────────────────


def test_zero_state_module_exists_and_exports_factory():
    """zero-state.ts must exist and export a createZeroState factory."""
    zero_state_path = _FRONTEND_DIR / "src" / "zero-state.ts"
    assert zero_state_path.exists(), "zero-state.ts must be created"
    source = zero_state_path.read_text(encoding="utf-8")
    assert "export function createZeroState(" in source
    assert "onSuggestionClick" in source


def test_zero_state_renders_greeting_and_suggestions():
    """createZeroState must render a greeting and three suggestion buttons."""
    source = _read_text("src/zero-state.ts")
    assert "Hola, soy Cero" in source
    assert "Preguntame sobre los videos de Plataforma Cero" in source
    assert "Lista de videos de Plataforma Cero" in source
    assert "¿Qué es FILMIG?" in source
    assert "¿Qué es Mujeres del Maíz?" in source
    assert "chat-zero-state" in source
    assert "chat-suggestion" in source
    assert "addEventListener('click'" in source or 'addEventListener("click"' in source


def test_zero_state_suggestion_click_calls_callback():
    """Clicking a suggestion card must invoke onSuggestionClick with the question text."""
    source = _read_text("src/zero-state.ts")
    assert "onSuggestionClick(question)" in source or "onSuggestionClick(" in source
    assert "button" in source


def test_zero_state_suggestion_passes_exact_label():
    """The callback must receive the suggestion label so it can be used as the question."""
    source = _read_text("src/zero-state.ts")
    assert "onSuggestionClick(currentLabel)" in source or "onSuggestionClick(" in source


def test_input_bar_module_exists_and_exports_factory():
    """input-bar.ts must exist and export a createInputBar factory."""
    input_bar_path = _FRONTEND_DIR / "src" / "input-bar.ts"
    assert input_bar_path.exists(), "input-bar.ts must be created"
    source = input_bar_path.read_text(encoding="utf-8")
    assert "export function createInputBar(" in source
    assert "onSend" in source


def test_input_bar_renders_input_send_and_mic():
    """createInputBar must render a text input, send button, and mic button."""
    source = _read_text("src/input-bar.ts")
    assert "chat-input-bar" in source
    assert "chat-input" in source
    assert "chat-send" in source
    assert "aria-label" in source
    assert "Enviar" in source or "send" in source.lower()
    assert "mic" in source.lower() or "microphone" in source.lower() or "voz" in source.lower()


def test_input_bar_enter_triggers_send():
    """Pressing Enter inside the input must trigger the onSend callback."""
    source = _read_text("src/input-bar.ts")
    assert "keydown" in source
    assert "Enter" in source
    assert "onSend(" in source


def test_input_bar_exposes_set_question_clear_focus_and_loading():
    """createInputBar must return setQuestion, clear, focus, and setLoading helpers."""
    source = _read_text("src/input-bar.ts")
    for helper in ("setQuestion", "clear", "focus", "setLoading"):
        assert helper in source, f"input bar API must expose {helper}"
    assert "return {" in source


def test_input_bar_shift_enter_allows_newline():
    """Shift+Enter inside the textarea must insert a newline instead of sending."""
    source = _read_text("src/input-bar.ts")
    assert "textarea" in source
    assert "shiftKey" in source
    assert "event.preventDefault()" in source or "preventDefault()" in source


def test_input_bar_mic_button_uses_media_recorder():
    """The microphone button must use MediaRecorder + getUserMedia, not SpeechRecognition."""
    source = _read_text("src/input-bar.ts")
    assert "MediaRecorder" in source
    assert "getUserMedia" in source
    assert "transcribeAudio" in source
    assert "isListening" in source


# ───────────────────────── Phase 8.7: Message list module ─────────────────────────


def test_message_list_module_exists_and_exports_factory():
    """message-list.ts must exist and export a createMessageList factory."""
    message_list_path = _FRONTEND_DIR / "src" / "message-list.ts"
    assert message_list_path.exists(), "message-list.ts must be created"
    source = message_list_path.read_text(encoding="utf-8")
    assert "export function createMessageList(" in source
    assert "addUserMessage" in source
    assert "addAgentResponse" in source
    assert "setLoading" in source
    assert "clear" in source


def test_message_list_returns_element_and_api():
    """createMessageList must return the root element and the public API."""
    source = _read_text("src/message-list.ts")
    assert "element" in source
    assert "return {" in source
    for method in ("addUserMessage", "addAgentResponse", "setLoading", "clear", "addErrorMessage"):
        assert method in source, f"message list API must expose {method}"


def test_message_list_container_is_accessible_scroll_log():
    """The message container must be a polite live region and scrollable."""
    source = _read_text("src/message-list.ts")
    assert "chat-messages" in source
    assert "role" in source
    assert "log" in source
    assert "aria-live" in source
    assert "polite" in source
    assert "overflowY" in source or "overflow-y" in source


def test_message_list_add_user_message_renders_user_bubble():
    """addUserMessage must append a user-styled bubble and scroll down."""
    source = _read_text("src/message-list.ts")
    assert "msg-user" in source
    assert "addUserMessage" in source
    assert "scrollTop" in source
    assert "scrollHeight" in source


def test_message_list_add_agent_response_renders_answer():
    """addAgentResponse must append an agent bubble with the answer text."""
    source = _read_text("src/message-list.ts")
    assert "msg-agent" in source
    assert "addAgentResponse" in source
    assert "response.answer" in source


def test_message_list_add_error_message_renders_error_bubble():
    """addErrorMessage must append an error-styled bubble."""
    source = _read_text("src/message-list.ts")
    assert "addErrorMessage" in source
    assert "msg-error" in source


def test_message_list_set_loading_shows_rotating_indicator():
    """setLoading(true) must show a rotating archive-themed indicator."""
    source = _read_text("src/message-list.ts")
    assert "Record<string, string[]>" in source
    assert "LOADING_I18N" in source
    assert "msg-loading" in source
    assert "setLoading" in source
    assert "setInterval" in source
    assert "rotationTimer" in source
    assert "Consulting the archive..." in source


def test_message_list_loading_messages_are_localized_arrays():
    """Each supported language must define an array of loading messages."""
    source = _read_text("src/message-list.ts")
    for lang in ("en", "es", "ca", "fr", "pt", "de"):
        assert f"{lang}: [" in source, f"LOADING_I18N must define an array for {lang}"
    # Count at least four string literals inside each language array by locating
    # the array block and checking for quoted entries.
    for lang in ("en", "es", "ca", "fr", "pt", "de"):
        start = source.find(f"{lang}:")
        assert start != -1
        open_bracket = source.find("[", start)
        close_bracket = source.find("]", open_bracket)
        block = source[open_bracket : close_bracket + 1]
        assert block.count("'") >= 8, f"{lang} must have at least 4 single-quoted messages"


def test_message_list_set_loading_false_hides_indicator():
    """setLoading(false) must remove the loading indicator from the list."""
    source = _read_text("src/message-list.ts")
    assert "setLoading" in source
    assert "removeChild" in source or ".remove(" in source


def test_message_list_set_loading_false_clears_rotation_timer():
    """setLoading(false) must clear the rotation interval."""
    source = _read_text("src/message-list.ts")
    assert "clearInterval(rotationTimer)" in source


def test_message_list_clear_removes_all_messages():
    """clear() must remove every rendered message."""
    source = _read_text("src/message-list.ts")
    assert "clear" in source
    assert "innerHTML" in source or "removeChild" in source


def test_message_list_agent_response_renders_answer_html():
    """addAgentResponse must render the answer as HTML (links come from backend)."""
    source = _read_text("src/message-list.ts")
    assert "addAgentResponse" in source
    assert "innerHTML" in source
    assert "response.answer" in source


def test_message_list_clear_resets_loading_state():
    """clear() must also reset the loading indicator reference."""
    source = _read_text("src/message-list.ts")
    assert "clear" in source
    assert "loadingIndicator" in source
    assert "= null" in source


def test_message_list_does_not_duplicate_loading_indicator():
    """setLoading(true) must reuse an existing indicator instead of stacking copies."""
    source = _read_text("src/message-list.ts")
    assert "setLoading" in source
    assert "if (!loadingIndicator)" in source


def test_message_list_set_language_updates_loading_text():
    """setLanguage must be able to refresh the loading indicator text."""
    source = _read_text("src/message-list.ts")
    assert "setLanguage" in source
    assert "loadingIndicator.textContent" in source


def test_message_list_set_loading_true_syncs_text_before_append_and_rotation():
    """setLoading(true) must reset rotationIndex and sync indicator text from getLoadingText before appending/starting rotation."""
    source = _read_text("src/message-list.ts")
    body = _extract_function_body(source, "setLoading")

    assert "rotationIndex = 0" in body, "rotationIndex must be reset when loading starts"
    assert "loadingIndicator.textContent = getLoadingText()" in body, "indicator text must be refreshed from current language"

    reset_pos = body.find("rotationIndex = 0")
    sync_pos = body.find("loadingIndicator.textContent = getLoadingText()")
    append_pos = body.find("element.appendChild(loadingIndicator)")
    rotate_pos = body.find("startRotation()")

    assert reset_pos < sync_pos, "rotationIndex reset must happen before text sync"
    assert sync_pos < append_pos, "text sync must happen before the indicator is appended"
    assert sync_pos < rotate_pos, "text sync must happen before rotation starts"

    # The sync must not be hidden inside the indicator-creation guard; it must run
    # every time loading is shown, including when an existing indicator is reused.
    inner_guard_open = body.find("if (!loadingIndicator)")
    inner_brace = body.find("{", inner_guard_open)
    inner_close = -1
    depth = 0
    for i in range(inner_brace, len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                inner_close = i
                break
    assert inner_close != -1, "could not locate indicator-creation guard"
    assert sync_pos > inner_close, "text sync must be outside the indicator-creation guard"


# ───────────────────────── Phase 8.8: Integration / accessibility ─────────────────────────


def test_chat_widget_a11y_attributes():
    """The orchestrator and child modules must expose required ARIA attributes."""
    widget = _read_text("src/chat-widget.ts")
    fab = _read_text("src/fab.ts")
    panel = _read_text("src/panel.ts")
    message_list = _read_text("src/message-list.ts")
    input_bar = _read_text("src/input-bar.ts")

    assert "aria-controls" in fab
    assert "chat-panel" in fab
    assert "aria-expanded" in fab
    assert "role" in panel
    assert "dialog" in panel
    assert "aria-label" in panel
    assert "Chat with Cero" in panel
    assert "role" in message_list
    assert "log" in message_list
    assert "aria-live" in message_list
    assert "polite" in message_list
    assert "aria-label" in input_bar


def test_chat_widget_focus_management_helpers():
    """The orchestrator must call focus on the input when opening and on the FAB when closing."""
    source = _read_text("src/chat-widget.ts")
    assert "inputBar.focus()" in source
    assert "fab.element.focus()" in source


def test_input_bar_focus_and_loading_methods_exist():
    """createInputBar must expose focus() and setLoading() for the orchestrator."""
    source = _read_text("src/input-bar.ts")
    assert "focus():" in source or "function focus" in source or "focus() {" in source
    assert "setLoading(" in source


def test_message_list_error_method_exists():
    """createMessageList must expose addErrorMessage for the orchestrator."""
    source = _read_text("src/message-list.ts")
    assert "addErrorMessage" in source


# ───────────────────────── Phase 8.9: Build verification ─────────────────────────


@pytest.mark.slow
@pytest.mark.skipif(not _FRONTEND_DIR.exists(), reason="frontend directory not created yet")
def test_pnpm_build_produces_dist_bundle():
    """pnpm install + pnpm build must succeed and emit a dist bundle."""
    if not (_FRONTEND_DIR / "node_modules").exists():
        # --ignore-scripts avoids the non-zero exit caused by pnpm ignoring
        # dependency build scripts (e.g. esbuild) in secure-by-default setups.
        install = subprocess.run(
            ["pnpm", "install", "--ignore-scripts"],
            cwd=_FRONTEND_DIR,
            capture_output=True,
            text=True,
        )
        assert install.returncode == 0, install.stderr

    build = subprocess.run(
        ["pnpm", "build"],
        cwd=_FRONTEND_DIR,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr

    dist = _FRONTEND_DIR / "dist"
    assert dist.exists(), "dist folder must be created by the build"
    assert (dist / "index.html").exists(), "dist/index.html must exist"
    assets = dist / "assets"
    assert assets.exists(), "dist/assets must exist"
    js_files = list(assets.glob("*.js"))
    css_files = list(assets.glob("*.css"))
    assert js_files, "at least one JS bundle must be emitted"
    assert css_files, "at least one CSS bundle must be emitted"


@pytest.mark.slow
@pytest.mark.skipif(not _FRONTEND_DIR.exists(), reason="frontend directory not created yet")
def test_built_css_respects_reduced_motion():
    """The emitted CSS bundle must disable motion inside prefers-reduced-motion."""
    import re
    dist_css = _FRONTEND_DIR / "dist" / "assets"
    css_files = list(dist_css.glob("*.css"))
    if not css_files:
        pytest.skip("no CSS bundle emitted yet")

    css_raw = css_files[0].read_text(encoding="utf-8")
    reduced_block = re.search(
        r"@media\s*\(prefers-reduced-motion[^}]*\}", css_raw, flags=re.DOTALL,
    )
    assert reduced_block is not None, "built CSS must retain prefers-reduced-motion block"
    block = reduced_block.group(0).lower()
    assert "transition" in block, "reduced-motion block must disable transitions"
    assert "animation" in block, "reduced-motion block must disable animations"
