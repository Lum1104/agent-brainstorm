# This file defines the core logic for the brainstorming process using LangGraph.

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from .state import GraphState
from .nodes import (
    ask_for_pdf_path_node,
    process_pdf_node,
    context_generation_node,
    persona_generation_node,
    divergent_ideation_node,
    collaborative_discussion_node,
    user_filter_ideas_node,
    red_team_critique_node,
    convergent_evaluation_node,
    user_select_idea_node,
    ask_for_arxiv_search_node,
    arxiv_search_node,
    implementation_planning_node,
    user_feedback_on_plan_node,
    route_pdf_input,
    route_arxiv_search_feedback,
    route_after_plan_feedback,
)


def build_graph(checkpointer: InMemorySaver):
    """Builds the LangGraph agent graph."""
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("ask_for_pdf_path", ask_for_pdf_path_node)
    workflow.add_node("process_pdf", process_pdf_node)
    workflow.add_node("context_generation", context_generation_node)
    workflow.add_node("persona_generation", persona_generation_node)
    workflow.add_node("divergent_ideation", divergent_ideation_node)
    workflow.add_node("collaborative_discussion", collaborative_discussion_node)
    workflow.add_node("user_filter_ideas", user_filter_ideas_node)
    workflow.add_node("red_team_critique", red_team_critique_node)
    workflow.add_node("convergent_evaluation", convergent_evaluation_node)
    workflow.add_node("user_select_idea", user_select_idea_node)
    workflow.add_node("ask_for_arxiv_search", ask_for_arxiv_search_node)
    workflow.add_node("arxiv_search", arxiv_search_node)
    workflow.add_node("implementation_planning", implementation_planning_node)
    workflow.add_node("user_feedback_on_plan", user_feedback_on_plan_node)

    # --- Define edges ---

    # Entry point
    workflow.set_entry_point("ask_for_pdf_path")

    # Conditional edge for PDF processing
    workflow.add_conditional_edges(
        "ask_for_pdf_path",
        route_pdf_input,
        {"process_pdf": "process_pdf", "context_generation": "context_generation"},
    )

    # Main linear flow
    workflow.add_edge("process_pdf", "context_generation")
    workflow.add_edge("context_generation", "persona_generation")
    workflow.add_edge("persona_generation", "divergent_ideation")
    workflow.add_edge("divergent_ideation", "collaborative_discussion")
    workflow.add_edge("collaborative_discussion", "user_filter_ideas")
    workflow.add_edge("user_filter_ideas", "red_team_critique")
    workflow.add_edge("red_team_critique", "convergent_evaluation")
    workflow.add_edge("convergent_evaluation", "user_select_idea")
    workflow.add_edge("user_select_idea", "ask_for_arxiv_search")

    # Conditional edge for ArXiv search
    workflow.add_conditional_edges(
        "ask_for_arxiv_search",
        route_arxiv_search_feedback,
        {
            "arxiv_search": "arxiv_search",
            "implementation_planning": "implementation_planning",
        },
    )

    workflow.add_edge("arxiv_search", "implementation_planning")
    workflow.add_edge("implementation_planning", "user_feedback_on_plan")

    # Conditional edge for the final feedback loop
    workflow.add_conditional_edges(
        "user_feedback_on_plan",
        route_after_plan_feedback,
        {"user_select_idea": "user_select_idea", "END": END},
    )

    # Compile the graph
    app = workflow.compile(checkpointer=checkpointer)
    return app
