# main.py
# This is the main entry point for the application.

import os
import re
import asyncio
from typing import List, Dict, Any
from collections import defaultdict
from workflow import BrainstormingWorkflow

def user_filter_ideas(raw_ideas_by_persona: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Parses all raw ideas, presents them to the user for filtering, and
    returns the list of ideas the user wants to keep.
    """
    print("\n--- User Filtering Step ---")
    print("Review the generated ideas. The Chief Analyst will only evaluate the ideas you keep.")

    all_ideas = []
    # Use regex to split each persona's output into individual ideas
    idea_pattern = re.compile(r'^\s*[\*\-]\s*(.*)', re.MULTILINE)

    for persona_result in raw_ideas_by_persona:
        role = persona_result['role']
        ideas_text = persona_result['ideas']
        found_ideas = idea_pattern.findall(ideas_text)
        for idea_content in found_ideas:
            all_ideas.append({'content': idea_content.strip(), 'role': role})

    if not all_ideas:
        print("No parsable ideas were found.")
        return []

    for i, idea in enumerate(all_ideas):
        print(f"  [{i+1}] ({idea['role']}): {idea['content']}")

    while True:
        try:
            response = input("\nEnter the numbers of ideas to REMOVE, separated by commas (e.g., 2, 5, 8), or press Enter to keep all: ").strip()
            if not response:
                break # User wants to keep all ideas

            indices_to_remove = {int(num.strip()) - 1 for num in response.split(',')}
            
            # Filter the list in reverse order of indices to avoid shifting issues
            for index in sorted(list(indices_to_remove), reverse=True):
                if 0 <= index < len(all_ideas):
                    del all_ideas[index]
                else:
                    print(f"Warning: Index {index+1} is out of bounds and was ignored.")
            break
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")

    print(f"\n✅ Filtering complete. {len(all_ideas)} ideas will be sent for evaluation.")

    # Reconstruct the data structure required by the evaluation agent
    ideas_by_role = defaultdict(list)
    for idea in all_ideas:
        ideas_by_role[idea['role']].append(f"- {idea['content']}")
    
    final_ideas_to_evaluate = [
        {'role': role, 'ideas': '\n'.join(idea_list)} 
        for role, idea_list in ideas_by_role.items()
    ]
    
    return final_ideas_to_evaluate


def user_select_final_idea(top_ideas: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Presents the top ideas to the user and asks them to select one for planning.
    """
    print("\n--- User Selection Step ---")
    print("The Chief Analyst has provided the top ideas. Please select one to create a final document.")
    
    for i, idea in enumerate(top_ideas):
        print(f"  [{i+1}] {idea['title']}: {idea['description']}")

    while True:
        try:
            choice = int(input(f"\nChoose an idea to proceed with (1-{len(top_ideas)}): ").strip())
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
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == '1':
            return 'project'
        elif choice == '2':
            return 'research_paper'
        else:
            print("Invalid choice. Please enter 1 or 2.")

async def main():
    """Main function to run the brainstorming workflow."""
    print("🚀 Welcome to the AI Brainstorming Agent!")
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            # Fallback for Google Colab environments
            from google.colab import userdata
            api_key = userdata.get('GOOGLE_API_KEY')
        except (ImportError, KeyError):
                api_key = input("Please enter your Google API Key: ").strip()

    if not api_key:
        print("A Google API Key is required to run this script.")
        return
        
    # User selects the goal of the session
    brainstorm_type = select_brainstorm_type()

    topic = input("Enter a topic to brainstorm: ").strip()
    if not topic:
        print("A topic is required.")
        return

    # Initialize workflow with the selected type
    workflow = BrainstormingWorkflow(api_key=api_key, brainstorm_type=brainstorm_type)

    # RAG Step: Get external context
    rag_summary = await workflow.run_rag_search_and_summary(topic)

    # Stage 1: Create Personas
    personas = await workflow.run_preview_agent(topic, rag_summary)
    if not personas:
        return

    # Stage 2: Generate Ideas
    await workflow.run_divergent_ideation(topic, personas, rag_summary)
    if not workflow.raw_ideas_by_persona:
        return

    # User Interaction 1: Filter ideas
    filtered_ideas = user_filter_ideas(workflow.raw_ideas_by_persona)
    if not filtered_ideas:
        print("No ideas left after filtering. Exiting.")
        return

    # Stage 3: Evaluate User-Filtered Ideas
    evaluation_result = await workflow.run_convergent_evaluation(filtered_ideas)
    top_ideas = evaluation_result.get('top_ideas')
    if not top_ideas:
        print("Could not determine top ideas from evaluation. Exiting.")
        return
        
    # User Interaction 2: Select final idea
    chosen_idea = user_select_final_idea(top_ideas)

    # Stage 4: Plan Implementation
    await workflow.run_implementation_planning(chosen_idea)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
