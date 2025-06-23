# This file contains the conditional logic (routers) for the graph.

from ..state import GraphState


def route_pdf_input(state: GraphState) -> str:
    """Determines the next node based on whether a PDF path was provided."""
    if state.get("pdf_text"):
        return "process_pdf"
    else:
        return "context_generation"


def route_after_plan_feedback(state: GraphState) -> str:
    """Determines the next step after user feedback on the plan."""
    if state.get("user_plan_feedback") == "r":
        return "user_select_idea"
    else:  # approve or anything else
        return "END"


def route_arxiv_search_feedback(state: GraphState) -> str:
    """Determines if using ArXiv search."""
    if state.get("use_arxiv_search"):
        return "arxiv_search"
    else:
        return "implementation_planning"
