# main.py
# This is the main entry point for the application.

import os
import asyncio
from typing import List, Dict, Any, Optional
from workflow import BrainstormingWorkflow

# Try to import pypdf, but handle the case where it's not installed.
try:
    import pypdf
except ImportError:
    pypdf = None

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
            response = input("\nEnter the numbers of ideas to REMOVE, separated by commas (e.g., 2, 5, 8), or press Enter to keep all: ").strip()
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
            choice_str = input(f"\nChoose an idea to proceed with (1-{len(top_ideas)}): ").strip()
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
        choice = input("Enter your choice (1 or 2): ").strip()
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
            if workflow.brainstorm_type == 'project':
                md.append(f"- **Idea:** {idea.get('idea', 'N/A')}")
                md.append(f"- **Target Audience:** {idea.get('target_audience', 'N/A')}")
                md.append(f"- **Problem Solved:** {idea.get('problem_solved', 'N/A')}")
                md.append(f"- **Rationale:** {idea.get('rationale', 'N/A')}")
            else: # research_paper
                md.append(f"- **Research Question:** {idea.get('research_question', 'N/A')}")
                md.append(f"- **Methodology:** {idea.get('potential_methodology', 'N/A')}")
                md.append(f"- **Contribution:** {idea.get('potential_contribution', 'N/A')}")
                md.append(f"- **Rationale:** {idea.get('rationale', 'N/A')}")

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

async def main():
    """Main function to run the brainstorming workflow."""
    print("🚀 Welcome to the AI Brainstorming Agent!")
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            from google.colab import userdata
            api_key = userdata.get('GOOGLE_API_KEY')
        except (ImportError, KeyError):
            api_key = input("Please enter your Google API Key: ").strip()

    if not api_key:
        print("A Google API Key is required to run this script.")
        return
        
    brainstorm_type = select_brainstorm_type()
    topic = input("Enter a topic to brainstorm: ").strip()
    if not topic:
        print("A topic is required.")
        return

    pdf_text = None
    pdf_path = input("Enter the path to a PDF file for extra context, or press Enter to skip: ").strip()
    if pdf_path:
        pdf_text = get_pdf_text(pdf_path)

    workflow = BrainstormingWorkflow(api_key=api_key, brainstorm_type=brainstorm_type)
    
    combined_context = await workflow.run_context_generation(topic, pdf_text)
    personas = await workflow.run_preview_agent(topic, combined_context)
    if not personas: return

    await workflow.run_divergent_ideation(topic, personas, combined_context)
    if not workflow.all_generated_ideas: return

    filtered_ideas = user_filter_ideas(workflow.all_generated_ideas, brainstorm_type)
    if not filtered_ideas:
        print("No ideas left after filtering. Exiting.")
        return

    evaluation_result = await workflow.run_convergent_evaluation(filtered_ideas)
    top_ideas = evaluation_result.get('top_ideas')
    if not top_ideas:
        print("Could not determine top ideas from evaluation. Exiting.")
        return
        
    chosen_idea = user_select_final_idea(top_ideas)
    if not chosen_idea:
        print("No idea selected. Exiting.")
        return

    await workflow.run_implementation_planning(chosen_idea)
    

    print("\n--- Session Complete ---")
    save_choice = input("Would you like to save the full session to a Markdown file? (Y/n): ").strip().lower()
    if save_choice == 'y' or not save_choice:
        print("Generating Markdown export...")
        markdown_content = generate_markdown_export(workflow)
        default_filename = f"brainstorm_{workflow.topic.replace(' ', '_').lower()}.md"
        filename_prompt = f"Enter filename (default: {default_filename}): "
        filename = input(filename_prompt).strip()
        if not filename:
            filename = default_filename
        save_markdown_file(filename, markdown_content)
    else:
        print("Session not saved. You can run the script again to save it later.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
