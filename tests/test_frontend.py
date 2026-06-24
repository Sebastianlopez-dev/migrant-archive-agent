"""Frontend build and structure verification for the chat widget."""

import json
import subprocess
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_DIR = _PROJECT_ROOT / "frontend"


def _read_text(rel_path: str) -> str:
    return (_FRONTEND_DIR / rel_path).read_text(encoding="utf-8")


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
    assert ".chat-bubble" in css
    assert ".chat-panel" in css
    assert "translateX" in css, "panel must use translateX for slide animation"


def test_chat_widget_class_has_required_methods():
    """chat-widget.ts must export a ChatWidget class with the expected API."""
    source = _read_text("src/chat-widget.ts")
    assert "export class ChatWidget" in source
    for method in ("createBubble", "createPanel", "togglePanel", "sendMessage", "renderMessage"):
        assert f"{method}(" in source, f"ChatWidget must implement {method}"
    assert "fetch('/api/ask'" in source or 'fetch("/api/ask"' in source


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


# ───────────────────────── Phase 7.5: Build verification ─────────────────────────


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
