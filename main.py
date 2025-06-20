# main.py
# This is the main entry point for the application.

import os
import asyncio
import itertools
import sys
from typing import List, Dict, Any, Optional
from workflow import BrainstormingWorkflow

# Try to import pypdf, but handle the case where it's not installed.
try:
    import pypdf
except ImportError:
    pypdf = None


def prompt_user_input(prompt_text: str) -> str:
    """Shows the cursor and prompts the user for input."""
    sys.stdout.write('\033[?25h') # Make cursor visible
    sys.stdout.flush()
    return input(prompt_text).strip()


async def spinner_task(shared_state: Dict[str, Any]):
    """Displays an animated spinner with the current stage name."""
    sys.stdout.write('\033[?25l')
    sys.stdout.flush()
    for char in itertools.cycle('|/-\\'):
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
    sys.stdout.write('\033[?25h')
    sys.stdout.flush()


def get_pdf_text(pdf_path: str) -> Optional[str]:
    """Extracts text from a PDF file."""
    if not pypdf:
        print("⚠️ 'pypdf' library not found. PDF processing is disabled.")
        print("   Please install it with: pip install pypdf")
        return None
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n\n"
            return text
    except FileNotFoundError:
        print(f"❌ Error: The file '{pdf_path}' was not found.")
        return None
    except Exception as e:
        print(f"❌ An error occurred while reading the PDF: {e}")
        return None

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

def generate_markdown_export(workflow: BrainstormingWorkflow) -> str:
    """
    Generates a complete markdown string of the entire brainstorming session.
    """
    md = []
    md.append(f"# Brainstorm Session: {workflow.topic}")
    md.append(f"**Type:** {workflow.brainstorm_type.replace('_', ' ').title()}")

    if workflow.combined_context:
        md.append('\n## Stage 1: Context & Team')
        md.append('### Research Context')
        md.append(workflow.combined_context)
    
    if workflow.personas:
        md.append('\n### Assembled Agent Team')
        for p in workflow.personas:
            md.append(f"- **{p['Role']}**")
            md.append(f"  - **Goal:** {p['Goal']}")
            md.append(f"  - **Backstory:** {p['Backstory']}")
    
    if workflow.all_generated_ideas:
        md.append('\n## Stage 2: Divergent Ideation')
        md.append('### All Generated Ideas')
        for idea in workflow.all_generated_ideas:
            md.append(f"\n#### Idea from {idea.get('role', 'Unknown')}")
            title = idea.get('idea') or idea.get('research_question', 'Untitled')
            if workflow.brainstorm_type == 'project':
                md.append(f"- **Idea:** {idea.get('idea', 'N/A')}")
                md.append(f"- **Target Audience:** {idea.get('target_audience', 'N/A')}")
                md.append(f"- **Problem Solved:** {idea.get('problem_solved', 'N/A')}")
            else:
                md.append(f"- **Research Question:** {idea.get('research_question', 'N/A')}")
                md.append(f"- **Methodology:** {idea.get('potential_methodology', 'N/A')}")
                md.append(f"- **Contribution:** {idea.get('potential_contribution', 'N/A')}")
            md.append(f"- **Rationale:** {idea.get('rationale', 'N/A')}")

            # Include the critique in the export
            matching_critique = next((c['critique'] for c in workflow.critiques if c['idea_title'] == title), None)
            if matching_critique:
                md.append(f"- **🔥 Red Team Critique:** {matching_critique}")


    if workflow.evaluation_markdown:
        md.append('\n## Stage 3: Convergent Evaluation')
        md.append(workflow.evaluation_markdown)

    if workflow.final_plan_text:
        md.append('\n## Stage 4: Final Plan')
        md.append(workflow.final_plan_text)

    return '\n\n'.join(md)

