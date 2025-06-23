# main.py
# This is the main entry point for the application, now using LangGraph.

import os
import asyncio
import sys

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from brainstorm_tool.agents.workflow import build_graph, GraphState
from brainstorm_tool.utils.ui import (
    prompt_user_input,
    select_brainstorm_type,
)
from brainstorm_tool.utils.file_utils import (
    generate_markdown_export,
    save_markdown_file,
)


async def main_async():
    """Main async function that runs the graph-based workflow."""
    print("🚀 Welcome to the AI Brainstorming Agent (LangGraph Edition)!")

    # 1. --- Initial Setup ---
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            from google.colab import userdata

            api_key = userdata.get("GOOGLE_API_KEY")
        except (ImportError, KeyError):
            api_key = prompt_user_input("Please enter your Google API Key: ")

    if not api_key:
        print("A Google API Key is required. Exiting.")
        return

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", google_api_key=api_key, temperature=0.7
    )

    brainstorm_type = select_brainstorm_type()
    topic = prompt_user_input("Enter a topic to brainstorm: ")
    if not topic:
        print("A topic is required. Exiting.")
        return

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
            value = input(user_instruction)
            result = await app.ainvoke(Command(resume=value), config=config)
    except Exception as e:
        print(f"\nAn error occurred during graph execution: {e}")

    # 4. --- Save Results ---
    if "final_plan_text" in result:
        print("\n✅ Graph execution complete.")
        if result.get("final_plan_text"):
            print("\n--- Session Complete ---")
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
                print("Session not saved.")
        else:
            print("\nWorkflow completed, but no final plan was generated to save.")
    else:
        print("\nWorkflow did not complete successfully or was exited early.")


def main():
    """Main synchronous wrapper for the application."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    finally:
        # Ensure cursor is visible on exit
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
