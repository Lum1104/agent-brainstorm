# ui.py
# This file contains functions for user interface and console interaction.

import sys
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt


# Shared Rich console for consistent styling across the app
console = Console()


def prompt_user_input(prompt_text: str, default: Optional[str] = None) -> str:
    """Shows the cursor and prompts the user for input using Rich."""
    sys.stdout.write("\033[?25h")  # Make cursor visible
    sys.stdout.flush()
    if default is not None and default != "":
        return Prompt.ask(prompt_text, default=str(default)).strip()
    return Prompt.ask(prompt_text).strip()


def select_brainstorm_type() -> str:
    """Asks the user to select the type of brainstorming session with Rich UI."""
    console.print(Panel.fit("Select the type of brainstorming session", style="bold cyan"))
    console.print("  [1] Project Idea (for products, features, etc.)", style="white")
    console.print("  [2] Research Paper (for academic topics, studies, etc.)", style="white")

    while True:
        choice = prompt_user_input("Enter your choice (1 or 2): ")
        if choice == "1":
            return "project"
        elif choice == "2":
            return "research_paper"
        else:
            console.print("Invalid choice. Please enter 1 or 2.", style="yellow")
