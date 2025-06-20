# main.py
# This is the main entry point for the application.

import os
import asyncio
import sys
from typing import Dict, Any, Optional

from brainstorm_tool.agents.workflow import BrainstormingWorkflow
from brainstorm_tool.utils.ui import (
    prompt_user_input,
    spinner_task,
    user_filter_ideas,
    user_select_final_idea,
    select_brainstorm_type
)
from brainstorm_tool.utils.file_utils import (
    get_pdf_text,
    generate_markdown_export,
    save_markdown_file
)

async def run_workflow_async(shared_state: Dict[str, Any]) -> Optional[BrainstormingWorkflow]:
    """Runs the asynchronous part of the workflow and returns the state object."""
    print("🚀 Welcome to the AI Brainstorming Agent!")
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        try:
            # Fallback for Google Colab
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
    shared_state['stop_spinner'] = True
    await asyncio.sleep(0.1) # allow spinner to finish
    filtered_ideas = user_filter_ideas(workflow.all_generated_ideas, brainstorm_type)
    if not filtered_ideas:
        print("No ideas left after filtering. Exiting.")
        return None
    shared_state['stop_spinner'] = False
    
    # Restart spinner for next async phase
    spinner = asyncio.create_task(spinner_task(shared_state))

    # Stage 4: Red Team Critique
    shared_state.update({'stage_name': 'Red Team Critique...', 'stage_index': 4})
    await workflow.run_red_team_critique(filtered_ideas)

    # Stage 5: Convergent Evaluation
    shared_state.update({'stage_name': 'Convergent Evaluation...', 'stage_index': 5})
    evaluation_result = await workflow.run_convergent_evaluation(filtered_ideas)
    top_ideas = evaluation_result.get('top_ideas')
    if not top_ideas:
        print("Could not determine top ideas from evaluation. Exiting.")
        shared_state['stop_spinner'] = True # Stop spinner before exit
        await spinner
        return None

    # Stop spinner for user interaction
    shared_state['stop_spinner'] = True
    await spinner
    chosen_idea = user_select_final_idea(top_ideas)
    if not chosen_idea:
        print("No idea selected. Exiting.")
        return None
    shared_state['stop_spinner'] = False
    
    # Restart spinner for final async phase
    spinner = asyncio.create_task(spinner_task(shared_state))

    # Stage 6: Generate Final Plan
    shared_state.update({'stage_name': 'Generating Final Plan...', 'stage_index': 6})
    await workflow.run_implementation_planning(chosen_idea)
    
    # Stop the final spinner
    shared_state['stop_spinner'] = True
    await spinner
    
    return workflow

async def main_async():
    """Main async function that runs the workflow and the spinner concurrently."""
    shared_state = {
        'stage_name': 'Initializing...', 
        'stage_index': 0, 
        'total_stages': 0,
        'stop_spinner': False
    }
    
    # This initial spinner will be stopped and restarted inside the workflow
    initial_spinner = asyncio.create_task(spinner_task(shared_state))
    
    workflow_result = await run_workflow_async(shared_state)
    
    # Ensure any running spinner is stopped
    shared_state['stop_spinner'] = True
    try:
        await asyncio.wait_for(initial_spinner, timeout=1.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass # Task is already done or cancelled, which is fine
    
    return workflow_result


def main():
    """Main synchronous wrapper for the application."""
    workflow = None
    try:
        workflow = asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting.")
    finally:
        # Ensure cursor is visible on exit
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()

    if workflow and workflow.final_plan_text:
        print("\n--- Session Complete ---")
        try:
            save_choice = prompt_user_input("Would you like to save the full session to a Markdown file? (Y/n): ").lower()
            if save_choice == 'y' or not save_choice:
                markdown_content = generate_markdown_export(workflow)
                default_filename = f"brainstorm_{workflow.topic.replace(' ', '_').lower()}.md"
                filename_prompt = f"Enter filename (default: {default_filename}): "
                filename = prompt_user_input(filename_prompt) or default_filename
                save_markdown_file(filename, markdown_content)
            else:
                print("Session not saved. Exiting.")
        except KeyboardInterrupt:
            print("\nSave operation cancelled by user.")
    else:
        print("\nWorkflow did not complete successfully. Exiting.")


if __name__ == "__main__":
    main()
