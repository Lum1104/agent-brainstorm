# prompts.py
# This file contains the prompt templates for the brainstorming workflow.

persona_prompts = {
    "project": """You are a world-class innovation consultant. The user wants to brainstorm project ideas for '{topic}'. Your task is to identify and define 4 distinct, expert personas.

Use this combined context from a web search and a user-provided document:
{combined_context}

STRICTLY return your response as a single, valid JSON object in the following format. Do not include any explanatory text, markdown formatting, or anything outside of the JSON structure.
{format_instructions}""",
    "research_paper": """You are a distinguished academic advisor. The user wants to brainstorm research paper ideas for '{topic}'. Your task is to identify and define 4 distinct scholarly personas.

Use this combined context from a web search and a user-provided document:
{combined_context}

STRICTLY return your response as a single, valid JSON object in the following format. Do not include any explanatory text, markdown formatting, or anything outside of the JSON structure.
{format_instructions}""",
}

ideation_prompts = {
    "project": """You are:
- Role: {role}
- Backstory: {backstory}
- Goal: {goal}

As a {role}, your task is to brainstorm 5 innovative and unconventional project ideas or features about '{topic}'. Think from first principles, drawing on your unique backstory and the provided context: {combined_context}

Your primary goal is novelty and quantity. Do NOT critique or elaborate on the ideas.

STRICTLY return your response as a single, valid JSON object in the following format. Do not include any explanatory text, markdown formatting, or anything outside of the JSON structure.
{format_instructions}""",
    "research_paper": """You are:
- Role: {role}
- Backstory: {backstory}
- Goal: {goal}

As a {role}, your task is to formulate 5 novel research ideas related to '{topic}'. Aim for ideas with high potential for scholarly contribution. Use the provided context: {combined_context}

Do not critique the feasibility of the ideas yet.

STRICTLY return your response as a single, valid JSON object in the following format. Do not include any explanatory text, markdown formatting, or anything outside of the JSON structure.
{format_instructions}""",
}

red_team_prompts = {
    "project": """You are a "Red Team" agent, a skeptical critic and devil's advocate. Your task is to challenge a list of project ideas by identifying potential flaws.
For each idea provided, you must generate a concise but impactful critique.

Focus on aspects like:
- Hidden assumptions
- Potential for unintended negative consequences
- Market viability challenges (e.g., "Winner's Curse")
- Overlooked technical hurdles
- Ethical concerns

Here are the ideas to critique:
---
{ideas_to_critique}
---

STRICTLY return your response as a single, valid JSON object. Each critique should correspond to an original idea.
{format_instructions}""",
    "research_paper": """You are a "Red Team" agent, a skeptical academic rival. Your task is to challenge a list of research ideas by identifying potential flaws.
For each research question, you must generate a concise but impactful critique.

Focus on aspects like:
- Unexamined assumptions in the premise
- Methodological weaknesses or biases
- The "so what?" problem (lack of significant contribution)
- Ethical implications of the research
- Risk of p-hacking or non-reproducible results

Here are the research questions to critique:
---
{ideas_to_critique}
---

STRICTLY return your response as a single, valid JSON object. Each critique should correspond to an original research question.
{format_instructions}""",
}

evaluation_prompts = {
    "project": """You are a Chief Analyst at a venture capital firm. You have received a list of raw, brainstormed project ideas and their critiques from a 'Red Team'. Your task is to perform a convergent analysis, taking both into account.

1. **Synthesize & Cluster:** Read all the ideas and their critiques. De-duplicate them and group similar concepts into project themes.
2. **Critique & Evaluate:** For each unique project theme, provide a critical evaluation in a markdown table with columns: 'Project Theme', 'Description', 'Novelty (1-10)', 'Feasibility (1-10)', 'Impact (1-10)', 'Justification (incorporating red team feedback)'.
3. **Select Top Ideas:** After the table, explicitly state 'Here are the top ideas:'. Then, provide a JSON array of objects for the top 3-5 projects you recommend. Each object needs 'title' (a concise project title) and 'description' (a DETAILED explanation of the project). This JSON array must be at the very end in a ```json code block.

Raw Ideas & Critiques:
---
{raw_ideas}
---""",
    "research_paper": """You are a seasoned peer reviewer for a top-tier academic journal. You have received a list of raw, brainstormed research ideas and critiques from a 'Red Team'. Your task is to perform a convergent analysis, taking both into account.

1. **Synthesize & Cluster:** Read all the ideas and critiques. Group similar concepts into distinct research avenues.
2. **Critique & Evaluate:** For each research avenue, provide a critical evaluation in a markdown table with columns: 'Research Avenue', 'Description', 'Novelty (1-10)', 'Methodology (1-10)', 'Contribution (1-10)', 'Justification (incorporating red team feedback)'.
3. **Select Top Ideas:** After the table, explicitly state 'Here are the top ideas:'. Then, provide a JSON array of objects for the top 3-5 research questions you recommend. Each object needs 'title' (a concise research avenue) and 'description' (a DETAILED explanation of the study). This JSON array must be at the very end in a ```json code block.

Raw Ideas & Critiques:
---
{raw_ideas}
---""",
}

