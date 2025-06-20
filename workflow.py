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

# Import data structures and prompts
from schemas import PersonaList, TopIdeasList, ProjectIdeasList, ResearchIdeasList
from prompts import persona_prompts, ideation_prompts, evaluation_prompts, planning_prompts

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
        self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", google_api_key=api_key, temperature=0.7)
        self.brainstorm_type = brainstorm_type
        
        # State variables to store the entire session for export
        self.topic = ""
        self.combined_context = ""
        self.personas = []
        self.all_generated_ideas = []
        self.evaluation_markdown = ""
        self.final_plan_text = ""
        
        self.persona_prompts = persona_prompts
        self.ideation_prompts = ideation_prompts
        self.evaluation_prompts = evaluation_prompts
        self.planning_prompts = planning_prompts


    async def run_context_generation(self, topic: str, pdf_text: str = None) -> str:
        """
        Generates a combined context from a web search and an optional user-provided PDF.
        """
        print(f"\n--- Context Generation: Searching for '{topic}' ---")
        self.topic = topic # Store topic for export
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
            
            self.combined_context = combined_context # Store context for export
            print("\n--- Combined Context Summary ---")
            print(self.combined_context)
            return self.combined_context
        except Exception as e:
            print(f"❌ Error during context generation: {e}")
            return "No summary could be generated."

    async def run_preview_agent(self, topic: str, combined_context: str) -> List[Dict[str, Any]]:
        """Generates a team of distinct expert personas for a given topic."""
        print(f"\n--- Stage 1: Assembling Agent Team for '{topic}' ({self.brainstorm_type}) ---")
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
            self.personas = response['personas'] # Store personas for export
            print("✅ Persona team assembled successfully.")
            for p in self.personas:
                print(f"- Role: {p['Role']}\n  Goal: {p['Goal']}\n  Backstory: {p['Backstory']}\n")
            return self.personas
        except Exception as e:
            print(f"❌ Error in Preview Agent: {e}")
            return []

    async def run_divergent_ideation(self, topic: str, personas: List[Dict[str, Any]], combined_context: str):
        """Generates a wide range of ideas from the perspective of each persona, parsing them as JSON."""
        print("\n--- Stage 2: Divergent Ideation (Generating Ideas in JSON) ---")
        self.all_generated_ideas = []
        
        if self.brainstorm_type == 'project':
            parser = JsonOutputParser(pydantic_object=ProjectIdeasList)
            ideas_key = 'project_ideas'
        else: # research_paper
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

    async def run_convergent_evaluation(self, ideas_to_evaluate: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyzes, critiques, and selects the top ideas from a given list of structured objects."""
        print("\n--- Stage 3: Convergent Evaluation (Analyzing & Selecting) ---")
        if not ideas_to_evaluate:
            print("⚠️ No ideas to evaluate. Skipping.")
            return {}

        raw_ideas_string = ""
        for item in ideas_to_evaluate:
            summary = f"- (From {item['role']}) "
            if self.brainstorm_type == 'project':
                summary += f"**{item['idea']}**\n"
                summary += f"  - For: {item['target_audience']}\n  - Problem: {item['problem_solved']}\n"
            else:
                summary += f"**{item['research_question']}**\n"
                summary += f"  - Methodology: {item['potential_methodology']}\n  - Contribution: {item['potential_contribution']}\n"
            summary += f"  - Rationale: {item['rationale']}\n---\n"
            raw_ideas_string += summary
        
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

            self.evaluation_markdown = analysis_markdown # Store for export
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
        """Generates a project initiation plan or research outline for a selected idea."""
        print(f"\n--- Stage 4: Final Document Generation for '{idea['title']}' ---")
        parser = StrOutputParser()
        template = self.planning_prompts[self.brainstorm_type]
        prompt = PromptTemplate.from_template(template)
        chain = prompt | self.llm | parser
        try:
            plan_text = await chain.ainvoke({"title": idea['title'], "description": idea['description']})
            self.final_plan_text = plan_text # Store full plan for export
            
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
