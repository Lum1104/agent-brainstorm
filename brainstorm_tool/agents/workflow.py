# workflow.py
# This file defines the core logic for the brainstorming process using LangGraph.

import json
import re
import asyncio
import datetime
from typing import List, Dict, Any, TypedDict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.document_loaders import ArxivLoader
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt
from regex import P


from .schemas import PersonaList, TopIdeasList, ProjectIdeasList, ResearchIdeasList, CritiqueList
from .prompts import persona_prompts, ideation_prompts, evaluation_prompts, planning_prompts, red_team_prompts


# --- Graph State Definition ---

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        api_key: The Google API key.
        llm: The language model instance.
        topic: The central topic for brainstorming.
        brainstorm_type: The type of brainstorm ('project' or 'research_paper').
        pdf_text: Optional text extracted from a user-provided PDF.
        combined_context: The summarized context from web search and PDF.
        personas: A list of generated expert personas.
        all_generated_ideas: A list of all ideas generated by the personas.
        critiques: A list of critiques for the generated ideas.
        filtered_ideas: A list of ideas after user filtering.
        evaluation_markdown: The markdown output from the evaluation stage.
        top_ideas: The top ideas selected by the analyst agent.
        chosen_idea: The final idea selected by the user for planning.
        final_plan_text: The final project plan or research outline.
