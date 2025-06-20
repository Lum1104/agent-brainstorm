# workflow.py
# This file defines the core logic for the brainstorming process.

import json
import re
import asyncio
import datetime
from ssl import SSLEOFError
from typing import List, Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.document_loaders import ArxivLoader

# Import data structures and prompts
from .schemas import PersonaList, TopIdeasList, ProjectIdeasList, ResearchIdeasList, CritiqueList
from .prompts import persona_prompts, ideation_prompts, evaluation_prompts, planning_prompts, red_team_prompts

class BrainstormingWorkflow:
    """
    Manages the multi-agent brainstorming process from persona creation to
    implementation planning, using LangChain and Google's Gemini model.
    """
    def __init__(self, api_key: str, brainstorm_type: str = 'project'):
        """
        Initializes the workflow with the user's API key and the type of brainstorm.
        """
        if not api_key:
            raise ValueError("API key cannot be empty.")
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.7)
        self.brainstorm_type = brainstorm_type
        
        # State variables to store the entire session for export
        self.topic = ""
        self.combined_context = ""
        self.personas = []
        self.all_generated_ideas = []
        self.critiques = []
        self.evaluation_markdown = ""
        self.final_plan_text = ""
        
        # Prompts are now imported from prompts.py
        self.persona_prompts = persona_prompts
        self.ideation_prompts = ideation_prompts
        self.evaluation_prompts = evaluation_prompts
        self.planning_prompts = planning_prompts
        self.red_team_prompts = red_team_prompts


    async def run_context_generation(self, topic: str, pdf_text: str = None) -> str:
        """
        Generates a combined context from a web search and an optional user-provided PDF.
        """
        print(f"\n--- Stage 1: Context Generation: Searching for '{topic}' ---")
        self.topic = topic 
        search = DuckDuckGoSearchRun()
        search_results = search.run(topic)
        print("✅ Web search complete.")

        summarizer_prompt = PromptTemplate.from_template(
            "You are a Research Analyst. Your task is to provide a concise, neutral summary of the following text. Focus on key concepts, definitions, and the current state of the topic.\nText:\n---\n{text_to_summarize}\n---\n\nProvide your summary in a single, dense paragraph."
        )
        summarizer_chain = summarizer_prompt | self.llm | StrOutputParser()

        try:
            web_summary = await summarizer_chain.ainvoke({"text_to_summarize": search_results})
            combined_context = f"**Web Search Summary:**\n{web_summary}"
            print("✅ Web summary generated.")

            if pdf_text:
                print("\n--- Summarizing PDF content ---")
                pdf_summary = await summarizer_chain.ainvoke({"text_to_summarize": pdf_text})
                combined_context += f"\n\n---\n\n**Uploaded Document Context:**\n{pdf_summary}"
                print("✅ PDF summary generated and combined.")
            
            self.combined_context = combined_context
            print("\n--- Combined Context Summary ---")
            print(self.combined_context)
            return self.combined_context
        except Exception as e:
            print(f"❌ Error during context generation: {e}")
            return "No summary could be generated."

    async def run_preview_agent(self, topic: str, combined_context: str) -> List[Dict[str, Any]]:
        """Generates a team of distinct expert personas for a given topic."""
        print(f"\n--- Stage 2: Assembling Agent Team for '{topic}' ({self.brainstorm_type}) ---")
        parser = JsonOutputParser(pydantic_object=PersonaList)
        template = self.persona_prompts[self.brainstorm_type]
        prompt = PromptTemplate(
            template=template,
            input_variables=["topic", "combined_context"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        chain = prompt | self.llm | parser
        try:
            response = await chain.ainvoke({"topic": topic, "combined_context": combined_context})
            self.personas = response['personas']
            print("✅ Persona team assembled successfully.")
            for p in self.personas:
                print(f"- Role: {p['Role']}\n  Goal: {p['Goal']}\n  Backstory: {p['Backstory']}\n")
            return self.personas
        except Exception as e:
            print(f"❌ Error in Preview Agent: {e}")
            return []

    async def run_divergent_ideation(self, topic: str, personas: List[Dict[str, Any]], combined_context: str):
        """Generates a wide range of ideas from the perspective of each persona, parsing them as JSON."""
        print("\n--- Stage 3: Divergent Ideation (Generating Ideas in JSON) ---")
        self.all_generated_ideas = []
        
        if self.brainstorm_type == 'project':
            parser = JsonOutputParser(pydantic_object=ProjectIdeasList)
            ideas_key = 'project_ideas'
        else:
            parser = JsonOutputParser(pydantic_object=ResearchIdeasList)
            ideas_key = 'research_ideas'
            
        template = self.ideation_prompts[self.brainstorm_type]
        prompt_template = PromptTemplate(
            template=template,
            input_variables=["role", "backstory", "goal", "topic", "combined_context"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        chain = prompt_template | self.llm | parser

        async def generate_for_persona(persona):
            try:
                persona_input = {"role": persona['Role'], "backstory": persona['Backstory'], "goal": persona['Goal']}
                result = await chain.ainvoke({**persona_input, "topic": topic, "combined_context": combined_context})
                
                ideas_with_context = []
                for idea_obj in result[ideas_key]:
                    idea_with_context = idea_obj
                    idea_with_context['role'] = persona['Role']
                    ideas_with_context.append(idea_with_context)

                self.all_generated_ideas.extend(ideas_with_context)
                print(f"✅ Ideas successfully generated and parsed for {persona['Role']}.")
            except Exception as e:
                print(f"❌ Error generating ideas for {persona['Role']}: {e}")

        await asyncio.gather(*(generate_for_persona(p) for p in personas))
        print("\n✅ Divergent ideation complete.")

    async def run_red_team_critique(self, ideas_to_critique: List[Dict[str, Any]]):
        """Runs a 'Red Team' agent to critique a list of ideas."""
        print("\n--- Stage 4: Red Team Critique ---")
        if not ideas_to_critique:
            print("⚠️ No ideas to critique. Skipping.")
            return

        # Format ideas into a string for the prompt
        critique_input_str = ""
        for i, idea in enumerate(ideas_to_critique):
            title = idea.get('idea') or idea.get('research_question', f"Idea {i+1}")
            critique_input_str += f"Idea Title: {title}\n"
            for key, value in idea.items():
                if key not in ['role']: # Don't include the role in the critique prompt, blind critique
                    critique_input_str += f"- {key.replace('_', ' ').title()}: {value}\n"
            critique_input_str += "---\n"

        parser = JsonOutputParser(pydantic_object=CritiqueList)
        template = self.red_team_prompts[self.brainstorm_type]
        prompt = PromptTemplate(
            template=template,
            input_variables=["ideas_to_critique"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        chain = prompt | self.llm | parser

        try:
            response = await chain.ainvoke({"ideas_to_critique": critique_input_str})
            self.critiques = response.get('critiques', [])
            print("✅ Red Team critique complete. The analyst will now consider these critiques.")
            # Display critiques to the user
            for crit in self.critiques:
                print(f"\nCritique for '{crit['idea_title']}':")
                print(f"  - {crit['critique']}")

        except Exception as e:
            print(f"❌ Error during Red Team critique: {e}")
            self.critiques = []


    async def run_convergent_evaluation(self, ideas_to_evaluate: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyzes, critiques, and selects the top ideas from a given list of structured objects."""
        print("\n--- Stage 5: Convergent Evaluation (Analyzing & Selecting) ---")
        if not ideas_to_evaluate:
            print("⚠️ No ideas to evaluate. Skipping.")
            return {}

        # Combine ideas and their critiques for the evaluator
        raw_ideas_string = ""
        for idea in ideas_to_evaluate:
            title = idea.get('idea') or idea.get('research_question', 'Untitled')
            raw_ideas_string += f"### Idea from {idea['role']}: {title}\n"
            for key, value in idea.items():
                 raw_ideas_string += f"- **{key.replace('_', ' ').title()}:** {value}\n"
            
            # Find and add the matching critique, if it exists
            matching_critique = next((c['critique'] for c in self.critiques if c['idea_title'] == title), None)
            if matching_critique:
                raw_ideas_string += f"- **Red Team Critique:** {matching_critique}\n"
            raw_ideas_string += "\n---\n"
        
        parser = StrOutputParser()
        template = self.evaluation_prompts[self.brainstorm_type]
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.llm | parser
        
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

            self.evaluation_markdown = analysis_markdown 
            print("✅ Convergent evaluation complete.")
            print("\n--- Full Analysis ---")
            print(self.evaluation_markdown)
            
            if top_ideas_list:
                print("\n--- Top Ideas ---")
                for idea in top_ideas_list:
                    print(f"- Title: {idea['title']}\n  Description: {idea['description']}\n")
            
            return {"analysis_markdown": self.evaluation_markdown, "top_ideas": top_ideas_list}

        except Exception as e:
            print(f"❌ Error during convergent evaluation: {e}")
            return {}

    async def run_implementation_planning(self, idea: Dict[str, str]):
        """Generates a project initiation plan or research outline for a selected idea, incorporating ArXiv research."""
        print(f"\n--- Stage 6: Final Document Generation for '{idea['title']}' ---")
        
        # search ArXiv for relevant papers for the selected idea
        print("-> Searching ArXiv and loading papers...")
        search_query = idea['title']
        arxiv_context = "No relevant papers found on ArXiv for this topic."

        retries = 3
        for attempt in range(retries):
            try:
                arxiv_loader = ArxivLoader(query=search_query, load_max_docs=8, load_all_available_meta=True)
                paper_documents = arxiv_loader.get_summaries_as_docs()
                
                if paper_documents:
                    print(f"✅ Found {len(paper_documents)} relevant paper(s) on ArXiv. Summarizing...")

                    summaries = []
                    today = datetime.datetime.now().date()

                    for doc in paper_documents:
                        published_date = doc.metadata.get("Published", None)

                        # Skip papers older than 2 years or with no publication date
                        if published_date:
                            if (today - published_date).days > 2 * 365:
                                print(f"Skipping old paper: {doc.metadata.get('Title', 'Unknown')} published on {published_date}")
                                continue
                            print(f"Processing paper: {doc.metadata.get('Title', 'Unknown')} published on {published_date}")
                        else:
                            # Optional: decide if want to include papers
                            print(f"Skipping paper with no publication date: {doc.metadata.get('Title', 'Unknown')}")
                            continue

                        title = doc.metadata.get('Title', 'N/A')
                        if doc.page_content:
                            summary_text = doc.page_content
                        else:
                            summary_text = "No abstract available"
                        summaries.append(f"**Paper: {title}**\nAbstract: {summary_text}")
                    
                    if summaries:
                        arxiv_context = "**Relevant Research from ArXiv:**\n\n" + "\n\n---\n\n".join(summaries)
                        print("✅ Summarization complete.")
                    else:
                        print("-> No recent relevant ArXiv papers found.")

                else:
                    print("-> No relevant ArXiv papers found.")
                break  # Exit loop if successful

            except Exception as e:
                if isinstance(e, ConnectionError) or isinstance(e, TimeoutError) or isinstance(e, SSLEOFError):
                    print(f"⚠️ Attempt {attempt + 1} failed due to connection issues: {e}. Retrying...")
                else:
                    arxiv_context = "No relevant papers found on ArXiv for this topic."
                    print(f"❌ Error during ArXiv processing: {e}")

        parser = StrOutputParser()
        template = self.planning_prompts[self.brainstorm_type]
        prompt = PromptTemplate(
            template=template,
            input_variables=["title", "description", "arxiv_context"]
        )
        chain = prompt | self.llm | parser
        try:
            plan_text = await chain.ainvoke({
                "title": idea['title'], 
                "description": idea['description'],
                "arxiv_context": arxiv_context
            })
            self.final_plan_text = plan_text + "\n\n---\n\n" + arxiv_context
            
            markdown_plan = self.final_plan_text
            mermaid_chart = ""

            mermaid_match = re.search(r"```mermaid\s*([\s\S]*?)```", self.final_plan_text, re.DOTALL)
            if mermaid_match:
                mermaid_chart = mermaid_match.group(1).strip()
                markdown_plan = self.final_plan_text.replace(mermaid_match.group(0), "").strip()

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