def save_markdown_file(filename: str, content: str):
    """Saves the given content to a file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✅ Session successfully saved to '{filename}'")
    except Exception as e:
        print(f"\n❌ Error saving file: {e}")

async def run_workflow_async(shared_state: Dict[str, Any]) -> Optional[BrainstormingWorkflow]:
    """Runs the asynchronous part of the workflow and returns the state object."""
    print("🚀 Welcome to the AI Brainstorming Agent!")
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            from google.colab import userdata
            api_key = userdata.get('GOOGLE_API_KEY')
        except (ImportError, KeyError):
            api_key = prompt_user_input("Please enter your Google API Key: ")

    if not api_key:
        print("A Google API Key is required to run this script.")
        return None
        
    brainstorm_type = select_brainstorm_type()
    topic = prompt_user_input("Enter a topic to brainstorm: ")
    if not topic:
        print("A topic is required.")
        return None

    pdf_text = None
    pdf_path = prompt_user_input("Enter the path to a PDF file for extra context, or press Enter to skip: ")
    if pdf_path:
        pdf_text = get_pdf_text(pdf_path)

    workflow = BrainstormingWorkflow(api_key=api_key, brainstorm_type=brainstorm_type)
    
    total_stages = 6 # Total number of async/interactive stages
    shared_state['total_stages'] = total_stages

    # Stage 1: Generate Context
    shared_state.update({'stage_name': 'Generating Context...', 'stage_index': 1})
    combined_context = await workflow.run_context_generation(topic, pdf_text)
    
    # Stage 2: Assemble Team
    shared_state.update({'stage_name': 'Assembling Team...', 'stage_index': 2})
    personas = await workflow.run_preview_agent(topic, combined_context)
    if not personas: return None

    # Stage 3: Divergent Ideation
    shared_state.update({'stage_name': 'Divergent Ideation...', 'stage_index': 3})
    await workflow.run_divergent_ideation(topic, personas, combined_context)
    if not workflow.all_generated_ideas: 
        print("\nNo ideas were generated during ideation. Exiting.")
        return None

    # Stop spinner for user interaction
    shared_state['stage_name'] = 'Waiting for user input...'
    filtered_ideas = user_filter_ideas(workflow.all_generated_ideas, brainstorm_type)
    if not filtered_ideas:
        print("No ideas left after filtering. Exiting.")
        return None

    # Stage 4: Red Team Critique
    shared_state.update({'stage_name': 'Red Team Critique...', 'stage_index': 4})
    await workflow.run_red_team_critique(filtered_ideas)

    # Stage 5: Convergent Evaluation
    shared_state.update({'stage_name': 'Convergent Evaluation...', 'stage_index': 5})
    evaluation_result = await workflow.run_convergent_evaluation(filtered_ideas)
    top_ideas = evaluation_result.get('top_ideas')
    if not top_ideas:
        print("Could not determine top ideas from evaluation. Exiting.")
        return None

    # Stop spinner for user interaction
    shared_state['stage_name'] = 'Waiting for user input...'
    chosen_idea = user_select_final_idea(top_ideas)
    if not chosen_idea:
        print("No idea selected. Exiting.")
        return None

    # Stage 6: Generate Final Plan
    shared_state.update({'stage_name': 'Generating Final Plan...', 'stage_index': 6})
    await workflow.run_implementation_planning(chosen_idea)
    
    return workflow

async def main_async():
    """Main async function that runs the workflow and the spinner concurrently."""
    shared_state = {'stage_name': 'Initializing...', 'stage_index': 0, 'total_stages': 0}
    spinner = asyncio.create_task(spinner_task(shared_state))
    
    workflow_task = asyncio.create_task(run_workflow_async(shared_state))
    
    workflow_result = await workflow_task
    
    spinner.cancel()
    try:
        await spinner
    except asyncio.CancelledError:
        pass
    
    return workflow_result


def main():
    """Main synchronous wrapper for the application."""
    workflow = None
    try:
        workflow = asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()
        return

    if workflow and workflow.final_plan_text:
        print("\n--- Session Complete ---")
        try:
            save_choice = prompt_user_input("Would you like to save the full session to a Markdown file? (y/n): ").lower()
            if save_choice == 'y':
                markdown_content = generate_markdown_export(workflow)
                default_filename = f"brainstorm_{workflow.topic.replace(' ', '_').lower()}.md"
                filename_prompt = f"Enter filename (default: {default_filename}): "
                filename = prompt_user_input(filename_prompt)
                if not filename:
                    filename = default_filename
                save_markdown_file(filename, markdown_content)
        except KeyboardInterrupt:
            print("\nSave operation cancelled by user.")
    else:
        print("\nWorkflow did not complete successfully. Exiting.")


if __name__ == "__main__":
    main()
