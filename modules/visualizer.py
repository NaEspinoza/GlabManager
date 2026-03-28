from gitlab import Gitlab
from rich.tree import Tree
from rich.live import Live
from rich.prompt import IntPrompt, Confirm
from rich.console import Console

console = Console()


def _is_active(obj) -> bool:
    return getattr(obj, 'marked_for_deletion_on', None) is None


class TreeVisualizer:
    def __init__(self, gl: Gitlab):
        self.gl = gl

    def run(self):
        from rich.prompt import Prompt
        g_id = Prompt.ask("ID del Grupo Raíz")
        max_d = IntPrompt.ask("Profundidad máxima", default=2)
        show_del = Confirm.ask("¿Mostrar elementos en proceso de eliminación?", default=False)

        root_node = Tree(f":vibration_mode: [bold magenta]Estructura de ID: {g_id}[/]")
        with Live(root_node, refresh_per_second=4, console=console) as live:
            self._build(g_id, root_node, max_depth=max_d, show_deleted=show_del)
            live.update(root_node)

    def _build(self, group_id, tree_node, current_depth=0, max_depth=3, show_deleted=False):
        if current_depth > max_depth:
            return

        try:
            group = self.gl.groups.get(group_id)

            for p in group.projects.list(get_all=False, per_page=50):
                if not show_deleted and not _is_active(p):
                    continue
                status = "[red][DEL][/] " if not _is_active(p) else ""
                tree_node.add(f":package: {status}[cyan]{p.name}[/] [dim]({p.id})[/]")

            for sg in group.subgroups.list(get_all=False, per_page=50):
                if not show_deleted and not _is_active(sg):
                    continue
                status = "[red][DEL][/] " if not _is_active(sg) else ""
                sub_node = tree_node.add(f":file_folder: {status}[bold yellow]{sg.name}[/] [dim]({sg.id})[/]")
                self._build(sg.id, sub_node, current_depth + 1, max_depth, show_deleted)

        except Exception as e:
            tree_node.add(f"[red]⚠ Error: {str(e)[:40]}[/]")
