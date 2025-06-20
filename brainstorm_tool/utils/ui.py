# ui.py
# This file contains functions for user interface and console interaction.

import sys
import asyncio
import itertools
from typing import List, Dict, Any, Optional

def prompt_user_input(prompt_text: str) -> str:
    """Shows the cursor and prompts the user for input."""
    sys.stdout.write('\033[?25h') # Make cursor visible
    sys.stdout.flush()
    return input(prompt_text).strip()


async def spinner_task(shared_state: Dict[str, Any]):
    """Displays an animated spinner with the current stage name."""
    sys.stdout.write('\033[?25l') # Hide cursor
    sys.stdout.flush()
    status = ""
    for char in itertools.cycle('|/-\\'):
        if shared_state.get('stop_spinner'):
            break
        stage_name = shared_state.get('stage_name', 'Initializing...')
        stage_index = shared_state.get('stage_index', 0)
        total_stages = shared_state.get('total_stages', 0)
        
        status = f" [{stage_index}/{total_stages}] {stage_name} {char}"
        
        sys.stdout.write(status)
        sys.stdout.flush()
        sys.stdout.write('\b' * len(status))
        try:
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
            
    # Clean up the line and show cursor
    sys.stdout.write('\r' + ' ' * (len(status) + 5) + '\r')
    sys.stdout.write('\033[?25h') # Show cursor
    sys.stdout.flush()


def user_filter_ideas(
    all_ideas: List[Dict[str, Any]], 
    brainstorm_type: str
) -> List[Dict[str, Any]]:
    """
    Presents the structured ideas to the user for filtering and returns the selection.
    """
    print("\n--- User Filtering Step ---")
    print("Review the generated ideas. The Analyst will only evaluate the ideas you keep.")

    if not all_ideas:
        print("No ideas were generated.")
        return []

    for i, idea in enumerate(all_ideas):
        print(f"\n--- Idea [{i+1}] (from {idea.get('role', 'Unknown')}) ---")
        if brainstorm_type == 'project':
            print(f"  Idea: {idea.get('idea', 'N/A')}")
            print(f"  Target Audience: {idea.get('target_audience', 'N/A')}")
            print(f"  Problem Solved: {idea.get('problem_solved', 'N/A')}")
            print(f"  Rationale: {idea.get('rationale', 'N/A')}")
        else: # research_paper
            print(f"  Research Question: {idea.get('research_question', 'N/A')}")
            print(f"  Methodology: {idea.get('potential_methodology', 'N/A')}")
            print(f"  Contribution: {idea.get('potential_contribution', 'N/A')}")
            print(f"  Rationale: {idea.get('rationale', 'N/A')}")

    while True:
        try:
            response = prompt_user_input("\nEnter the numbers of ideas to REMOVE, separated by commas (e.g., 2, 5, 8), or press Enter to keep all: ")
            if not response:
                return all_ideas 

            indices_to_remove = {int(num.strip()) - 1 for num in response.split(',')}
            kept_ideas = [idea for i, idea in enumerate(all_ideas) if i not in indices_to_remove]
            
            print(f"\n✅ Filtering complete. {len(kept_ideas)} ideas will be sent for evaluation.")
            return kept_ideas
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")

def user_select_final_idea(top_ideas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Presents the top ideas to the user and asks them to select one for planning.
    """
    print("\n--- User Selection Step ---")
    print("The Analyst has provided the top ideas. Please select one to create a final document.")
    
    if not top_ideas:
        print("⚠️ No top ideas were provided by the analyst.")
        return None

    for i, idea in enumerate(top_ideas):
        print(f"\n  [{i+1}] Title: {idea['title']}")
        print(f"      Description: {idea['description']}")

    while True:
        try:
            choice_str = prompt_user_input(f"\nChoose an idea to proceed with (1-{len(top_ideas)}): ")
            if not choice_str: continue
            choice = int(choice_str)
            if 1 <= choice <= len(top_ideas):
                return top_ideas[choice - 1]
            else:
                print("Invalid choice. Please select a number from the list.")
        except (ValueError, IndexError):
            print("Invalid input. Please enter a valid number.")

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
