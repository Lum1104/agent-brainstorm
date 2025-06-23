# This file contains nodes related to evaluating and critiquing ideas.

import json
import re
import asyncio
from typing import Dict, Any, List
from collections import defaultdict

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from ..schemas import (
    ProjectIdeasList,
    ResearchIdeasList,
    CritiqueList,
    TopIdeasList,
)
from ..prompts import (
    collaborative_discussion_prompts,
    red_team_prompts,
    evaluation_prompts,
)
from ..state import GraphState


async def collaborative_discussion_node(state: GraphState) -> Dict[str, Any]:
    """
    Simulates a discussion where each persona evaluates all ideas.
    Ideas selected by two or more personas are kept, along with the rationales from each agent who selected them.
    """
    print("\n--- 🤝 Collaborative Discussion Node ---")
    topic = state["topic"]
    personas = state["personas"]
    all_generated_ideas = state["all_generated_ideas"]
    brainstorm_type = state["brainstorm_type"]
    llm = state.get("llm")

    if not all_generated_ideas:
        print("⚠️ No ideas to discuss. Skipping.")
        return {"all_generated_ideas": []}

    # Determine the correct parser and keys based on the brainstorm type
    if brainstorm_type == "project":
        parser = JsonOutputParser(pydantic_object=ProjectIdeasList)
        ideas_key = "project_ideas"
        idea_title_key = "idea"
    else:  # research_paper
        parser = JsonOutputParser(pydantic_object=ResearchIdeasList)
        ideas_key = "research_ideas"
        idea_title_key = "research_question"

    # Format all ideas into a single string for the prompt context
    all_ideas_text = ""
    for idea in all_generated_ideas:
        all_ideas_text += (
            f"### Idea from {idea['Role']}: {idea.get(idea_title_key, 'Untitled')}\n"
        )
        for key, value in idea.items():
            if key != "Role":
                all_ideas_text += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        all_ideas_text += "\n---\n"

    # Set up the LangChain prompt and chain
    template = collaborative_discussion_prompts[brainstorm_type]
    prompt = PromptTemplate(
        template=template,
        input_variables=["Role", "backstory", "topic", "all_ideas"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | llm | parser

    async def get_persona_selections(persona: Dict) -> List[Dict]:
        """Sub-task to get selections for a single persona."""
        print(f"-> Asking {persona['Role']} for their top picks...")
        try:
            persona_input = {
                "role": persona["Role"],
                "backstory": persona["Backstory"],
            }
            response = await chain.ainvoke(
                {
                    **persona_input,
                    "topic": topic,
                    "all_ideas": all_ideas_text,
                }
            )
            selected_ideas = response.get(ideas_key, [])
            print(f"✅ {persona['Role']} selected {len(selected_ideas)} ideas.")
            return selected_ideas
        except Exception as e:
            print(f"❌ Error getting selections from {persona['Role']}: {e}")
            return []

    # Gather selections from all personas
    persona_selections = await asyncio.gather(
        *(get_persona_selections(p) for p in personas)
    )

    # Use a dictionary to track idea counts and rationales
    idea_tracker = defaultdict(
        lambda: {"count": 0, "rationales": [], "idea_data": None}
    )

    # Correlate selections with the persona who made them to store their specific rationale
    for persona, selected_ideas_list in zip(personas, persona_selections):
        if not selected_ideas_list:
            continue
        for idea in selected_ideas_list:
            title = idea.get(idea_title_key)
            if not title:
                continue

            rationale = idea.get("rationale", "No rationale provided.")

            # Increment the count and add the persona's rationale
            idea_tracker[title]["count"] += 1
            idea_tracker[title]["rationales"].append(
                f"**{persona['Role']}**: {rationale}"
            )

            # Store the full original idea data only the first time we encounter it
            if idea_tracker[title]["idea_data"] is None:
                original_idea = next(
                    (
                        og
                        for og in all_generated_ideas
                        if og.get(idea_title_key) == title
                    ),
                    None,
                )
                if original_idea:
                    idea_tracker[title]["idea_data"] = original_idea.copy()

    # Filter for ideas that have reached a consensus (selected >= 2 times)
    collaborative_ideas = []
    for title, data in idea_tracker.items():
        if data["count"] >= 2:
            final_idea = data["idea_data"]
            if final_idea:
                # Replace the original rationale with the collection of new ones
                final_idea["rationale"] = "\n".join(data["rationales"])
                collaborative_ideas.append(final_idea)

    print(f"\nTotal ideas with consensus (>= 2 selections): {len(collaborative_ideas)}")
    return {"all_generated_ideas": collaborative_ideas}


async def red_team_critique_node(state: GraphState) -> Dict[str, Any]:
    """Runs a 'Red Team' agent to critique a list of ideas."""
    print("\n--- 🛡️ Red Team Critique Node ---")
    ideas_to_critique = state["filtered_ideas"]
    brainstorm_type = state["brainstorm_type"]
    llm = state["llm"]

    if not ideas_to_critique:
        print("⚠️ No ideas to critique. Skipping.")
        return {"critiques": []}

    critique_input_str = ""
    for i, idea in enumerate(ideas_to_critique):
        title = idea.get("idea") or idea.get("research_question", f"Idea {i+1}")
        critique_input_str += f"Idea Title: {title}\n"
        for key, value in idea.items():
            if key not in ["Role"]:
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
        critiques = response.get("critiques", [])
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
    ideas_to_evaluate = state["filtered_ideas"]
    critiques = state.get("critiques", [])
    brainstorm_type = state["brainstorm_type"]
    llm = state["llm"]

    if not ideas_to_evaluate:
        print("⚠️ No ideas to evaluate. Skipping.")
        return {"top_ideas": [], "evaluation_markdown": ""}

    raw_ideas_string = ""
    for idea in ideas_to_evaluate:
        title = idea.get("idea") or idea.get("research_question", "Untitled")
        raw_ideas_string += f"### {title}\n"
        for key, value in idea.items():
            raw_ideas_string += f"- **{key.replace('_', ' ').title()}:** {value}\n"

        matching_critique = next(
            (c["critique"] for c in critiques if c["idea_title"] == title), None
        )
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
                top_ideas_list = top_ideas_obj.model_dump()["ideas"]
                analysis_markdown = full_response.replace(
                    json_match.group(0), ""
                ).strip()
            except (json.JSONDecodeError, TypeError) as e:
                print(f"❌ Error decoding or validating JSON from evaluation: {e}")

        print("\n--- Full Analysis ---")
        print(analysis_markdown)

        if top_ideas_list:
            print("\n--- Top Ideas ---")
            for idea in top_ideas_list:
                print(
                    f"- Title: {idea['title']}\n  Description: {idea['description']}\n"
                )

        return {"evaluation_markdown": analysis_markdown, "top_ideas": top_ideas_list}

    except Exception as e:
        print(f"❌ Error during convergent evaluation: {e}")
        return {"top_ideas": [], "evaluation_markdown": ""}
