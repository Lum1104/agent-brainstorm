# This file contains nodes related to context gathering (PDF, Web, ArXiv).

import pypdf
import datetime
from pathlib import Path
from typing import Dict, Any
from brainstorm.utils.ui import console
import asyncio

from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.document_loaders import ArxivLoader
from langgraph.types import interrupt

from ..state import GraphState


async def ask_for_pdf_path_node(state: GraphState) -> Dict[str, Any]:
    """Interrupts to ask the user for a PDF path or to skip."""
    pdf_path = interrupt(
        {
            "message": "Optional: Enter the full path to a PDF file for context, or press Enter to skip: "
        }
    )
    return {"pdf_text": pdf_path.strip() if pdf_path else None}


async def process_pdf_node(state: GraphState) -> Dict[str, Any]:
    """Extracts text from the PDF path provided in the state."""
    pdf_path = state.get("pdf_text")
    if not pdf_path:
        return {"pdf_text": None}

    if pdf_path.startswith("~"):
        pdf_path = pdf_path.replace("~", str(Path.home()), 1)

    console.print(f"📄 PDF path provided: {pdf_path}")
    console.print(f"\n--- 📄 Processing PDF: {pdf_path} ---", style="bold cyan")
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            pdf_text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    pdf_text += extracted + "\n\n"
        if pdf_text:
            console.print("✅ PDF text successfully extracted.", style="green")
            return {"pdf_text": pdf_text}
        else:
            console.print(
                "⚠️ Could not extract text from PDF. Continuing without it.",
                style="yellow",
            )
            return {"pdf_text": None}
    except FileNotFoundError:
        console.print(
            f"❌ Error: The file '{pdf_path}' was not found. Continuing without it.",
            style="red",
        )
        return {"pdf_text": None}
    except Exception as e:
        console.print(
            f"❌ An error occurred while reading the PDF: {e}. Continuing without it.",
            style="red",
        )
        return {"pdf_text": None}


async def context_generation_node(state: GraphState) -> Dict[str, Any]:
    """
    Generates a combined context from a web search and an optional user-provided PDF.
    """
    console.print("\n--- 🌐 Context Generation Node ---", style="bold cyan")
    topic = state["topic"]
    pdf_text = state.get("pdf_text")
    llm = state["llm"]

    search = DuckDuckGoSearchRun()

    concept_extractor_prompt = PromptTemplate.from_template(
        "You are a research assistant. Your task is to deconstruct the user's topic into a list of 3-5 core, searchable concepts or keywords. "
        "These concepts should be fundamental to understanding the topic. "
        "Return these concepts as a single, comma-separated string. Do not add any preamble or explanation.\n\n"
        "Topic: {topic}\n\n"
        "Keywords:"
    )
    concept_extractor_chain = concept_extractor_prompt | llm | StrOutputParser()

    try:
        # Get the comma-separated list of concepts from the LLM
        concepts_str = await concept_extractor_chain.ainvoke({"topic": topic})
        search_concepts = [
            concept.strip() for concept in concepts_str.split(",") if concept.strip()
        ]
        console.print(
            f"--- 🔍 Identified concepts for search: {search_concepts} ---",
            style="bold",
        )
    except Exception as e:
        console.print(f"❌ Error during concept extraction: {e}", style="red")
        search_concepts = [topic]

    all_search_results = []
    for concept in search_concepts:
        while True:
            try:
                search_results = search.run(concept)
                if search_results:
                    all_search_results.append(search_results)
                    console.print(f"✅ Found results for concept '{concept}'.", style="green")
                else:
                    console.print(f"⚠️ No results found for concept '{concept}'.", style="yellow")
                break
            except Exception as e:
                if "Ratelimit" in str(e):
                    console.print("⚠️ Rate limit reached. Retrying after a short delay...", style="yellow")
                    await asyncio.sleep(3)
                else:
                    console.print(f"❌ Error during concept extraction: {e}", style="red")
                    break

    web_context = "\n\n".join(all_search_results)

    summarizer_prompt = PromptTemplate.from_template(
        "You are a Research Analyst. Your task is to provide a concise, neutral summary of the following text. Focus on key concepts, definitions, and the current state of the topic.\nText:\n---\n{text_to_summarize}\n---\n\nProvide your summary in a single, dense paragraph."
    )
    summarizer_chain = summarizer_prompt | llm | StrOutputParser()

    try:
        web_summary = await summarizer_chain.ainvoke({"text_to_summarize": web_context})
        combined_context = f"**Web Search Summary:**\n{web_summary}"

        if pdf_text:
            pdf_summary = await summarizer_chain.ainvoke(
                {"text_to_summarize": pdf_text}
            )
            combined_context += (
                f"\n\n---\n\n**Uploaded Document Context:**\n{pdf_summary}"
            )

        console.print("\n--- Combined Context Summary ---", style="bold magenta")
        console.print(combined_context)
        return {"combined_context": combined_context}
    except Exception as e:
        console.print(f"❌ Error during context generation: {e}", style="red")
        return {"combined_context": "No summary could be generated."}


async def ask_for_arxiv_search_node(state: GraphState) -> Dict[str, Any]:
    """Interrupts to ask the user if they want to perform an ArXiv search."""
    use_arxiv = interrupt(
        {
            "message": "\nDo you want to include a search for relevant ArXiv papers in the final plan? (Y/n): "
        }
    )
    if use_arxiv.strip().lower() == "y" or not use_arxiv.strip():
        return {"use_arxiv_search": True}
    else:
        return {"use_arxiv_search": False}


async def arxiv_search_node(state: GraphState) -> Dict[str, Any]:
    """Search relevant paper on ArXiv"""
    idea = state["chosen_idea"]
    arxiv_context = "No relevant papers found on ArXiv for this topic."

    if not idea:
        return {"arxiv_context": arxiv_context}

    search_query = idea["title"]

    console.print("\n--- 📚 Searching ArXiv for relevant papers... ---", style="bold cyan")

    try:
        arxiv_loader = ArxivLoader(
            query=search_query, load_max_docs=8, load_all_available_meta=True
        )
        paper_documents = arxiv_loader.get_summaries_as_docs()

        if paper_documents:
            summaries = []
            today = datetime.datetime.now().date()
            for doc in paper_documents:
                published_date = doc.metadata.get("Published")
                if published_date and (today - published_date).days <= 2 * 365:
                    summaries.append(
                        f"**Paper: {doc.metadata.get('Title', 'N/A')}**\nAbstract: {doc.page_content.replace('\n', ' ') or 'N/A'}"
                    )
                else:
                    console.print(
                        f"Skipping paper '{doc.metadata.get('Title', 'N/A')}' published on {published_date} (older than 2 years)",
                        style="yellow",
                    )

            if summaries:
                arxiv_context = (
                    "**Relevant Research from ArXiv:**\n\n"
                    + "\n\n---\n\n".join(summaries)
                )
                console.print(arxiv_context)
    except Exception as e:
        console.print(f"❌ Error during ArXiv search: {e}", style="red")

    return {"arxiv_context": arxiv_context}
