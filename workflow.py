# workflow.py
# This file defines the core logic for the brainstorming process.

import json
import re
import asyncio
from typing import List, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun

# Import data structures from the schemas file
from schemas import PersonaList, TopIdeasList

class BrainstormingWorkflow:
    """
    Manages the multi-agent brainstorming process from persona creation to
    implementation planning, using LangChain and Google's Gemini model.
    """
    def __init__(self, api_key: str, brainstorm_type: str = 'project'):
        """
        Initializes the workflow with the user's API key and the type of brainstorm.

        Args:
            api_key: The Google API key for accessing Gemini.
            brainstorm_type: The goal of the brainstorm ('project' or 'research_paper').
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        # Using a more capable model for better structured output and reasoning
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)
        self.raw_ideas_by_persona = []
        self.brainstorm_type = brainstorm_type
        self._initialize_prompts()

    def _initialize_prompts(self):
        """Defines the prompt templates for different brainstorming types."""
        self.persona_prompts = {
            'project': """You are a world-class innovation consultant. The user wants to brainstorm project ideas for '{topic}'.
Your task is to identify and define 4 distinct, expert personas who would be perfect for this topic (e.g., Product Manager, Lead Engineer, Marketing Head, User Advocate).
For each, provide their Role, Goal, and Backstory.

Use the following summary for additional context on the topic:
<context>
{rag_summary}
</context>

{format_instructions}""",
            'research_paper': """You are a distinguished academic advisor. The user wants to brainstorm research paper ideas for '{topic}'.
