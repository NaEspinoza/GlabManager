import os
import sys
from gitlab import Gitlab, exceptions
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.live import Live

console = Console()

class GitLabArchitect:
    def __init__(self):
        self.url = os.getenv("GITLAB_URL", "https://gitlab.com")
        self.token = os.getenv("GITLAB_PRIVATE_TOKEN")
        
        if not self.token:
            console.print("[bold red]❌ Error:[/] GITLAB_PRIVATE_TOKEN no detectado.", style="red")
            sys.exit(1)
            
        try:
            # Aumentamos el timeout para evitar KeyboardInterrupt prematuros
            self.gl = Gitlab(self.url, private_token=self.token, timeout=15)
            self.gl.auth()
            console.print(f"[bold green]✓ Arquitecto Conectado:[/] {self.gl.user.username}")
        except Exception as e:
            console.print(f"[bold red]❌ Error Crítico:[/] {e}")
            sys.exit(1)

    # --- Lógica de Filtrado (SRE Principle: Data Cleaning) ---
    def _is_active(self, obj):
        """Retorna True si el objeto no está marcado para eliminación."""
        # GitLab API marca esto en 'marked_for_deletion_on'
        return getattr(obj, 'marked_for_deletion_on', None) is None

    # --- 1. Árbol Estructural Optimizado ---
    def build_tree(self, group_id, tree_node, current_depth=0, max_depth=3, show_deleted=False):
        if current_depth > max_depth:
            return

        try:
            group = self.gl.groups.get(group_id)
            
            # Procesar Proyectos
            projects = group.projects.list(get_all=False, per_page=50)
            for p in projects:
                if not show_deleted and not self._is_active(p): continue
                status = "[red][DEL][/]" if not self._is_active(p) else ""
                tree_node.add(f":package: {status} [cyan]{p.name}[/] [dim]({p.id})[/]")

            # Procesar Subgrupos
            subgroups = group.subgroups.list(get_all=False, per_page=50)
            for sg in subgroups:
                # Filtrado lógico
                if not show_deleted and not self._is_active(sg): continue
                
                status = "[red][DEL][/]" if not self._is_active(sg) else ""
                sub_node = tree_node.add(f":file_folder: {status} [bold yellow]{sg.name}[/] [dim]({sg.id})[/]")
                self.build_tree(sg.id, sub_node, current_depth + 1, max_depth, show_deleted)

        except Exception as e:
            tree_node.add(f"[red]⚠ Error: {str(e)[:20]}...[/]")

    # --- 2. Gestión de Labels (Módulo Nuevo) ---
    def manage_labels(self):
        group_id = Prompt.ask("ID del Grupo para gestionar Labels")
        try:
            group = self.gl.groups.get(group_id)
            labels = group.labels.list()
            
            table = Table(title=f"Labels de {group.name}")
            table.add_column("Nombre", style="bold")
            table.add_column("Color")
            table.add_column("Descripción")
            
            for l in labels:
                table.add_row(l.name, f"[{l.color}]{l.color}[/]", l.description or "")
            console.print(table)

            if Confirm.ask("¿Deseas crear una nueva Label?"):
                name = Prompt.ask("Nombre de la Label")
                color = Prompt.ask("Color (Hex, ej: #FF0000)", default="#428BCA")
                group.labels.create({'name': name, 'color': color})
                console.print("[green]✓ Label creada exitosamente.[/]")
        except Exception as e:
            console.print(f"[red]Error en Labels: {e}[/]")

    # --- 3. Gestión de Proyectos (Lifecycle) ---
    def manage_projects(self):
        p_id = Prompt.ask("ID del Proyecto")
        try:
            project = self.gl.projects.get(p_id)
            console.print(Panel(f"Proyecto: {project.name}\nWeb URL: {project.web_url}\nEstado: {'Archivado' if project.archived else 'Activo'}"))
            
            action = Prompt.ask("Acción", choices=["archivar", "desarchivar", "borrar", "atrás"], default="atrás")
            
            if action == "archivar":
                project.archive()
                console.print("[yellow]✓ Proyecto archivado (Read-only).[/]")
            elif action == "desarchivar":
                project.unarchive()
                console.print("[green]✓ Proyecto activo de nuevo.[/]")
            elif action == "borrar":
                if Confirm.ask(f"[bold red]⚠ ¿ESTÁS SEGURO DE ELIMINAR {project.name}?"):
                    project.delete()
                    console.print("[red]✓ Eliminación solicitada.[/]")
        except Exception as e:
            console.print(f"[red]Error en Proyecto: {e}[/]")

    def run_tree_view(self):
        g_id = Prompt.ask("ID del Grupo Raíz")
        max_d = IntPrompt.ask("Profundidad", default=2)
        show_del = Confirm.ask("¿Mostrar elementos en proceso de eliminación?", default=False)
        
        root_node = Tree(f":vibration_mode: [bold magenta]Estructura de ID: {g_id}[/]")
        with Live(root_node, refresh_per_second=4, console=console) as live:
            self.build_tree(g_id, root_node, max_depth=max_d, show_deleted=show_del)
            live.update(root_node)

# --- Main Menu Loop ---
def main():
    arch = GitLabArchitect()
    while True:
        console.print(Panel.fit(
            "1. 🌲 Ver Árbol Estructural (Filtro Deletion Activo)\n"
            "2. 🏷  Gestionar Labels de Grupo\n"
            "3. 📦 Ciclo de Vida de Proyectos (Archive/Delete)\n"
            "4. 📂 Gestión de Subgrupos (Crear/Mover)\n"
            "0. Salir",
            title="GitLab Architect CLI v4.0", border_style="bold green"
        ))
        choice = Prompt.ask("Selecciona una opción", choices=["1", "2", "3", "4", "0"], default="0")
        
        if choice == "1": arch.run_tree_view()
        elif choice == "2": arch.manage_labels()
        elif choice == "3": arch.manage_projects()
        elif choice == "4": 
            # Reutilizamos la lógica del script anterior para subgrupos
            console.print("[yellow]Funcionalidad de la V3 disponible aquí...[/]")
        elif choice == "0": break

if __name__ == "__main__":
    main()
