# This file contains the final node for implementation planning.

import re
from typing import Dict, Any

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from ..prompts import planning_prompts
from ..state import GraphState


async def implementation_planning_node(state: GraphState) -> Dict[str, Any]:
    """Generates a final plan for the selected idea."""
    print("\n--- 📝 Implementation Planning Node ---")
    idea = state["chosen_idea"]
    brainstorm_type = state["brainstorm_type"]
    llm = state["llm"]
    arxiv_context = state["arxiv_context"]

    if not idea:
        return {"final_plan_text": "No idea chosen for planning."}

    parser = StrOutputParser()
    template = planning_prompts[brainstorm_type]
    prompt = PromptTemplate(
        template=template, input_variables=["title", "description", "arxiv_context"]
    )
    chain = prompt | llm | parser

    try:
        plan_text = await chain.ainvoke(
            {
                "title": idea["title"],
                "description": idea["description"],
                "arxiv_context": arxiv_context,
            }
        )
        final_plan_text = plan_text + "\n\n---\n\n" + arxiv_context

        markdown_plan = final_plan_text
        mermaid_match = re.search(
            r"```mermaid\s*([\s\S]*?)```", final_plan_text, re.DOTALL
        )
        if mermaid_match:
            mermaid_chart = mermaid_match.group(1).strip()
            markdown_plan = final_plan_text.replace(mermaid_match.group(0), "").strip()
            print("\n--- Generated Mermaid Flowchart ---")
            print(
                "Copy the code below and paste it into a Mermaid.js renderer (e.g., https://mermaid.live)"
            )
            print(f"```mermaid\n{mermaid_chart}\n```")

        print(
            f"\n--- Generated {brainstorm_type.replace('_', ' ').title()} Outline ---"
        )
        print(markdown_plan)

        return {"final_plan_text": final_plan_text}
    except Exception as e:
        print(f"❌ Error generating final document: {e}")
        return {"final_plan_text": "Error during plan generation."}
