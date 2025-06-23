# This file contains nodes that require user interaction (interrupts).

from typing import Dict, Any
from langgraph.types import interrupt

from ..state import GraphState


async def user_filter_ideas_node(state: GraphState) -> Dict[str, Any]:
    """
    A node that interrupts the graph to ask the user to filter ideas.
    """
    print("\n--- ⏸️ User Input Required: Idea Filtering ---")
    print(
        "The AI personas have discussed and shortlisted their ideas. Review them and decide which to keep for the final analysis."
    )
    brainstorm_type = state["brainstorm_type"]
    all_ideas = state.get("all_generated_ideas")
    if not all_ideas:
        print("\nNo ideas were generated to be filtered. Continuing.")
        return {"filtered_ideas": []}

    for i, idea in enumerate(all_ideas):
        print(f"\n--- Idea [{i+1}] (from Personas' Discussion) ---")
        if brainstorm_type == "project":
            print(f"  Idea: {idea.get('idea', 'N/A')}")
            print(f"  Target Audience: {idea.get('target_audience', 'N/A')}")
            print(f"  Problem Solved: {idea.get('problem_solved', 'N/A')}")
            print(f"  Rationale: {idea.get('rationale', 'N/A')}")
        else:  # research_paper
            print(f"  Research Question: {idea.get('research_question', 'N/A')}")
            print(f"  Methodology: {idea.get('potential_methodology', 'N/A')}")
            print(f"  Contribution: {idea.get('potential_contribution', 'N/A')}")
            print(f"  Rationale: {idea.get('rationale', 'N/A')}")

    indices_to_remove_str = interrupt(
        {
            "message": "\nEnter the numbers of ideas to REMOVE, separated by commas (e.g., 2, 5), or press Enter to keep all: "
        }
    )

    if not indices_to_remove_str or not indices_to_remove_str.strip():
        print(f"\n✅ Keeping all {len(all_ideas)} ideas. Resuming workflow...")
        return {"filtered_ideas": all_ideas}

    try:
        indices_to_remove = {
            int(num.strip()) - 1 for num in indices_to_remove_str.split(",")
        }
        filtered_ideas = [
            idea for i, idea in enumerate(all_ideas) if i not in indices_to_remove
        ]
        print(
            f"\n✅ Removed {len(all_ideas) - len(filtered_ideas)} ideas. {len(filtered_ideas)} ideas remaining. Resuming workflow..."
        )
        return {"filtered_ideas": filtered_ideas}
    except ValueError:
        print("⚠️ Invalid input. Could not parse numbers. Keeping all ideas.")
        return {"filtered_ideas": all_ideas}


async def user_select_idea_node(state: GraphState) -> Dict[str, Any]:
    """
    A node that interrupts the graph to ask the user to select the final idea.
    """
    print("\n--- ⏸️ User Input Required: Final Selection ---")
    print(
        "The Analyst has provided the top ideas. Please select one to create a final document."
    )
    top_ideas = state.get("top_ideas")
    if not top_ideas:
        print("⚠️ No top ideas were provided by the analyst. Skipping.")
        return {"chosen_idea": None}

    for i, idea in enumerate(top_ideas):
        print(f"\n  [{i+1}] Title: {idea['title']}")
        print(f"      Description: {idea['description']}")

    choice_str = interrupt(
        {"message": f"\nChoose an idea to proceed with (1-{len(top_ideas)}): "}
    )

    try:
        choice = int(choice_str)
        if 1 <= choice <= len(top_ideas):
            chosen = top_ideas[choice - 1]
            print(
                f"✅ Great choice! Selecting '{chosen['title']}'. Generating the final document..."
            )
            return {"chosen_idea": chosen}
        else:
            print(
                f"⚠️ Invalid choice. Number out of range. Select the first idea by default."
            )
            return {"chosen_idea": top_ideas[0]}
    except (ValueError, IndexError, TypeError):
        print(
            "⚠️ Invalid input. Could not parse number. Selecting the first idea by default."
        )
        return {"chosen_idea": top_ideas[0]}


async def user_feedback_on_plan_node(state: GraphState) -> Dict[str, Any]:
    """Interrupts to ask the user for feedback on the generated plan."""
    print("\n--- ⏸️ User Input Required: Plan Review ---")
    print(
        "Please review the generated plan. Do you approve it, or would you like to select a different idea?"
    )

    feedback = interrupt(
        {
            "message": "Type 'Y' to finish, or 'R' to go back to the idea selection screen: "
        }
    )

    return {"user_plan_feedback": feedback.strip().lower()}