Your task is to identify and define 4 distinct scholarly personas (e.g., Lead Researcher, Literature Review Specialist, Methodology Expert, Devil's Advocate Scholar).
For each, provide their Role, Goal, and Backstory related to academic research.

Use the following summary for additional context on the topic:
<context>
{rag_summary}
</context>

{format_instructions}"""
        }

        self.ideation_prompts = {
            'project': """Your Persona:
- Role: {role}
- Backstory: {backstory}
- Goal: {goal}

Based on your unique persona, brainstorm 5 innovative project ideas or features about '{topic}'.
Use the following research summary for additional context and inspiration.

Research Summary:
<context>
{rag_summary}
</context>

Your primary goal is quantity and novelty. Do NOT critique or evaluate your own ideas.
Present your ideas as a simple bulleted list in Markdown.""",
            'research_paper': """Your Persona:
- Role: {role}
- Backstory: {backstory}
- Goal: {goal}

Based on your unique scholarly persona, brainstorm 5 innovative research questions, hypotheses, or study designs related to '{topic}'.
Use the following research summary for additional context and inspiration.

Research Summary:
<context>
{rag_summary}
</context>

Your primary goal is novelty and potential for scholarly contribution. Do NOT critique your ideas yet.
Present your ideas as a simple bulleted list in Markdown."""
        }

        # --- UPDATED: Changed from a markdown table to a structured list for better console readability ---
        self.evaluation_prompts = {
            'project': """You are a Chief Analyst at a venture capital firm. You have received a list of raw, brainstormed project ideas. Your task is to perform a convergent analysis.
1. **Synthesize & Cluster:** Read all the ideas. De-duplicate them and group similar concepts into project themes.
2. **Critique & Evaluate:** For each unique project theme, provide a critical evaluation. Present each evaluation with the following clear headings, each on a new line: 'Project Theme', 'Description', 'Novelty (1-10)', 'Feasibility (1-10)', 'Impact (1-10)', and 'Justification'. Separate each theme's evaluation with '---'.
3. **Select Top 3:** After the evaluations, explicitly state 'Here are the top 3 project ideas:'. Then, provide a JSON array of objects for the top 3 projects you recommend. Each object needs 'title' and 'description' keys. This JSON array must be at the very end in a ```json code block.

Raw Ideas:
---
{raw_ideas}
---""",
            'research_paper': """You are a seasoned peer reviewer for a top-tier academic journal. You have received a list of raw, brainstormed research ideas. Your task is to perform a convergent analysis.
1. **Synthesize & Cluster:** Read all the ideas. Group similar concepts into distinct research avenues.
2. **Critique & Evaluate:** For each research avenue, provide a critical evaluation. Present each evaluation with the following clear headings, each on a new line: 'Research Avenue', 'Description', 'Novelty/Originality (1-10)', 'Methodological Soundness (1-10)', 'Potential Contribution (1-10)', and 'Justification'. Separate each avenue's evaluation with '---'.
3. **Select Top 3:** After the evaluations, explicitly state 'Here are the top 3 research ideas:'. Then, provide a JSON array of objects for the top 3 research questions you recommend. Each object needs 'title' (a concise research question) and 'description' (a brief explanation of the study). This JSON array must be at the very end in a ```json code block.

Raw Ideas:
---
{raw_ideas}
---"""
        }
        
        self.planning_prompts = {
            'project': """You are an expert AI Project Manager. A promising idea has been selected. Generate a detailed, concise project initiation document in Markdown.
**Selected Idea:**
- **Title:** {title}
- **Description:** {description}

Please include these sections:
### High-Level Requirements & User Stories
### Proposed Technology Stack
### Phased Project Timeline (with estimated weeks)
### Initial Resource Estimation (roles needed)

Finally, create a Mermaid flowchart to visualize the project timeline. Enclose it in a ```mermaid code block.
IMPORTANT: Use double quotes for the text inside nodes, like A["Your Text Here"].
For example:
```mermaid
graph TD;
    A["Phase 1: Discovery & Research (4 weeks)"] --> B["Phase 2: Design & Prototyping (6 weeks)"];
    B --> C["Phase 3: Development & Testing (8 weeks)"];
    C --> D["Phase 4: Deployment & Launch (2 weeks)"];
```
""",
            'research_paper': """You are an experienced academic writer. A promising research idea has been selected. Generate a concise research paper outline or abstract in Markdown.
**Selected Research Question:**
- **Title:** {title}
- **Description:** {description}

Please include these sections:
### 1. Introduction & Problem Statement
### 2. Preliminary Literature Review
### 3. Proposed Methodology
### 4. Expected Outcomes & Contribution to the Field
### 5. Potential Target Conferences or Journals for Publication

Finally, create a Mermaid flowchart to visualize the research stages. Enclose it in a ```mermaid code block.
IMPORTANT: Use double quotes for the text inside nodes, like A["Your Text Here"].
For example:
```mermaid
graph TD;
    A["Literature Review"] --> B["Formulate Hypothesis"];
    B --> C["Design Experiment"];
    C --> D["Collect & Analyze Data"];
    D --> E["Write Paper"];
```
"""
        }

    async def run_rag_search_and_summary(self, topic: str) -> str:
        """Performs a web search for the topic (RAG) and creates a summary."""
        print(f"\n--- RAG Step: Searching for '{topic}' to provide context ---")
        search = DuckDuckGoSearchRun()
        search_results = search.run(topic)
        print("✅ Web search complete.")
        summarizer_prompt = PromptTemplate.from_template(
            """You are a Research Analyst. Your task is to provide a concise, neutral summary of the following text to be used as context for a brainstorming session. Focus on key concepts, definitions, and the current state of the topic.
            Search Results:\n---\n{search_results}\n---\n\nProvide your summary in a single, dense paragraph."""
        )
        summarizer_chain = summarizer_prompt | self.llm | StrOutputParser()
        try:
            summary = await summarizer_chain.ainvoke({"search_results": search_results})
            print("✅ RAG summary generated.")
            print("\n--- RAG Context Summary ---")
            print(summary)
            return summary
        except Exception as e:
            print(f"❌ Error during RAG summary generation: {e}")
            return "No summary could be generated."

    async def run_preview_agent(self, topic: str, rag_summary: str = "") -> List[Dict[str, Any]]:
        """Generates a team of distinct expert personas for a given topic."""
        print(f"\n--- Stage 1: Assembling Agent Team for '{topic}' ({self.brainstorm_type}) ---")
        parser = JsonOutputParser(pydantic_object=PersonaList)
        template = self.persona_prompts[self.brainstorm_type]
        prompt = PromptTemplate(
            template=template,
            input_variables=["topic", "rag_summary"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        chain = prompt | self.llm | parser
        try:
            response = await chain.ainvoke({"topic": topic, "rag_summary": rag_summary})
            print("✅ Persona team assembled successfully.")
            for p in response['personas']:
                print(f"- Role: {p['role']}\n  Goal: {p['goal']}\n  Backstory: {p['backstory']}\n")
            return response['personas']
        except Exception as e:
            print(f"❌ Error in Preview Agent: {e}")
            return []

    async def run_divergent_ideation(self, topic: str, personas: List[Dict[str, Any]], rag_summary: str = ""):
        """Generates a wide range of ideas from the perspective of each persona."""
        print("\n--- Stage 2: Divergent Ideation (Generating Ideas) ---")
        self.raw_ideas_by_persona = []
        parser = StrOutputParser()
        template = self.ideation_prompts[self.brainstorm_type]
        prompt_template = PromptTemplate.from_template(template)
        chain = prompt_template | self.llm | parser

        async def generate_for_persona(persona):
            try:
                ideas_text = await chain.ainvoke({**persona, "topic": topic, "rag_summary": rag_summary})
                print(f"💡 Ideas generated for {persona['role']}:")
                print(ideas_text)
                self.raw_ideas_by_persona.append({"role": persona['role'], "ideas": ideas_text})
            except Exception as e:
                print(f"❌ Error generating ideas for {persona['role']}: {e}")

        await asyncio.gather(*(generate_for_persona(p) for p in personas))
        print("\n✅ Divergent ideation complete.")

    async def run_convergent_evaluation(self, ideas_to_evaluate: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyzes, critiques, and selects the top ideas from a given list."""
        print("\n--- Stage 3: Convergent Evaluation (Analyzing & Selecting) ---")
        if not ideas_to_evaluate:
            print("⚠️ No ideas to evaluate. Skipping.")
            return {}

        raw_ideas_string = "\n\n---\n\n".join(f"Ideas from {item['role']}:\n{item['ideas']}" for item in ideas_to_evaluate)
        analysis_parser = StrOutputParser()
        template = self.evaluation_prompts[self.brainstorm_type]
        analysis_prompt = PromptTemplate.from_template(template)
        analysis_chain = analysis_prompt | self.llm | analysis_parser
        try:
            full_response = await analysis_chain.ainvoke({"raw_ideas": raw_ideas_string})
            
            # Use regex for robust JSON extraction
            analysis_markdown = full_response
            top_ideas_json = []

            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", full_response, re.DOTALL)
            if json_match:
                json_string = json_match.group(1).strip()
                try:
                    top_ideas_json = json.loads(json_string)
                    # Remove the json block from the markdown for cleaner display
                    analysis_markdown = full_response.replace(json_match.group(0), "").strip()
                except json.JSONDecodeError as e:
                    print(f"❌ Error decoding JSON from evaluation response: {e}")
                    print(f"--- Raw JSON String: ---\n{json_string}")

            print("✅ Convergent evaluation complete.")
            print("\n--- Full Analysis ---")
            print(analysis_markdown)
            
            top_ideas_obj = TopIdeasList(top_ideas=top_ideas_json)
            print("\n--- Top 3 Ideas ---")
            for idea in top_ideas_obj.top_ideas:
                    print(f"- Title: {idea.title}\n  Description: {idea.description}\n")
            return {"analysis_markdown": analysis_markdown, "top_ideas": top_ideas_obj.dict()['top_ideas']}
        except Exception as e:
            print(f"❌ Error during convergent evaluation: {e}")
            return {}

    async def run_implementation_planning(self, idea: Dict[str, str]):
        """Generates a project initiation plan or research outline for a selected idea."""
        print(f"\n--- Stage 4: Final Document Generation for '{idea['title']}' ---")
        parser = StrOutputParser()
        template = self.planning_prompts[self.brainstorm_type]
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.llm | parser
        try:
            plan_text = await chain.ainvoke({"title": idea['title'], "description": idea['description']})
            
            # Parse and display Markdown and Mermaid chart separately
            markdown_plan = plan_text
            mermaid_chart = ""

            mermaid_match = re.search(r"```mermaid\s*([\s\S]*?)```", plan_text, re.DOTALL)
            if mermaid_match:
                mermaid_chart = mermaid_match.group(1).strip()
                markdown_plan = plan_text.replace(mermaid_match.group(0), "").strip()

            print(f"\n--- Generated {self.brainstorm_type.replace('_', ' ').title()} Outline ---")
            print(markdown_plan)

            if mermaid_chart:
                print("\n--- Generated Mermaid Flowchart ---")
                print("Copy the code below and paste it into a Mermaid.js renderer (e.g., https://mermaid.live)")
                print("```mermaid")
                print(mermaid_chart)
                print("```")

            print("\n✅ Final document generated.")
        except Exception as e:
            print(f"❌ Error generating final document: {e}")
