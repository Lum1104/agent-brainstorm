# This file contains nodes related to persona and idea generation.

import asyncio
from typing import Dict, Any, List, Optional

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..schemas import PersonaList, ProjectIdeasList, ResearchIdeasList
from ..prompts import persona_prompts, ideation_prompts
from ..state import GraphState


async def persona_generation_node(state: GraphState) -> Dict[str, Any]:
    """Generates a team of distinct expert personas for a given topic."""
    print("\n--- 🧑‍💼 Persona Generation Node ---")
    topic = state["topic"]
    combined_context = state["combined_context"]
    brainstorm_type = state["brainstorm_type"]
    llm = state["llm"]

    parser = JsonOutputParser(pydantic_object=PersonaList)
    template = persona_prompts[brainstorm_type]
    prompt = PromptTemplate(
        template=template,
        input_variables=["topic", "combined_context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | llm | parser
    try:
        response = await chain.ainvoke(
            {"topic": topic, "combined_context": combined_context}
        )
        personas = response["personas"]
        for p in personas:
            print(
                f"- Role: {p['Role']}\n  Goal: {p['Goal']}\n  Backstory: {p['Backstory']}\n"
            )
        return {"personas": personas}
    except Exception as e:
        print(f"❌ Error in Persona Generation Node: {e}")
        return {"personas": []}


async def divergent_ideation_node(state: GraphState) -> Dict[str, Any]:
    """Generates a wide range of ideas from the perspective of each persona."""
    print("\n--- 💡 Divergent Ideation Node ---")
    topic = state["topic"]
    personas = state["personas"]
    combined_context = state["combined_context"]
    brainstorm_type = state["brainstorm_type"]
    llm = state["llm"]

    if brainstorm_type == "project":
        parser = JsonOutputParser(pydantic_object=ProjectIdeasList)
        ideas_key = "project_ideas"
    else:
        parser = JsonOutputParser(pydantic_object=ResearchIdeasList)
        ideas_key = "research_ideas"

    template = ideation_prompts[brainstorm_type]
    prompt_template = PromptTemplate(
        template=template,
        input_variables=["Role", "backstory", "goal", "topic", "combined_context"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt_template | llm | parser

    async def generate_for_persona(persona: Dict) -> Optional[List[Dict]]:
        try:
            persona_input = {
                "role": persona["Role"],
                "backstory": persona["Backstory"],
                "goal": persona["Goal"],
            }
            result = await chain.ainvoke(
                {**persona_input, "topic": topic, "combined_context": combined_context}
            )

            ideas_with_context = []
            for idea_obj in result.get(ideas_key, []):
                idea_with_context = idea_obj
                idea_with_context["Role"] = persona["Role"]
                ideas_with_context.append(idea_with_context)

            print(f"✅ Ideas successfully generated and parsed for {persona['Role']}.")
            return ideas_with_context
        except Exception as e:
            print(f"❌ Error generating ideas for {persona['Role']}: {e}")
            return None

    results_from_personas = await asyncio.gather(
        *(generate_for_persona(p) for p in personas)
    )
    all_generated_ideas = [
        idea for sublist in results_from_personas if sublist for idea in sublist
    ]
    print(f"\nTotal ideas generated across all personas: {len(all_generated_ideas)}\n")
    return {"all_generated_ideas": all_generated_ideas}
