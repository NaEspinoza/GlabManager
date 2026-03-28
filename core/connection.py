import os
import sys
from gitlab import Gitlab
from rich.console import Console

console = Console()


class GitLabClient:
    def connect(self) -> Gitlab:
        url = os.getenv("GITLAB_URL", "https://gitlab.com")
        token = os.getenv("GITLAB_PRIVATE_TOKEN")

        if not token:
            console.print("[bold red]❌ Error:[/] GITLAB_PRIVATE_TOKEN no detectado.")
            sys.exit(1)

        try:
            gl = Gitlab(url, private_token=token, timeout=15)
            gl.auth()
            console.print(f"[bold green]✓ Conectado como:[/] {gl.user.username}")
            return gl
        except Exception as e:
            console.print(f"[bold red]❌ Error Crítico:[/] {e}")
            sys.exit(1)
