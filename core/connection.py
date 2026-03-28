"""
Módulo de autenticación con GitLab.

Cadena de resolución de credenciales (en orden):
  1. Token en caché local (~/.config/glabmanager/token.json)
  2. Variable de entorno GITLAB_PRIVATE_TOKEN
  3. Flujo interactivo:
       a) OAuth 2.0 + PKCE  →  abre el navegador, captura el redirect
       b) Personal Access Token  →  el usuario lo pega en la terminal

Para el flujo OAuth necesitas registrar la app en:
  GitLab.com → Settings > Applications
  o en tu instancia self-hosted como admin.
"""

import os
import sys
import json
import time
import base64
import hashlib
import secrets
import subprocess
import webbrowser
import urllib.parse
import http.server
import threading
from pathlib import Path
from getpass import getpass

import requests
from gitlab import Gitlab
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()

# ── Constantes ─────────────────────────────────────────────────────────────
TOKEN_CACHE = Path.home() / ".config" / "glabmanager" / "token.json"
OAUTH_REDIRECT_PORT = 7777
OAUTH_REDIRECT_URI = f"http://localhost:{OAUTH_REDIRECT_PORT}"
OAUTH_SCOPES = "api read_user"


# ── Helpers de caché ────────────────────────────────────────────────────────
def _load_cached_token() -> dict | None:
    if TOKEN_CACHE.exists():
        try:
            data = json.loads(TOKEN_CACHE.read_text())
            # Si hay expiración, verificarla
            if "expires_at" in data and data["expires_at"] < time.time():
                console.print("[yellow]⚠ Token expirado, re-autenticando...[/]")
                TOKEN_CACHE.unlink()
                return None
            return data
        except (json.JSONDecodeError, KeyError):
            return None
    return None


def _save_token(data: dict):
    TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(json.dumps(data, indent=2))
    TOKEN_CACHE.chmod(0o600)  # Solo lectura para el usuario


def _clear_token():
    if TOKEN_CACHE.exists():
        TOKEN_CACHE.unlink()
        console.print("[yellow]Token eliminado del caché.[/]")


# ── Browser helper (compatible con WSL) ─────────────────────────────────────
def _open_browser(url: str):
    """Abre el navegador detectando si estamos en WSL."""
    try:
        with open("/proc/version") as f:
            if "microsoft" in f.read().lower():
                # En WSL, explorer.exe abre la URL en el navegador de Windows
                subprocess.Popen(["explorer.exe", url])
                return
    except FileNotFoundError:
        pass
    webbrowser.open(url)


# ── PKCE helpers ────────────────────────────────────────────────────────────
def _pkce_pair() -> tuple[str, str]:
    """Genera (code_verifier, code_challenge) para el flujo PKCE."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


# ── Servidor HTTP temporal para capturar el redirect ───────────────────────
class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handler minimalista: captura ?code= y cierra el servidor."""
    captured_code: str | None = None
    captured_error: str | None = None

    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in params:
            _CallbackHandler.captured_code = params["code"][0]
            body = b"<h2>Autenticado. Puedes cerrar esta ventana.</h2>"
        elif "error" in params:
            _CallbackHandler.captured_error = params.get("error_description", ["Error desconocido"])[0]
            body = b"<h2>Error de autenticacion. Vuelve a la terminal.</h2>"
        else:
            body = b"<h2>Esperando...</h2>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silenciar logs del servidor
        pass


def _wait_for_callback(timeout: int = 120) -> str:
    """Levanta el servidor HTTP y espera el código de autorización."""
    server = http.server.HTTPServer(("localhost", OAUTH_REDIRECT_PORT), _CallbackHandler)
    server.timeout = timeout

    deadline = time.time() + timeout
    while time.time() < deadline:
        server.handle_request()
        if _CallbackHandler.captured_code or _CallbackHandler.captured_error:
            break

    server.server_close()

    if _CallbackHandler.captured_error:
        raise RuntimeError(f"GitLab rechazó la autorización: {_CallbackHandler.captured_error}")
    if not _CallbackHandler.captured_code:
        raise TimeoutError("No se recibió respuesta del navegador en el tiempo límite.")

    return _CallbackHandler.captured_code