"""
    api_key: str
    llm: ChatGoogleGenerativeAI
    topic: str
    brainstorm_type: str
    pdf_text: Optional[str]
    combined_context: str
    personas: List[Dict]
    all_generated_ideas: List[Dict]
    critiques: List[Dict]
    filtered_ideas: List[Dict]
    evaluation_markdown: str
    top_ideas: List[Dict]
    chosen_idea: Optional[Dict]
    final_plan_text: str


# --- Node Functions ---
async def context_generation_node(state: GraphState) -> Dict[str, Any]:
    """
    Generates a combined context from a web search and an optional user-provided PDF.
    """
    print("\n--- 🌐 Context Generation Node ---")
    topic = state['topic']
    pdf_text = state.get('pdf_text')
    llm = state['llm']
    
    search = DuckDuckGoSearchRun()
    search_results = search.run(topic)
    
    summarizer_prompt = PromptTemplate.from_template(
        "You are a Research Analyst. Your task is to provide a concise, neutral summary of the following text. Focus on key concepts, definitions, and the current state of the topic.\nText:\n---\n{text_to_summarize}\n---\n\nProvide your summary in a single, dense paragraph."
    )
    summarizer_chain = summarizer_prompt | llm | StrOutputParser()

    try:
        web_summary = await summarizer_chain.ainvoke({"text_to_summarize": search_results})
        combined_context = f"**Web Search Summary:**\n{web_summary}"

        if pdf_text:
            pdf_summary = await summarizer_chain.ainvoke({"text_to_summarize": pdf_text})
            combined_context += f"\n\n---\n\n**Uploaded Document Context:**\n{pdf_summary}"
        
        print("\n--- Combined Context Summary ---")
        print(combined_context)
        return {"combined_context": combined_context}
    except Exception as e:
        print(f"❌ Error during context generation: {e}")
        return {"combined_context": "No summary could be generated."}


async def persona_generation_node(state: GraphState) -> Dict[str, Any]:
    """Generates a team of distinct expert personas for a given topic."""
    print("\n--- 🧑‍💼 Persona Generation Node ---")
    topic = state['topic']
    combined_context = state['combined_context']
    brainstorm_type = state['brainstorm_type']
    llm = state['llm']

    parser = JsonOutputParser(pydantic_object=PersonaList)
    template = persona_prompts[brainstorm_type]
    prompt = PromptTemplate(
        template=template,
        input_variables=["topic", "combined_context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | llm | parser
    try:
        response = await chain.ainvoke({"topic": topic, "combined_context": combined_context})
        personas = response['personas']
        for p in personas:
            print(f"- Role: {p['Role']}\n  Goal: {p['Goal']}\n  Backstory: {p['Backstory']}\n")
        return {"personas": personas}
    except Exception as e:
        print(f"❌ Error in Persona Generation Node: {e}")
        return {"personas": []}


async def divergent_ideation_node(state: GraphState) -> Dict[str, Any]:
    """Generates a wide range of ideas from the perspective of each persona."""
    print("\n--- 💡 Divergent Ideation Node ---")
    topic = state['topic']
    personas = state['personas']
    combined_context = state['combined_context']
    brainstorm_type = state['brainstorm_type']
    llm = state['llm']
    
    if brainstorm_type == 'project':
        parser = JsonOutputParser(pydantic_object=ProjectIdeasList)
        ideas_key = 'project_ideas'
    else:
        parser = JsonOutputParser(pydantic_object=ResearchIdeasList)
        ideas_key = 'research_ideas'
        
    template = ideation_prompts[brainstorm_type]
    prompt_template = PromptTemplate(
        template=template,
        input_variables=["role", "backstory", "goal", "topic", "combined_context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt_template | llm | parser

    async def generate_for_persona(persona: Dict) -> Optional[List[Dict]]:
        try:
            persona_input = {"role": persona['Role'], "backstory": persona['Backstory'], "goal": persona['Goal']}
            result = await chain.ainvoke({**persona_input, "topic": topic, "combined_context": combined_context})
            
            ideas_with_context = []
            for idea_obj in result.get(ideas_key, []):
                idea_with_context = idea_obj
                idea_with_context['role'] = persona['Role']
                ideas_with_context.append(idea_with_context)

            print(f"✅ Ideas successfully generated and parsed for {persona['Role']}.")
            return ideas_with_context
        except Exception as e:
            print(f"❌ Error generating ideas for {persona['Role']}: {e}")
            return None

    results_from_personas = await asyncio.gather(*(generate_for_persona(p) for p in personas))
    all_generated_ideas = [idea for sublist in results_from_personas if sublist for idea in sublist]
    print(f"\nTotal ideas generated across all personas: {len(all_generated_ideas)}\n")
    return {"all_generated_ideas": all_generated_ideas}

async def user_filter_ideas_node(state: GraphState) -> Dict[str, Any]:
    """
    A node that interrupts the graph to ask the user to filter ideas.
    The `interrupt()` call pauses graph execution until it is resumed.
    """
    print("\n--- ⏸️ User Input Required: Idea Filtering ---")
    print("Review the generated ideas. The Analyst will only evaluate the ideas you keep.")
    brainstorm_type = state['brainstorm_type']
    all_ideas = state.get('all_generated_ideas')
    if not all_ideas:
        print("\nNo ideas were generated to be filtered. Continuing.")
        return {"filtered_ideas": []}
    
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

    indices_to_remove_str = interrupt(
        {
            "message": "\nEnter the numbers of ideas to REMOVE, separated by commas (e.g., 2, 5), or press Enter to keep all: "
        }
    )
    
    if not indices_to_remove_str or not indices_to_remove_str.strip():
        print(f"\n✅ Keeping all {len(all_ideas)} ideas. Resuming workflow...")
        return {"filtered_ideas": all_ideas}

    try:
        # Validate the input
        indices_to_remove = {int(num.strip()) - 1 for num in indices_to_remove_str.split(',')}
        filtered_ideas = [idea for i, idea in enumerate(all_ideas) if i not in indices_to_remove]
        print(f"\n✅ Removed {len(all_ideas) - len(filtered_ideas)} ideas. {len(filtered_ideas)} ideas remaining. Resuming workflow...")
        return {"filtered_ideas": filtered_ideas}
    except ValueError:
        # A more complex graph could have a separate validation node and a conditional edge
        # that loops back if validation fails.
        print("⚠️ Invalid input. Could not parse numbers. Keeping all ideas.")
        return {"filtered_ideas": all_ideas}

async def user_select_idea_node(state: GraphState) -> Dict[str, Any]:
    """
    A node that interrupts the graph to ask the user to select the final idea.
    """
    print("\n--- ⏸️ User Input Required: Final Selection ---")
    print("The Analyst has provided the top ideas. Please select one to create a final document.")
    top_ideas = state.get('top_ideas')
    if not top_ideas:
        print("⚠️ No top ideas were provided by the analyst. Skipping.")
        return {"chosen_idea": None}
    
    for i, idea in enumerate(top_ideas):
        print(f"\n  [{i+1}] Title: {idea['title']}")
        print(f"      Description: {idea['description']}")

    choice_str = interrupt(
        {
            "message": f"\nChoose an idea to proceed with (1-{len(top_ideas)}): "
        }
    )

    try:
        choice = int(choice_str)
        if 1 <= choice <= len(top_ideas):
            chosen = top_ideas[choice - 1]
            print(f"✅ Great choice! Selecting '{chosen['title']}'. Generating the final document...")
            return {"chosen_idea": chosen}
        else:
            print(f"⚠️ Invalid choice. Number out of range. Select the first idea by default.")
            return {"chosen_idea": top_ideas[0]}
    except (ValueError, IndexError, TypeError):
        # Handles cases where input is not a number, or empty.
        print("⚠️ Invalid input. Could not parse number. Selecting the first idea by default.")
        return {"chosen_idea": top_ideas[0]}    

async def red_team_critique_node(state: GraphState) -> Dict[str, Any]:
    """Runs a 'Red Team' agent to critique a list of ideas."""
    print("\n--- 🛡️ Red Team Critique Node ---")
    ideas_to_critique = state['filtered_ideas']
    brainstorm_type = state['brainstorm_type']
    llm = state['llm']

    if not ideas_to_critique:
        print("⚠️ No ideas to critique. Skipping.")
        return {"critiques": []}

    critique_input_str = ""
    for i, idea in enumerate(ideas_to_critique):
        title = idea.get('idea') or idea.get('research_question', f"Idea {i+1}")
        critique_input_str += f"Idea Title: {title}\n"
        for key, value in idea.items():
            if key not in ['role']:
                critique_input_str += f"- {key.replace('_', ' ').title()}: {value}\n"
        critique_input_str += "---\n"

    parser = JsonOutputParser(pydantic_object=CritiqueList)
    template = red_team_prompts[brainstorm_type]
    prompt = PromptTemplate(
        template=template,
        input_variables=["ideas_to_critique"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | llm | parser

    try:
        response = await chain.ainvoke({"ideas_to_critique": critique_input_str})
        critiques = response.get('critiques', [])
        for crit in critiques:
            print(f"\nCritique for '{crit['idea_title']}':")
            print(f"  - {crit['critique']}")
        return {"critiques": critiques}
    except Exception as e:
        print(f"❌ Error during Red Team critique: {e}")
        return {"critiques": []}


async def convergent_evaluation_node(state: GraphState) -> Dict[str, Any]:
    """Analyzes, critiques, and selects the top ideas."""
    print("\n--- 📊 Convergent Evaluation Node ---")
    ideas_to_evaluate = state['filtered_ideas']
    critiques = state.get('critiques', [])
    brainstorm_type = state['brainstorm_type']
    llm = state['llm']

    if not ideas_to_evaluate:
        print("⚠️ No ideas to evaluate. Skipping.")
        return {"top_ideas": [], "evaluation_markdown": ""}

    raw_ideas_string = ""
    for idea in ideas_to_evaluate:
        title = idea.get('idea') or idea.get('research_question', 'Untitled')
        raw_ideas_string += f"### Idea from {idea['role']}: {title}\n"
        for key, value in idea.items():
             raw_ideas_string += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        
        matching_critique = next((c['critique'] for c in critiques if c['idea_title'] == title), None)
        if matching_critique:
            raw_ideas_string += f"- **Red Team Critique:** {matching_critique}\n"
        raw_ideas_string += "\n---\n"
    
    parser = StrOutputParser()
    template = evaluation_prompts[brainstorm_type]
    prompt = PromptTemplate.from_template(template)
    chain = prompt | llm | parser
    
    try:
        full_response = await chain.ainvoke({"raw_ideas": raw_ideas_string})
        analysis_markdown = full_response
        top_ideas_list = []

        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", full_response, re.DOTALL)
        if json_match:
            json_string = json_match.group(1).strip()
            try:
                parsed_json = json.loads(json_string)
                top_ideas_obj = TopIdeasList(ideas=parsed_json)
                top_ideas_list = top_ideas_obj.model_dump()['ideas']
                analysis_markdown = full_response.replace(json_match.group(0), "").strip()
            except (json.JSONDecodeError, TypeError) as e:
                print(f"❌ Error decoding or validating JSON from evaluation: {e}")

        print("\n--- Full Analysis ---")
        print(analysis_markdown)
        
        if top_ideas_list:
            print("\n--- Top Ideas ---")
            for idea in top_ideas_list:
                print(f"- Title: {idea['title']}\n  Description: {idea['description']}\n")
        
        return {"evaluation_markdown": analysis_markdown, "top_ideas": top_ideas_list}

    except Exception as e:
        print(f"❌ Error during convergent evaluation: {e}")
        return {"top_ideas": [], "evaluation_markdown": ""}


async def implementation_planning_node(state: GraphState) -> Dict[str, Any]:
    """Generates a final plan for the selected idea."""
    print("\n--- 📝 Implementation Planning Node ---")
    idea = state['chosen_idea']
    brainstorm_type = state['brainstorm_type']
    llm = state['llm']
    
    if not idea:
        return {"final_plan_text": "No idea chosen for planning."}

    search_query = idea['title']
    arxiv_context = "No relevant papers found on ArXiv for this topic."

    try:
        arxiv_loader = ArxivLoader(query=search_query, load_max_docs=8, load_all_available_meta=True)
        paper_documents = arxiv_loader.get_summaries_as_docs()
        
        if paper_documents:
            summaries = []
            today = datetime.datetime.now().date()
            for doc in paper_documents:
                published_date = doc.metadata.get("Published")
                if published_date and (today - published_date).days <= 2 * 365:
                    summaries.append(f"**Paper: {doc.metadata.get('Title', 'N/A')}**\nAbstract: {doc.page_content or 'N/A'}")
            
            if summaries:
                arxiv_context = "**Relevant Research from ArXiv:**\n\n" + "\n\n---\n\n".join(summaries)
    except Exception as e:
        print(f"❌ Error during ArXiv search: {e}")

    parser = StrOutputParser()
    template = planning_prompts[brainstorm_type]
    prompt = PromptTemplate(template=template, input_variables=["title", "description", "arxiv_context"])
    chain = prompt | llm | parser

    try:
        plan_text = await chain.ainvoke({
            "title": idea['title'], 
            "description": idea['description'],
            "arxiv_context": arxiv_context
        })
        final_plan_text = plan_text + "\n\n---\n\n" + arxiv_context
        
        markdown_plan = final_plan_text
        mermaid_match = re.search(r"```mermaid\s*([\s\S]*?)```", final_plan_text, re.DOTALL)
        if mermaid_match:
            mermaid_chart = mermaid_match.group(1).strip()
            markdown_plan = final_plan_text.replace(mermaid_match.group(0), "").strip()
            print("\n--- Generated Mermaid Flowchart ---")
            print("Copy the code below and paste it into a Mermaid.js renderer (e.g., https://mermaid.live)")
            print(f"```mermaid\n{mermaid_chart}\n```")

        print(f"\n--- Generated {brainstorm_type.replace('_', ' ').title()} Outline ---")
        print(markdown_plan)

        return {"final_plan_text": final_plan_text}
    except Exception as e:
        print(f"❌ Error generating final document: {e}")
        return {"final_plan_text": "Error during plan generation."}


# --- Graph Builder ---
def build_graph(checkpointer: InMemorySaver):
    """Builds the LangGraph agent graph."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("context_generation", context_generation_node)
    workflow.add_node("persona_generation", persona_generation_node)
    workflow.add_node("divergent_ideation", divergent_ideation_node)
    workflow.add_node("user_filter_ideas", user_filter_ideas_node)
    workflow.add_node("red_team_critique", red_team_critique_node)
    workflow.add_node("convergent_evaluation", convergent_evaluation_node)
    workflow.add_node("user_select_idea", user_select_idea_node)
    workflow.add_node("implementation_planning", implementation_planning_node)

    # Define edges
    workflow.set_entry_point("context_generation")
    workflow.add_edge("context_generation", "persona_generation")
    workflow.add_edge("persona_generation", "divergent_ideation")
    workflow.add_edge("divergent_ideation", "user_filter_ideas")
    workflow.add_edge("user_filter_ideas", "red_team_critique")
    workflow.add_edge("red_team_critique", "convergent_evaluation")
    workflow.add_edge("convergent_evaluation", "user_select_idea")
    workflow.add_edge("user_select_idea", "implementation_planning")
    workflow.add_edge("implementation_planning", END)
    
    # Compile the graph
    app = workflow.compile(checkpointer=checkpointer)
    return app