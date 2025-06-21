# ui.py
# This file contains functions for user interface and console interaction.

import sys


def prompt_user_input(prompt_text: str) -> str:
    """Shows the cursor and prompts the user for input."""
    sys.stdout.write('\033[?25h') # Make cursor visible
    sys.stdout.flush()
    return input(prompt_text).strip()


def select_brainstorm_type() -> str:
    """Asks the user to select the type of brainstorming session."""
    print("\nSelect the type of brainstorming session:")
    print("  [1] Project Idea (for products, features, etc.)")
    print("  [2] Research Paper (for academic topics, studies, etc.)")
    
    while True:
        choice = prompt_user_input("Enter your choice (1 or 2): ")
        if choice == '1':
            return 'project'
        elif choice == '2':
            return 'research_paper'
        else:
            print("Invalid choice. Please enter 1 or 2.")