# ── Flujo OAuth 2.0 + PKCE ──────────────────────────────────────────────────
def _oauth_flow(gitlab_url: str, client_id: str) -> dict:
    """
    Ejecuta el flujo completo OAuth 2.0 con PKCE.
    Retorna un dict con access_token (y opcionalmente expires_at).
    """
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(16)

    params = {
        "client_id": client_id,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": OAUTH_SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{gitlab_url}/oauth/authorize?{urllib.parse.urlencode(params)}"

    console.print(Panel(
        f"[bold cyan]Abriendo navegador para autenticarte en GitLab...[/]\n\n"
        f"Si no se abre automáticamente, copia esta URL:\n[dim]{auth_url}[/]",
        title="OAuth 2.0 Login", border_style="cyan"
    ))
    _open_browser(auth_url)

    console.print("[dim]Esperando respuesta del navegador (máx. 2 min)...[/]")
    # Resetear estado del handler antes de escuchar
    _CallbackHandler.captured_code = None
    _CallbackHandler.captured_error = None
    code = _wait_for_callback()

    # Intercambiar code por access_token
    resp = requests.post(
        f"{gitlab_url}/oauth/token",
        data={
            "client_id": client_id,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": OAUTH_REDIRECT_URI,
            "code_verifier": verifier,
        },
        timeout=15,
    )
    resp.raise_for_status()
    token_data = resp.json()

    result = {
        "type": "oauth",
        "access_token": token_data["access_token"],
        "gitlab_url": gitlab_url,
    }
    if "expires_in" in token_data:
        result["expires_at"] = time.time() + token_data["expires_in"]

    return result


# ── Flujo PAT interactivo ────────────────────────────────────────────────────
def _pat_flow(gitlab_url: str) -> dict:
    """
    Pide al usuario que pegue su Personal Access Token.
    Lo valida antes de guardarlo.
    """
    console.print(Panel(
        "Genera un token en:\n"
        f"[bold]{gitlab_url}/-/user_settings/personal_access_tokens[/]\n\n"
        "Scopes necesarios: [cyan]api[/] y [cyan]read_user[/]",
        title="Personal Access Token", border_style="yellow"
    ))
    token = getpass("Pega tu Personal Access Token (no se mostrará): ").strip()
    if not token:
        raise ValueError("Token vacío.")
    return {"type": "pat", "access_token": token, "gitlab_url": gitlab_url}


# ── Punto de entrada principal ───────────────────────────────────────────────
class GitLabClient:
    def connect(self) -> Gitlab:
        gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/")

        # 1. Caché local
        cached = _load_cached_token()
        if cached:
            gl = self._build_client(cached)
            if gl:
                return gl
            # Token inválido → limpiar y continuar
            _clear_token()

        # 2. Variable de entorno
        env_token = os.getenv("GITLAB_PRIVATE_TOKEN")
        if env_token:
            try:
                gl = Gitlab(gitlab_url, private_token=env_token, timeout=15)
                gl.auth()
                console.print(f"[bold green]✓ Conectado (env) como:[/] {gl.user.username}")
                return gl
            except Exception:
                console.print("[yellow]⚠ GITLAB_PRIVATE_TOKEN en .env no es válido.[/]")

        # 3. Flujo interactivo
        console.print(Panel(
            "No se encontró una sesión activa.\n\n"
            "[bold cyan]1.[/] 🌐 OAuth — abre el navegador (recomendado)\n"
            "[bold cyan]2.[/] 🔑 Personal Access Token — pega el token aquí\n"
            "[bold cyan]0.[/] Salir",
            title="Autenticación GitLab", border_style="bold green"
        ))
        choice = Prompt.ask("Método", choices=["1", "2", "0"], default="1")

        if choice == "0":
            sys.exit(0)

        try:
            if choice == "1":
                client_id = os.getenv("GITLAB_OAUTH_CLIENT_ID") or Prompt.ask(
                    "[yellow]Client ID[/] de la app OAuth\n"
                    "  [dim](NO es un token glpat-... — es un número)[/]\n"
                    "  Regístrala en: [cyan]gitlab.com > Settings > Applications[/]\n"
                    "  Redirect URI: [cyan]http://localhost:7777[/]  |  Scopes: [cyan]api, read_user[/]\n"
                    "Client ID"
                )
                token_data = _oauth_flow(gitlab_url, client_id)
            else:
                token_data = _pat_flow(gitlab_url)

            gl = self._build_client(token_data)
            if not gl:
                console.print("[bold red]❌ Las credenciales no son válidas.[/]")
                sys.exit(1)

            if Confirm.ask("¿Guardar sesión para no volver a autenticarte?", default=True):
                _save_token(token_data)
                console.print(f"[dim]Token guardado en {TOKEN_CACHE}[/]")

            return gl

        except (RuntimeError, TimeoutError, ValueError, requests.HTTPError) as e:
            console.print(f"[bold red]❌ Error de autenticación:[/] {e}")
            sys.exit(1)

    @staticmethod
    def _build_client(token_data: dict) -> Gitlab | None:
        """Construye y valida un cliente Gitlab a partir del dict de token."""
        url = token_data.get("gitlab_url", "https://gitlab.com")
        token = token_data.get("access_token")
        token_type = token_data.get("type", "pat")

        try:
            if token_type == "oauth":
                gl = Gitlab(url, oauth_token=token, timeout=15)
            else:
                gl = Gitlab(url, private_token=token, timeout=15)
            gl.auth()
            console.print(f"[bold green]✓ Conectado como:[/] {gl.user.username}")
            return gl
        except Exception:
            return None


def logout():
    """Elimina el token guardado. Útil para cambiar de cuenta."""
    _clear_token()
