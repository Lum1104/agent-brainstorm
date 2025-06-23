# This file contains nodes related to context gathering (PDF, Web, ArXiv).

import pypdf
import datetime
from pathlib import Path
from typing import Dict, Any

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

    print(f"📄 PDF path provided: {pdf_path}")
    print(f"\n--- 📄 Processing PDF: {pdf_path} ---")
    try:
        with open(pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            pdf_text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    pdf_text += extracted + "\n\n"
        if pdf_text:
            print("✅ PDF text successfully extracted.")
            return {"pdf_text": pdf_text}
        else:
            print("⚠️ Could not extract text from PDF. Continuing without it.")
            return {"pdf_text": None}
    except FileNotFoundError:
        print(f"❌ Error: The file '{pdf_path}' was not found. Continuing without it.")
        return {"pdf_text": None}
    except Exception as e:
        print(
            f"❌ An error occurred while reading the PDF: {e}. Continuing without it."
        )
        return {"pdf_text": None}


async def context_generation_node(state: GraphState) -> Dict[str, Any]:
    """
    Generates a combined context from a web search and an optional user-provided PDF.
    """
    print("\n--- 🌐 Context Generation Node ---")
    topic = state["topic"]
    pdf_text = state.get("pdf_text")
    llm = state["llm"]

    search = DuckDuckGoSearchRun()
    search_results = search.run(topic)

    summarizer_prompt = PromptTemplate.from_template(
        "You are a Research Analyst. Your task is to provide a concise, neutral summary of the following text. Focus on key concepts, definitions, and the current state of the topic.\nText:\n---\n{text_to_summarize}\n---\n\nProvide your summary in a single, dense paragraph."
    )
    summarizer_chain = summarizer_prompt | llm | StrOutputParser()

    try:
        web_summary = await summarizer_chain.ainvoke(
            {"text_to_summarize": search_results}
        )
        combined_context = f"**Web Search Summary:**\n{web_summary}"

        if pdf_text:
            pdf_summary = await summarizer_chain.ainvoke(
                {"text_to_summarize": pdf_text}
            )
            combined_context += (
                f"\n\n---\n\n**Uploaded Document Context:**\n{pdf_summary}"
            )

        print("\n--- Combined Context Summary ---")
        print(combined_context)
        return {"combined_context": combined_context}
    except Exception as e:
        print(f"❌ Error during context generation: {e}")
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

    print("\n--- 📚 Searching ArXiv for relevant papers... ---")

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
                    print(
                        f"Skipping paper '{doc.metadata.get('Title', 'N/A')}' published on {published_date} (older than 2 years)"
                    )

            if summaries:
                arxiv_context = (
                    "**Relevant Research from ArXiv:**\n\n"
                    + "\n\n---\n\n".join(summaries)
                )
                print(arxiv_context)
    except Exception as e:
        print(f"❌ Error during ArXiv search: {e}")

    return {"arxiv_context": arxiv_context}
