# main.py
# This is the main entry point for the application, now using LangGraph.

import os
import asyncio
import sys
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from brainstorm.agents.workflow import build_graph
from brainstorm.agents.state import GraphState
from brainstorm.utils.ui import (
    prompt_user_input,
    select_brainstorm_type,
    console,
)
import typer
from rich.panel import Panel
from brainstorm.utils.file_utils import (
    generate_markdown_export,
    save_markdown_file,
)


async def main_async(api_key: str, topic: str, brainstorm_type: str):
    """Main async function that runs the graph-based workflow."""
    console.print(Panel.fit("🚀 Welcome to the AI Brainstorming Agent!", style="bold green"))

    # 1. --- Initial Setup ---
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", google_api_key=api_key, temperature=0.7
    )

    # 2. --- Build and Compile the Graph ---
    checkpointer = InMemorySaver()
    app = build_graph(checkpointer)
    # print(app.get_graph().draw_mermaid())

    # 3. --- Run the Graph Stream ---
    initial_state: GraphState = {
        "api_key": api_key,
        "llm": llm,
        "topic": topic,
        "brainstorm_type": brainstorm_type,
        "pdf_text": None,
        "combined_context": "",
        "personas": [],
        "all_generated_ideas": [],
        "critiques": [],
        "filtered_ideas": [],
        "evaluation_markdown": "",
        "top_ideas": [],
        "chosen_idea": None,
        "final_plan_text": "",
        "arxiv_context": "No relevant papers found on ArXiv for this topic.",
        "use_arxiv_search": True,
        "user_plan_feedback": "",
    }

    config = {
        "configurable": {"thread_id": "brainstorm-thread-v2"}
    }  # Using a new thread ID
    try:
        result = await app.ainvoke(input=initial_state, config=config)
        while "__interrupt__" in result:
            user_instruction = result["__interrupt__"][0].value["message"]
            value = prompt_user_input(user_instruction)
            result = await app.ainvoke(Command(resume=value), config=config)
    except Exception as e:
        console.print(f"\nAn error occurred during graph execution: {e}", style="red")

    # 4. --- Save Results ---
    if "final_plan_text" in result:
        console.print("\n✅ Graph execution complete.", style="bold green")
        if result.get("final_plan_text"):
            console.print("\n--- Session Complete ---", style="bold cyan")
            save_choice = prompt_user_input(
                "Would you like to save the full session to a Markdown file? (Y/n): "
            ).lower()
            if save_choice in ["y", "yes", ""]:
                markdown_content = generate_markdown_export(result)
                default_filename = (
                    f"brainstorm_{result['topic'].replace(' ', '_').lower()}.md"
                )
                filename = (
                    prompt_user_input(f"Enter filename (default: {default_filename}): ")
                    or default_filename
                )
                save_markdown_file(filename, markdown_content)
            else:
                console.print("Session not saved.", style="yellow")
        else:
            console.print("\nWorkflow completed, but no final plan was generated to save.", style="yellow")
    else:
        console.print("\nWorkflow did not complete successfully or was exited early.", style="red")


app = typer.Typer(add_completion=False)


@app.command()
def run(
    topic: Optional[str] = typer.Option(None, "--topic", "-q", help="Topic to brainstorm"),
    brainstorm_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Type of brainstorming session (project or research_paper)",
        case_sensitive=False,
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        envvar="GOOGLE_API_KEY",
        help="Google API Key (or set GOOGLE_API_KEY env var)",
    ),
):
    """Run the AI Brainstorming Agent."""
    try:
        # Resolve API key
        resolved_api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not resolved_api_key:
            resolved_api_key = prompt_user_input("Please enter your Google API Key: ")
        if not resolved_api_key:
            console.print("A Google API Key is required. Exiting.", style="red")
            raise typer.Exit(code=1)

        # Resolve brainstorm type
        resolved_type = (
            brainstorm_type.lower() if brainstorm_type else select_brainstorm_type()
        )
        if resolved_type not in {"project", "research_paper"}:
            console.print("Invalid type. Choose 'project' or 'research_paper'.", style="red")
            raise typer.Exit(code=1)

        # Resolve topic
        resolved_topic = topic or prompt_user_input("Enter a topic to brainstorm: ")
        if not resolved_topic:
            console.print("A topic is required. Exiting.", style="red")
            raise typer.Exit(code=1)

        asyncio.run(main_async(resolved_api_key, resolved_topic, resolved_type))
    except KeyboardInterrupt:
        console.print("\nProcess interrupted by user. Exiting.", style="yellow")
    finally:
        # Ensure cursor is visible on exit
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


if __name__ == "__main__":
    app()
