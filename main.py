import os
import sys
from gitlab import Gitlab, exceptions
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.prompt import Prompt, IntPrompt
from rich.live import Live

console = Console()

class GitLabArchitect:
    def __init__(self):
        self.url = os.getenv("GITLAB_URL", "https://gitlab.com")
        self.token = os.getenv("GITLAB_PRIVATE_TOKEN")
        
        if not self.token:
            console.print("[bold red]❌ Error:[/] Falta GITLAB_PRIVATE_TOKEN.", style="red")
            sys.exit(1)
            
        try:
            self.gl = Gitlab(self.url, private_token=self.token, timeout=10)
            self.gl.auth()
            console.print(f"[bold green]✓ Sesión:[/] {self.gl.user.username}")
        except Exception as e:
            console.print(f"[bold red]❌ Error de conexión:[/] {e}")
            sys.exit(1)

    def build_tree(self, group_id, tree_node, current_depth=0, max_depth=3):
        """
        Construye el árbol de forma recursiva con límites para evitar hangs.
        """
        if current_depth > max_depth:
            tree_node.add("[dim italic]... profundidad máxima alcanzada[/]")
            return

        try:
            # Obtenemos el objeto grupo
            group = self.gl.groups.get(group_id)
            
            # 1. Procesar Proyectos (limitamos a 20 para velocidad)
            projects = group.projects.list(get_all=False, per_page=20)
            for p in projects:
                tree_node.add(f":package: [cyan]{p.name}[/] [dim]({p.id})[/]")

            # 2. Procesar Subgrupos
            subgroups = group.subgroups.list(get_all=False, per_page=15)
            for sg in subgroups:
                sub_node = tree_node.add(f":file_folder: [bold yellow]{sg.name}[/] [dim]({sg.id})[/]")
                # Llamada recursiva
                self.build_tree(sg.id, sub_node, current_depth + 1, max_depth)

        except exceptions.GitlabGetError:
            tree_node.add("[red]❌ Error: No accesible[/]")
        except Exception as e:
            tree_node.add(f"[red]⚠ Error de API: {str(e)[:30]}...[/]")

    def run_tree_view(self):
        g_id = Prompt.ask("ID o Path del Grupo Raíz")
        max_d = IntPrompt.ask("Profundidad máxima del árbol", default=3)
        
        # Iniciamos el objeto Tree de Rich
        root_node = Tree(f":vibration_mode: [bold magenta]Explorando ID: {g_id}[/]")
        
        with Live(root_node, refresh_per_second=4, console=console) as live:
            self.build_tree(g_id, root_node, max_depth=max_d)
            live.update(root_node) # Actualización final

    def manage_subgroups(self):
        console.print(Panel("[bold]1. Crear | 2. Eliminar | 3. Transferir (Mover) | 0. Atrás[/]"))
        op = Prompt.ask("Selecciona", choices=["1", "2", "3", "0"], default="0")
        
        if op == "1":
            p_id = Prompt.ask("ID Padre")
            name = Prompt.ask("Nombre")
            self.gl.groups.create({'name': name, 'path': name.lower().replace(" ","-"), 'parent_id': p_id})
            console.print("[green]✓ Creado[/]")
        elif op == "2":
            s_id = Prompt.ask("ID a eliminar")
            if Prompt.ask(f"¿Borrar {s_id}?", choices=["s","n"]) == "s":
                self.gl.groups.delete(s_id)
                console.print("[yellow]⚠ Borrado[/]")
        elif op == "3":
            g_id = Prompt.ask("ID Grupo a mover")
            target_id = Prompt.ask("ID Nuevo Padre")
            try:
                # El transfer en grupos se hace vía ID del grupo destino
                group = self.gl.groups.get(g_id)
                self.gl.http_post(f'/groups/{target_id}/transfer', query_data={'group_id': g_id})
                console.print("[green]✓ Transferencia iniciada[/]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")

    def search_projects(self):
        query = Prompt.ask("Nombre del proyecto")
        try:
            # Usamos simple=True para que la respuesta sea mínima y rápida
            projects = self.gl.projects.list(search=query, per_page=10)
            table = Table(title=f"Resultados: {query}")
            table.add_column("ID")
            table.add_column("Nombre")
            for p in projects: table.add_row(str(p.id), p.path_with_namespace)
            console.print(table)
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")

def main():
    arch = GitLabArchitect()
    while True:
        console.print(Panel.fit(
            "1. Ver Árbol Estructural (Live Tree)\n"
            "2. Gestión de Subgrupos (CRUD/Move)\n"
            "3. Buscar Proyectos\n"
            "0. Salir", 
            title="GitLab Architect CLI v3.0"
        ))
        choice = Prompt.ask(">>", choices=["1", "2", "3", "0"], default="0")
        if choice == "1": arch.run_tree_view()
        elif choice == "2": arch.manage_subgroups()
        elif choice == "3": arch.search_projects()
        elif choice == "0": break

if __name__ == "__main__":
    main()