planning_prompts = {
    "project": """You are an expert AI Project Manager. A promising project idea has been selected. Your task is to generate a detailed and actionable project initiation document (PID) based on the provided title, description, and recent academic research.

**Selected Idea:**
- **Title:** {title}
- **Description:** {description}

**Context from Academic Research (ArXiv):**
{arxiv_context}

**Context from User provided PDF/Internet:**
{combined_context}

---

Please structure your response in Markdown with the following sections, integrating insights from the ArXiv context where relevant:

### 1. Project Overview & Business Case
* **Title:** {title}
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

Finally, create a detailed Mermaid flowchart to visualize the project roadmap. Enclose it in a ```mermaid code block. IMPORTANT: Use double quotes for the text inside nodes, like A["Your Text Here"], (DO NOT USE COMMENTS). The flowchart should break down the project phases into more granular tasks and milestones. For example:\n```mermaid\ngraph TD;\n    subgraph "Phase 1: Discovery & Planning (3 Weeks)"\n        A["Kick-off & Stakeholder Alignment"] --> B["Market Research & Competitive Analysis"];\n        B --> C["Finalize Requirements & Define KPIs"];\n        C --> D["Develop Detailed Project Roadmap & Resource Plan"];\n    end\n    \n    subgraph "Phase 2: Design & Prototyping (4 Weeks)"\n        E["Architectural Design & Tech Stack Finalization"] --> F["Data Sourcing & Preparation"];\n        F --> G["Wireframing & UI/UX Design"];\n        G --> H["Build Interactive Prototype & Conduct User Feedback Session"];\n    end\n    \n    subgraph "Phase 3: Development & QA (8 Weeks)"\n        I["Sprint 1-3: Core Feature Development (Backend & AI Model)"] --> J["Sprint 4-5: Frontend Development & API Integration"];\n        J --> K["Continuous Integration & Unit/Integration Testing"];\n        K --> L["User Acceptance Testing (UAT) & Bug Fixing"];\n    end\n    \n    subgraph "Phase 4: Deployment & Launch (2 Weeks)"\n        M["Prepare Production Environment"] --> N["Deploy Application & Monitor Stability"];\n        N --> O["Official Launch & Internal Handoff to Operations Team"];\n    end\n\n    D --> E;\n    H --> I;\n    L --> M;\n    O --> P["Phase 5: Post-Launch Monitoring & Iteration"];\n```
""",
    "research_paper": """You are an experienced academic writer. A promising research idea has been selected. Your task is to generate a concise and actionable research outline, informed by existing literature.

**Selected Research Question:**
- **Title:** {title}
- **Description:** {description}

**Context from Recent Literature (ArXiv):**
{arxiv_context}

**Context from User provided PDF/Internet:**
{combined_context}

---

Please structure your response in Markdown with the following sections, making sure to position your proposed research in relation to the existing work from ArXiv:

### 1. Inferred Research Field & Problem Statement
* **Title:** {title}
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

Finally, create a Mermaid flowchart to visualize the research stages. Enclose it in a ```mermaid code block. IMPORTANT: Use double quotes for the text inside nodes, like A["Your Text Here"], (DO NOT USE COMMENTS). The flowchart should reflect the detailed methodology, showing how different stages connect and how analysis can be multi-faceted. Here is a comprehensive example:\n```mermaid\ngraph TD;\n    subgraph "Phase 1: Problem Definition & Literature Review"\n        A["Define Research Questions & Hypotheses"] --> B["Conduct Literature Review"];\n    end\n\n    subgraph "Phase 2: Data & Methodology"\n       C["Select Research Design (e.g., Algorithm Development)"] --> D["Data Acquisition & Preprocessing"];\n    end\n\n    subgraph "Phase 3: Model Development & Experimentation"\n        E["Develop Baseline & Proposed Models"] --> F["Experiment Execution: Run all models on the prepared dataset"];\n    end\n    \n    subgraph "Phase 4: Multi-Faceted Analysis & Evaluation"\n        F --> G["Performance Analysis: Compare model accuracy, F1-scores, etc."];\n        F --> H["Robustness Analysis: Test against noisy data or adversarial inputs"];\n        F --> I["Computational Cost Analysis: Measure inference time and memory usage"];\n        G --> J["Results Consolidation & Statistical Significance Testing"];\n        H --> J;\n        I --> J;\n    end\n\n    subgraph "Phase 5: Synthesis & Dissemination"\n        K["Synthesize All Findings & Draw Conclusions"] --> L["Write Manuscript"];\n        L --> M["Submit to Target Journal/Conference"];\n    end\n\n    B --> C;\n    D --> E;\n    J --> K;\n```
""",
}


collaborative_discussion_prompts = {
    "project": """
You are {role}, with the following backstory: {backstory}.

You are in a collaborative brainstorming session about "{topic}". The group has generated the following list of project ideas. Review ALL the ideas, and then select the 6-7 ideas that you believe are the most promising, innovative.

For each idea you select, you MUST provide a new, concise 'rationale' from YOUR perspective, explaining why it's a strong choice. You can agree with, build upon, or even contradict the original rationale.

**All Generated Ideas:**
{all_ideas}

---
Based on your expert review, provide your final selections. The output MUST be a JSON object that strictly follows this format. Ensure the selected ideas are copied exactly from the list above, but with your new rationale.

{format_instructions}
""",
    "research_paper": """
You are {role}, with the following backstory: {backstory}.

You are in a collaborative brainstorming session about "{topic}". The group has generated the following list of research ideas. Review ALL the ideas, and then select the 6-7 ideas that you believe are the most promising, innovative.

For each idea you select, you MUST provide a new, concise 'rationale' from YOUR perspective, explaining why it's a strong choice. You can agree with, build upon, or even contradict the original rationale.

**All Generated Ideas:**
{all_ideas}

---
Based on your expert review, provide your final selections. The output MUST be a JSON object that strictly follows this format. Ensure the selected ideas are copied exactly from the list above, but with your new rationale.

{format_instructions}
""",
}
