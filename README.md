# Multi-Agent Brainstorming System

**[中文版 / Chinese Version](./README-zh.md)**

**Try it now:** [https://lum1104.github.io/agent-brainstorm/](https://lum1104.github.io/agent-brainstorm/)

A client-side AI agent system that runs entirely in your browser, utilizing Google's Gemini API to facilitate structured brainstorming sessions through multiple AI personas.

## Overview

This system implements a 5-stage brainstorming methodology using AI agents to generate, evaluate, and refine ideas for both project development and research papers. The entire process runs locally in your browser with no server-side dependencies.

## Features

### 🤖 Multi-Agent Architecture
- **Preview Agent**: Assembles expert teams with distinct personas
- **RAG Agent**: Provides contextual research and background information
- **Ideation Agents**: Generate diverse ideas from different perspectives
- **Critic Agent**: Evaluates and ranks generated ideas
- **Expert Agent**: Creates detailed implementation plans

### 📋 Two Brainstorming Modes
1. **Project Ideas**: For products, features, and development projects
2. **Research Papers**: For academic topics, studies, and research questions

### 🔄 5-Stage Workflow
1. **Define Direction & Assemble Team**: Configure personas based on your topic
2. **Context via RAG Agent**: Gather relevant background information
3. **Divergent Ideation**: Generate multiple ideas from different perspectives
4. **Convergent Evaluation**: Analyze, cluster, and rank ideas
5. **Final Document Generation**: Create detailed plans for selected ideas

## Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- Google Gemini API Key (free from [Google AI Studio](https://aistudio.google.com/apikey))

### Setup
1. Clone or download this repository
2. Open `index.html` in your web browser
3. Enter your Google Gemini API Key in the settings section
4. Start brainstorming!

### API Key Setup
1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Create a free account if needed
3. Generate an API key
4. Enter the key in the application settings
5. Your key is stored securely in your browser session only

## How to Use

### Step 1: Configuration
- Select your brainstorming type (Project or Research Paper)
- Enter your topic (e.g., "Using LLM for the course project of HCI")
- Click "Start Brainstorm"

### Step 2: Review Expert Team
The Preview Agent will automatically assemble a team of 4 expert personas relevant to your topic, each with:
- **Role**: Their area of expertise
- **Goal**: What they aim to achieve
- **Backstory**: Their professional background

### Step 3: Contextual Research
The RAG Agent provides background information and current state-of-the-art knowledge about your topic.

### Step 4: Idea Generation
Each expert persona generates 5 unique ideas. You can:
- Review all generated ideas
- Uncheck ideas you want to exclude
- Select the most promising concepts

### Step 5: Evaluation & Ranking
The Critic Agent:
- Analyzes and clusters similar ideas
- Evaluates each concept on multiple criteria
- Provides detailed justifications
- Ranks the top 3 recommendations

### Step 6: Implementation Planning
Select one of the top ideas to generate:
- **For Projects**: Implementation plan with requirements, tech stack, timeline, and resources
- **For Research**: Research outline with methodology, literature review, and publication targets

## Example Use Cases

### Project Development
- "Mobile app for university students"
- "AI-powered learning platform"
- "Sustainable energy management system"

### Research Papers
- "Machine learning in healthcare"
- "Human-computer interaction studies"
- "Climate change mitigation strategies"
