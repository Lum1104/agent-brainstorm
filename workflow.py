# workflow.py
# This file defines the core logic for the brainstorming process.

import json
import re
import asyncio
from typing import List, Dict, Any, Union

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_community.tools import DuckDuckGoSearchRun


from schemas import PersonaList, TopIdeasList, ProjectIdeasList, ResearchIdeasList

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
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key, temperature=0.7)
        self.all_generated_ideas = [] # This will now store structured idea objects
        self.brainstorm_type = brainstorm_type
        self._initialize_prompts()

    def _initialize_prompts(self):
        """
        Loads and defines the prompt templates from the new, more detailed structure.
        These prompts are aligned with the `prompts.js` file.
        """
        self.persona_prompts = {
            'project': """You are a world-class innovation consultant. The user wants to brainstorm project ideas for '{topic}'. Your task is to identify and define 4 distinct, expert personas.

Use this combined context from a web search and a user-provided document:
{combined_context}

STRICTLY return your response as a single, valid JSON object in the following format. Do not include any explanatory text, markdown formatting, or anything outside of the JSON structure.
{format_instructions}""",
            'research_paper': """You are a distinguished academic advisor. The user wants to brainstorm research paper ideas for '{topic}'. Your task is to identify and define 4 distinct scholarly personas.

Use this combined context from a web search and a user-provided document:
{combined_context}

STRICTLY return your response as a single, valid JSON object in the following format. Do not include any explanatory text, markdown formatting, or anything outside of the JSON structure.
{format_instructions}"""
        }

        self.ideation_prompts = {
            'project': """You are:
- Role: {role}
- Backstory: {backstory}
- Goal: {goal}

As a {role}, your task is to brainstorm 5 innovative and unconventional project ideas or features about '{topic}'. Think from first principles, drawing on your unique backstory and the provided context: {combined_context}

Your primary goal is novelty and quantity. Do NOT critique or elaborate on the ideas.

STRICTLY return your response as a single, valid JSON object in the following format. Do not include any explanatory text, markdown formatting, or anything outside of the JSON structure.
{format_instructions}""",
            'research_paper': """You are:
- Role: {role}
- Backstory: {backstory}
- Goal: {goal}

As a {role}, your task is to formulate 5 novel research ideas related to '{topic}'. Aim for ideas with high potential for scholarly contribution. Use the provided context: {combined_context}

Do not critique the feasibility of the ideas yet.

STRICTLY return your response as a single, valid JSON object in the following format. Do not include any explanatory text, markdown formatting, or anything outside of the JSON structure.
{format_instructions}"""
        }

        self.evaluation_prompts = {
            'project': """You are a Chief Analyst at a venture capital firm. You have received a list of raw, brainstormed project ideas. Your task is to perform a convergent analysis.

1. **Synthesize & Cluster:** Read all the ideas. De-duplicate them and group similar concepts into project themes.
2. **Critique & Evaluate:** For each unique project theme, provide a critical evaluation in a markdown table with columns: 'Project Theme', 'Description', 'Novelty (1-10)', 'Feasibility (1-10)', 'Impact (1-10)', 'Justification'.
3. **Select Top Ideas:** After the table, explicitly state 'Here are the top ideas:'. Then, provide a JSON array of objects for the top 3-5 projects you recommend. Each object needs 'title' (a concise project title) and 'description' (a DETAILED explanation of the project). This JSON array must be at the very end in a ```json code block.

Raw Ideas:
---
{raw_ideas}
---""",
            'research_paper': """You are a seasoned peer reviewer for a top-tier academic journal. You have received a list of raw, brainstormed research ideas. Your task is to perform a convergent analysis.

1. **Synthesize & Cluster:** Read all the ideas. Group similar concepts into distinct research avenues.
2. **Critique & Evaluate:** For each research avenue, provide a critical evaluation in a markdown table with columns: 'Research Avenue', 'Description', 'Novelty (1-10)', 'Methodology (1-10)', 'Contribution (1-10)', 'Justification'.
3. **Select Top Ideas:** After the table, explicitly state 'Here are the top ideas:'. Then, provide a JSON array of objects for the top 3-5 research questions you recommend. Each object needs 'title' (a concise research avenue) and 'description' (a DETAILED explanation of the study). This JSON array must be at the very end in a ```json code block.

Raw Ideas:
---
{raw_ideas}
---"""
        }

        self.planning_prompts = {
            'project': """You are an expert AI Project Manager. A promising project idea has been selected. Your task is to generate a detailed and actionable project initiation document (PID) based on the provided title and description.

**Selected Idea:**
- **Title:** {title}
- **Description:** {description}

Please structure your response in Markdown with the following sections:

### 1. Project Overview & Business Case
* **Inferred Business Domain:** Based on the title and description, first identify the specific business domain or industry this project belongs to (e.g., FinTech - Algorithmic Trading, Healthcare - Diagnostic AI, E-commerce - Recommendation Systems).
* **Problem Statement & Opportunity:** Briefly introduce the business problem the project solves or the market opportunity it captures.
* **Project Goals & Objectives:** Clearly articulate the primary business goal and list 2-3 specific, measurable (SMART) objectives for the project.

### 2. Scope, Technology & Execution Plan
* **Project Approach:** Propose a primary project management methodology (e.g., Agile-Scrum, Kanban, Waterfall) and justify its selection.
* **Core Features & Requirements:**
    * **In-Scope Features:** List the high-level features or epics that define the core functionality of the final product.
    * **Proposed Technology Stack:** Recommend a specific technology stack (e.g., Frontend, Backend, Database, AI/ML Libraries, Cloud Infrastructure).
* **Quality Assurance & Success Metrics:**
    * **Testing Strategy:** Outline the methods for ensuring quality (e.g., unit testing, integration testing, user acceptance testing).
    * **Key Performance Indicators (KPIs):** Define clear, quantifiable metrics to evaluate the project's success post-launch (e.g., user engagement, revenue increase, cost reduction, system performance).

### 3. Expected Deliverables & Business Impact
* **Key Project Deliverables:** List the tangible outputs the project will produce (e.g., Deployed production API, interactive user dashboard, technical documentation).
* **Anticipated Business Impact:** Explain how this project, if successful, would contribute to the business. What specific strategic, financial, or operational value would it deliver?
* **Initial Resource Plan:** Estimate the core team roles required to execute the project (e.g., Project Manager, AI/ML Engineer, Backend Developer, UI/UX Designer, QA Analyst).

### 4. Phased Project Roadmap
* Provide a high-level project timeline, broken down into distinct phases with estimated durations in weeks.

Finally, create a detailed Mermaid flowchart to visualize the project roadmap. Enclose it in a ```mermaid code block. IMPORTANT: Use double quotes for the text inside nodes, like A["Your Text Here"].
""",
            'research_paper': """You are an experienced academic writer. A promising research idea has been selected. Your task is to generate a concise and actionable research outline based on the provided title and description.

**Selected Research Question:**
- **Title:** {title}
- **Description:** {description}

Please structure your response in Markdown with the following sections:

### 1. Inferred Research Field & Problem Statement
* **Inferred Field:** Based on the title and description, first identify and state the specific academic field and sub-field this research belongs to (e.g., Computer Science - Natural Language Processing, Sociology - Urban Studies, Bioinformatics, etc.).
* **Problem Context:** Briefly introduce the broader context of the problem.
* **Core Challenge & Objectives:** Clearly articulate the central challenge the research addresses and list 2-3 specific, actionable objectives.

### 2. Detailed Proposed Methodology
* **Research Design:** Propose a primary research design appropriate for the inferred field (e.g., Experimental Study, Quantitative Survey, Qualitative Case Study, Algorithm Development & Benchmarking).
* **Data & Procedures:**
    * **Data Requirements:** Describe the type of data or corpus needed (e.g., a specific dataset, survey responses from a target demographic, textual corpus, patient data).
    * **Execution Steps:** Provide a step-by-step plan for conducting the research, from data acquisition/preparation to execution.
* **Analysis & Evaluation:**
    * **Analysis Techniques:** Suggest specific methods for analyzing the results (e.g., statistical tests like regression analysis, ML model training protocols, thematic analysis of interviews).
    * **Evaluation Metrics:** Define clear metrics to evaluate the success of the outcomes (e.g., model accuracy/F1-score, statistical significance (p-value), improvement over a baseline).

### 3. Expected Outcomes & Contribution
* **Hypothesized Outcomes:** Briefly state the expected findings or results of the research.
* **Contribution to the Field:** Explain how this research, if successful, would contribute to the **inferred academic field**. What specific theoretical or practical advancements would it offer?

### 4. Potential Target Publication Venues
* Based on the **inferred field**, recommend 2-3 highly relevant and reputable academic conferences or journals for publication.

Finally, create a Mermaid flowchart to visualize the research stages. Enclose it in a ```mermaid code block. IMPORTANT: Use double quotes for the text inside nodes, like A["Your Text Here"].
"""
        }

    async def run_context_generation(self, topic: str, pdf_text: str = None) -> str:
        """
        Generates a combined context from a web search and an optional user-provided PDF.
        """
        print(f"\n--- Context Generation: Searching for '{topic}' ---")
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

            print("\n--- Combined Context Summary ---")
            print(combined_context)
            return combined_context
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
            print("✅ Persona team assembled successfully.")
            for p in response['personas']:
                print(f"- Role: {p['Role']}\n  Goal: {p['Goal']}\n  Backstory: {p['Backstory']}\n")
            return response['personas']
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
                # The persona dict from pydantic needs keys to be capitalized
                persona_input = {
                    "role": persona['Role'], 
                    "backstory": persona['Backstory'],
                    "goal": persona['Goal']
                }
                result = await chain.ainvoke({**persona_input, "topic": topic, "combined_context": combined_context})
                
                # Add persona role to each idea object for context
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

        # Format the structured ideas into a readable string for the LLM
        raw_ideas_string = ""
        for item in ideas_to_evaluate:
            summary = f"- (From {item['role']}) "
            if self.brainstorm_type == 'project':
                summary += f"**{item['idea']}**\n"
                summary += f"  - For: {item['target_audience']}\n  - Problem: {item['problem_solved']}\n"
            else: # research_paper
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

            # Robustly find and parse the JSON block
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", full_response, re.DOTALL)
            if json_match:
                json_string = json_match.group(1).strip()
                try:
                    # The prompt asks for a JSON array, so we load it directly
                    parsed_json = json.loads(json_string)
                    # We need to wrap it to match our Pydantic schema
                    top_ideas_obj = TopIdeasList(ideas=parsed_json)
                    top_ideas_list = top_ideas_obj.model_dump()['ideas']
                    analysis_markdown = full_response.replace(json_match.group(0), "").strip()
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"❌ Error decoding or validating JSON from evaluation: {e}")
                    print(f"--- Raw JSON String: ---\n{json_string}")

            print("✅ Convergent evaluation complete.")
            print("\n--- Full Analysis ---")
            print(analysis_markdown)
            
            if top_ideas_list:
                print("\n--- Top Ideas ---")
                for idea in top_ideas_list:
                    print(f"- Title: {idea['title']}\n  Description: {idea['description']}\n")
            
            return {"analysis_markdown": analysis_markdown, "top_ideas": top_ideas_list}

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
