from core.connection import GitLabClient, logout
from modules.visualizer import TreeVisualizer
from modules.groups import GroupManager
from modules.projects import interactive_project_menu
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


def main():
    gl = GitLabClient().connect()

    visualizer = TreeVisualizer(gl)
    group_mgr = GroupManager(gl)

    while True:
        console.print(Panel.fit(
            "[bold cyan]1.[/] 🌲 Visualizar Estructura (Tree)\n"
            "[bold cyan]2.[/] 📦 Gestión de Proyectos (CRUD / Archive / Topics)\n"
            "[bold cyan]3.[/] 📂 Gestión de Grupos y Labels\n"
            "[bold cyan]9.[/] 🚪 Cerrar sesión (logout)\n"
            "[bold cyan]0.[/] Salir",
            title="GitLab Architect CLI", border_style="bold green"
        ))
        choice = Prompt.ask("Selecciona", choices=["1", "2", "3", "9", "0"], default="0")

        if choice == "1":
            visualizer.run()
        elif choice == "2":
            interactive_project_menu(gl)
        elif choice == "3":
            group_mgr.menu_interactivo()
        elif choice == "9":
            logout()
        elif choice == "0":
            break


if __name__ == "__main__":
    main()
