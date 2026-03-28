from gitlab import Gitlab, GitlabError
from gitlab.v4.objects import Project
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from typing import List

console = Console()


class ProjectController:
    def __init__(self, gl: Gitlab):
        self.gl = gl

    def list_projects(self, group_id: int, recursive: bool = True) -> List[Project]:
        try:
            group = self.gl.groups.get(group_id)
            console.print(f"[dim]Fetcheando proyectos de: {group.name}...[/]")
            projects = group.projects.list(include_subgroups=recursive, all=True)
            active = [p for p in projects if not getattr(p, 'marked_for_deletion_on', None)]
            self._render_table(active, group.name)
            return active
        except GitlabError as e:
            console.print(f"[bold red]❌ Error al listar proyectos:[/] {e}")
            return []

    def create_project(self, group_id: int):
        console.print(Panel("🛠  [bold cyan]Crear Nuevo Proyecto[/]", style="cyan"))
        name = Prompt.ask("Nombre del Proyecto")
        path = Prompt.ask("Path (slug)", default=name.lower().replace(" ", "-"))
        desc = Prompt.ask("Descripción", default="")
        visibility = Prompt.ask("Visibilidad", choices=["private", "internal", "public"], default="private")

        try:
            project = self.gl.projects.create({
                'name': name,
                'path': path,
                'namespace_id': group_id,
                'description': desc,
                'visibility': visibility,
            })
            console.print(f"[bold green]✓ Proyecto creado:[/] {project.web_url}")

            if Confirm.ask("¿Inicializar con README?"):
                project.files.create({
                    'file_path': 'README.md',
                    'branch': 'main',
                    'content': f'# {name}\n\n{desc}',
                    'commit_message': 'Initial commit',
                })
                console.print("[green]✓ README.md creado.[/]")

        except GitlabError as e:
            console.print(f"[bold red]❌ Fallo en la creación:[/] {e}")

    def edit_project(self):
        p_id = Prompt.ask("ID del Proyecto a editar")
        try:
            project = self.gl.projects.get(p_id)
            console.print(f"[yellow]Editando: {project.name_with_namespace}[/]")
            field = Prompt.ask("Campo a editar", choices=["name", "description", "visibility", "default_branch"])
            new_value = Prompt.ask(f"Nuevo valor para '{field}'")
            setattr(project, field, new_value)
            project.save()
            console.print(f"[green]✓ '{field}' actualizado.[/]")
        except GitlabError as e:
            console.print(f"[red]Error al actualizar: {e}[/]")

    def delete_project(self):
        p_id = Prompt.ask("ID del Proyecto a eliminar")
        try:
            project = self.gl.projects.get(p_id)
            console.print(f"[bold red]⚠ ADVERTENCIA: {project.path_with_namespace}[/]")
            confirmation = Prompt.ask(f"Escribe '[bold]{project.path}[/]' para confirmar")
            if confirmation == project.path:
                project.delete()
                console.print(f"[yellow]✓ Proyecto {p_id} eliminado.[/]")
            else:
                console.print("[green]Operación cancelada.[/]")
        except GitlabError as e:
            console.print(f"[red]Error al eliminar: {e}[/]")

    def archive_project(self):
        p_id = Prompt.ask("ID del Proyecto")
        try:
            project = self.gl.projects.get(p_id)
            console.print(Panel(
                f"Proyecto: {project.name}\nURL: {project.web_url}\n"
                f"Estado: {'Archivado' if project.archived else 'Activo'}"
            ))
            action = Prompt.ask("Acción", choices=["archivar", "desarchivar", "atrás"], default="atrás")
            if action == "archivar":
                project.archive()
                console.print("[yellow]✓ Proyecto archivado (read-only).[/]")
            elif action == "desarchivar":
                project.unarchive()
                console.print("[green]✓ Proyecto activo de nuevo.[/]")
        except GitlabError as e:
            console.print(f"[red]Error: {e}[/]")

    def manage_topics(self):
        """Gestiona Topics (tag_list) del proyecto — metadata del repo."""
        p_id = Prompt.ask("ID del Proyecto")
        try:
            project = self.gl.projects.get(p_id)
            current = project.attributes.get('topics') or project.attributes.get('tag_list', [])
            console.print(f"Topics actuales: [cyan]{', '.join(current) or 'ninguno'}[/]")

            action = Prompt.ask("Acción", choices=["añadir", "limpiar", "salir"], default="salir")
            if action == "añadir":
                new_tags = Prompt.ask("Etiquetas (separadas por coma)").split(',')
                updated = list(set(current + [t.strip() for t in new_tags if t.strip()]))
                project.topics = updated
                project.save()
                console.print(f"[green]✓ Topics actualizados: {project.topics}[/]")
            elif action == "limpiar":
                if Confirm.ask("¿Borrar todos los topics?"):
                    project.topics = []
                    project.save()
                    console.print("[yellow]Topics eliminados.[/]")
        except GitlabError as e:
            console.print(f"[red]Error gestionando topics: {e}[/]")

    def _render_table(self, projects: List[Project], group_name: str):
        if not projects:
            console.print("[yellow]No se encontraron proyectos activos.[/]")
            return
        table = Table(title=f"Proyectos en {group_name}")
        table.add_column("ID", style="dim", width=10)
        table.add_column("Nombre", style="bold white")
        table.add_column("Visibilidad", style="cyan")
        table.add_column("Última actividad", style="magenta")
        table.add_column("URL", style="blue")
        for p in projects:
            table.add_row(
                str(p.id), p.name, p.visibility,
                (p.last_activity_at or "")[:10],
                p.web_url,
            )
        console.print(table)


def interactive_project_menu(gl: Gitlab):
    controller = ProjectController(gl)

    while True:
        console.print(Panel.fit(
            "1. 📋 Listar Proyectos de un Grupo\n"
            "2. ➕ Crear Proyecto\n"
            "3. ✏️  Editar Metadatos\n"
            "4. 📦 Archivar / Desarchivar\n"
            "5. 🏷  Gestionar Topics\n"
            "6. 🗑  Eliminar Proyecto\n"
            "0. 🔙 Volver",
            title="Project Lifecycle Manager", border_style="bold cyan"
        ))
        choice = Prompt.ask("Selecciona", choices=["1", "2", "3", "4", "5", "6", "0"], default="0")

        if choice == "1":
            g_id = Prompt.ask("ID del Grupo Padre")
            controller.list_projects(int(g_id))
        elif choice == "2":
            g_id = Prompt.ask("ID del Grupo donde crear")
            controller.create_project(int(g_id))
        elif choice == "3":
            controller.edit_project()
        elif choice == "4":
            controller.archive_project()
        elif choice == "5":
            controller.manage_topics()
        elif choice == "6":
            controller.delete_project()
        elif choice == "0":
            break
