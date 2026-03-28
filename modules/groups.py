from gitlab import Gitlab, GitlabError
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()


class GroupManager:
    def __init__(self, gl: Gitlab):
        self.gl = gl

    def menu_interactivo(self):
        while True:
            console.print(Panel.fit(
                "1. 🏷  Gestionar Labels del Grupo\n"
                "2. ➕ Crear Subgrupo\n"
                "3. 🗑  Eliminar Grupo\n"
                "4. 🔀 Transferir (Mover) Grupo\n"
                "0. 🔙 Volver",
                title="Gestión de Grupos", border_style="bold yellow"
            ))
            choice = Prompt.ask("Selecciona", choices=["1", "2", "3", "4", "0"], default="0")

            if choice == "1":
                self.manage_labels()
            elif choice == "2":
                self._create_subgroup()
            elif choice == "3":
                self._delete_group()
            elif choice == "4":
                self._transfer_group()
            elif choice == "0":
                break

    def manage_labels(self):
        group_id = Prompt.ask("ID del Grupo para gestionar Labels")
        try:
            group = self.gl.groups.get(group_id)
            labels = group.labels.list()

            table = Table(title=f"Labels de {group.name}")
            table.add_column("ID", style="dim", width=8)
            table.add_column("Nombre", style="bold")
            table.add_column("Color")
            table.add_column("Descripción")

            for label in labels:
                table.add_row(str(label.id), label.name, label.color, label.description or "")
            console.print(table)

            if Confirm.ask("¿Deseas crear una nueva Label?"):
                name = Prompt.ask("Nombre de la Label")
                color = Prompt.ask("Color (Hex)", default="#428BCA")
                group.labels.create({'name': name, 'color': color})
                console.print("[green]✓ Label creada exitosamente.[/]")

        except GitlabError as e:
            console.print(f"[red]Error en Labels: {e}[/]")

    def _create_subgroup(self):
        parent_id = Prompt.ask("ID del Grupo Padre")
        name = Prompt.ask("Nombre del Subgrupo")
        path = Prompt.ask("Path (slug)", default=name.lower().replace(" ", "-"))
        try:
            self.gl.groups.create({
                'name': name,
                'path': path,
                'parent_id': parent_id
            })
            console.print(f"[green]✓ Subgrupo '{name}' creado.[/]")
        except GitlabError as e:
            console.print(f"[red]Error al crear subgrupo: {e}[/]")

    def _delete_group(self):
        g_id = Prompt.ask("ID del Grupo a eliminar")
        try:
            group = self.gl.groups.get(g_id)
            console.print(f"[bold red]⚠ Estás a punto de eliminar: {group.full_path}[/]")
            confirmation = Prompt.ask(f"Escribe '[bold]{group.path}[/]' para confirmar")
            if confirmation == group.path:
                group.delete()
                console.print("[yellow]✓ Grupo eliminado.[/]")
            else:
                console.print("[green]Operación cancelada.[/]")
        except GitlabError as e:
            console.print(f"[red]Error al eliminar: {e}[/]")

    def _transfer_group(self):
        g_id = Prompt.ask("ID del Grupo a mover")
        target_id = Prompt.ask("ID del Nuevo Grupo Padre")
        try:
            self.gl.http_post(f'/groups/{target_id}/transfer', query_data={'group_id': g_id})
            console.print("[green]✓ Transferencia completada.[/]")
        except GitlabError as e:
            console.print(f"[red]Error en transferencia: {e}[/]")
