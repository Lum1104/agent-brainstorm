# file_utils.py
# This file contains utility functions for file I/O and data handling.

import re
from typing import Optional
from brainstorm.agents.state import GraphState
from brainstorm.utils.ui import console

# Try to import pypdf, but handle the case where it's not installed.
try:
    import pypdf
except ImportError:
    pypdf = None


def get_pdf_text(pdf_path: str) -> Optional[str]:
    """Extracts text from a PDF file."""
    if not pypdf:
        console.print("⚠️ 'pypdf' library not found. PDF processing is disabled.", style="yellow")
        console.print("   Please install it with: pip install pypdf", style="yellow")
        return None
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n\n"
            return text
    except FileNotFoundError:
        console.print(f"❌ Error: The file '{pdf_path}' was not found.", style="red")
        return None
    except Exception as e:
        console.print(f"❌ An error occurred while reading the PDF: {e}", style="red")
        return None


def generate_markdown_export(state: GraphState) -> str:
    """
    Generates a complete markdown string of the entire brainstorming session
    from the final graph state.
    """
    md = []
    md.append(f"# Brainstorm Session: {state.get('topic', 'N/A')}")
    md.append(f"**Type:** {state.get('brainstorm_type', '').replace('_', ' ').title()}")

    if state.get("combined_context"):
        md.append("\n## Stage 1: Context & Team")
        md.append("### Research Context")
        md.append(state["combined_context"])

    if state.get("personas"):
        md.append("\n### Assembled Agent Team")
        for p in state["personas"]:
            md.append(f"- **{p['Role']}**")
            md.append(f"  - **Goal:** {p['Goal']}")
            md.append(f"  - **Backstory:** {p['Backstory']}")

    if state.get("all_generated_ideas"):
        md.append("\n## Stage 2: Divergent Ideation")
        md.append("### All Generated Ideas (Pre-Filtering)")
        idea_idx = 1
        for idea in state["all_generated_ideas"]:
            md.append(f"\n#### Idea {idea_idx}")
            idea_idx += 1
            title = idea.get("idea") or idea.get("research_question", "Untitled")
            if state.get("brainstorm_type") == "project":
                md.append(f"- **Idea:** {idea.get('idea', 'N/A')}")
                md.append(
                    f"- **Target Audience:** {idea.get('target_audience', 'N/A')}"
                )
                md.append(f"- **Problem Solved:** {idea.get('problem_solved', 'N/A')}")
            else:  # research_paper
                md.append(
                    f"- **Research Question:** {idea.get('research_question', 'N/A')}"
                )
                md.append(
                    f"- **Methodology:** {idea.get('potential_methodology', 'N/A')}"
                )
                md.append(
                    f"- **Contribution:** {idea.get('potential_contribution', 'N/A')}"
                )
            md.append(f"- **Rationale:** {idea.get('rationale', 'N/A')}")

            # Include the critique in the export, if it exists for this idea
            if state.get("critiques"):
                matching_critique = next(
                    (
                        c["critique"]
                        for c in state["critiques"]
                        if c["idea_title"] == title
                    ),
                    None,
                )
                if matching_critique:
                    md.append(f"- **🔥 Red Team Critique:** {matching_critique}")

    if state.get("evaluation_markdown"):
        md.append("\n## Stage 3: Convergent Evaluation")
        md.append(state["evaluation_markdown"])

    if state.get("final_plan_text"):
        md.append("\n## Stage 4: Final Plan")
        md.append(state["final_plan_text"])

    return "\n\n".join(md)


def save_markdown_file(filename: str, content: str):
    """Saves the given content to a file."""
    try:
        content = re.sub(
            r"```markdown\s*([\s\S]*?)```", r"\1", content, flags=re.DOTALL
        )
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"\n✅ Session successfully saved to '{filename}'", style="bold green")
    except Exception as e:
        console.print(f"\n❌ Error saving file: {e}", style="red")
