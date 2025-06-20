# file_utils.py
# This file contains utility functions for file I/O and data handling.

from typing import Optional
from ..agents.workflow import BrainstormingWorkflow

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
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n\n"
            return text
    except FileNotFoundError:
        print(f"❌ Error: The file '{pdf_path}' was not found.")
        return None
    except Exception as e:
        print(f"❌ An error occurred while reading the PDF: {e}")
        return None

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
            else: # research_paper
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
