# prompts.py
# This file contains the prompt templates for the brainstorming workflow.

persona_prompts = {
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

ideation_prompts = {
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

evaluation_prompts = {
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

planning_prompts = {
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