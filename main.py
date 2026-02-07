import os
import sys
from gitlab import Gitlab, exceptions
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.prompt import Prompt, IntPrompt

console = Console()

class GitLabArchitect:
    def __init__(self):
        self.url = os.getenv("GITLAB_URL", "https://gitlab.com")
        self.token = os.getenv("GITLAB_PRIVATE_TOKEN")

        if not self.token:
            console.print("[bold red]❌ Error:[/] Define GITLAB_PRIVATE_TOKEN en tu entorno.", style="red")
            sys.exit(1)

        try:
            self.gl = Gitlab(self.url, private_token=self.token)
            self.gl.auth()
            console.print(f"[bold green]✓ Sesión iniciada:[/] {self.gl.user.username}", style="green")
        except Exception as e:
            console.print(f"[bold red]❌ Error de conexión:[/] {e}", style="red")
            sys.exit(1)

    # --- 1. Visualización de Jerarquía (Algoritmo de Árbol) ---
    def show_tree(self, group_id, tree_node=None):
        try:
            group = self.gl.groups.get(group_id)
            if tree_node is None:
                tree_node = Tree(f":vibration_mode: [bold magenta]Grupo: {group.name} (ID: {group.id})[/]")

            # Listar Proyectos del nivel actual
            projects = group.projects.list(all=True)
            for p in projects:
                tree_node.add(f":package: [cyan]{p.name}[/] (ID: {p.id})")

            # Listar Subgrupos (Recursión $O(N)$ donde N es el número de subgrupos)
            subgroups = group.subgroups.list(all=True)
            for sg in subgroups:
                sub_node = tree_node.add(f":file_folder: [bold yellow]{sg.name}[/] (ID: {sg.id})")
                self.show_tree(sg.id, sub_node)

            return tree_node
        except exceptions.GitlabGetError:
            console.print(f"[red]Error: No se encontró el grupo {group_id}[/]")

    # --- 2. Gestión de Subgrupos ---
    def manage_subgroups(self):
        console.print("\n[bold]🛠 Gestión de Subgrupos[/]")
        action = Prompt.ask("Acción", choices=["crear", "eliminar", "mover", "atrás"], default="atrás")

        if action == "crear":
            parent_id = Prompt.ask("ID del Grupo Padre")
            name = Prompt.ask("Nombre del nuevo Subgrupo")
            path = name.lower().replace(" ", "-")
            try:
                self.gl.groups.create({'name': name, 'path': path, 'parent_id': parent_id})
                console.print(f"[green]✓ Subgrupo '{name}' creado con éxito.[/]")
            except Exception as e:
                console.print(f"[red]Error al crear:[/] {e}")

        elif action == "eliminar":
            sg_id = Prompt.ask("ID del Subgrupo a eliminar")
            confirm = Prompt.ask(f"¿Estás seguro de eliminar el ID {sg_id}? (s/n)", choices=["s", "n"])
            if confirm == "s":
                try:
                    self.gl.groups.delete(sg_id)
                    console.print("[yellow]⚠ Subgrupo eliminado.[/]")
                except Exception as e:
                    console.print(f"[red]Error:[/] {e}")

        elif action == "mover":
            group_id = Prompt.ask("ID del Grupo/Subgrupo a mover")
            new_parent_id = Prompt.ask("ID del nuevo Grupo Padre")
            try:
                # En GitLab API, mover un grupo es un 'transfer'
                group = self.gl.groups.get(group_id)
                group.transfer(new_parent_id)
                console.print(f"[green]✓ Grupo {group_id} transferido al padre {new_parent_id}.[/]")
            except Exception as e:
                console.print(f"[red]Error al mover:[/] {e}")

    # --- 3. Búsqueda con Manejo de Errores (Fix 500) ---
    def search_projects(self):
        query = Prompt.ask("Buscar proyecto por nombre")
        try:
            # Añadimos simple=True y limitamos para evitar que GitLab sature y devuelva 500
            projects = self.gl.projects.list(search=query, get_all=False, per_page=10)
            if not projects:
                console.print("[yellow]No se encontraron resultados.[/]")
                return

            table = Table(title=f"Resultados para: {query}")
            table.add_column("ID", justify="right", style="dim")
            table.add_column("Nombre", style="bold")
            table.add_column("Path", style="blue")

            for p in projects:
                table.add_row(str(p.id), p.name, p.path_with_namespace)
            console.print(table)
        except Exception as e:
            console.print(f"[bold red]❌ GitLab devolvió un error (posible 500):[/] {e}")

    # --- 4. Raw API (Fix Serialization) ---
    def raw_api(self):
        endpoint = Prompt.ask("Endpoint (ej: /groups/123/subgroups)")
        # Limpieza básica del endpoint
        if not endpoint.startswith('/'): endpoint = '/' + endpoint

        method = Prompt.ask("Método", choices=["GET", "POST", "DELETE"], default="GET")
        try:
            # .http_request devuelve un objeto Response de la librería 'requests'
            response = self.gl.http_request(method, endpoint)
            # Intentamos parsear a JSON si la respuesta tiene contenido
            try:
                data = response.json()
                console.print_json(data=data)
            except:
                console.print(f"[yellow]Respuesta sin JSON (Status: {response.status_code})[/]")
        except Exception as e:
            console.print(f"[red]Error en API Call:[/] {e}")

def main():
    arch = GitLabArchitect()

    while True:
        console.print(Panel.fit(
            "[bold cyan]1.[/] Ver Árbol de Jerarquía (Tree)\n"
            "[bold cyan]2.[/] Gestionar Subgrupos (Crear/Mover/Eliminar)\n"
            "[bold cyan]3.[/] Buscar Proyectos (Optimizado)\n"
            "[bold cyan]4.[/] Raw API Request\n"
            "[bold cyan]0.[/] Salir",
            title="GitLab Architect CLI v2.0", border_style="bold blue"
        ))

        choice = IntPrompt.ask("Selecciona una opción", default=0)

        if choice == 1:
            g_id = Prompt.ask("ID del Grupo Raíz")
            with console.status("[bold green]Generando árbol..."):
                tree = arch.show_tree(g_id)
                if tree: console.print(tree)
        elif choice == 2:
            arch.manage_subgroups()
        elif choice == 3:
            arch.search_projects()
        elif choice == 4:
            arch.raw_api()
        elif choice == 0:
            break

if __name__ == "__main__":
    main()
