# 🧠 Agent Brainstorm

**[中文版 / Chinese Version](./README-zh.md)**

A multi-agent brainstorming tool powered by AI agents to help you with creative thinking and idea expansion.

## ✨ Project Overview

Agent Brainstorm is a fully client-side multi-agent brainstorming system. Simply enter a brief idea or topic, and the system will automatically assemble an expert team to help you generate innovative ideas and create implementation plans through a structured five-stage process.

## 🚀 Core Features

### 🎯 Intelligent Team Assembly
- **Preview Agent Analysis**: AI analyzes your topic and automatically assembles 4 domain experts
- **Dynamic Role Generation**: Dynamically creates AI agents with different backgrounds and expertise based on topic characteristics

### 💡 Structured Creative Process
1. **Topic Definition & Team Assembly**: Input your idea, AI automatically analyzes and assembles expert team
2. **Divergent Thinking**: Expert agents independently generate innovative ideas
3. **Convergent Evaluation**: Critical analysis and idea clustering
4. **Solution Selection**: Evaluate ideas based on novelty, feasibility, and impact
5. **Implementation Planning**: Generate detailed project implementation plans for selected ideas

### 🛡️ Privacy & Security
- **Client-Side Operation**: All processing happens entirely in your browser
- **API Key Security**: Your Google Gemini API key is only used in local sessions, never uploaded
- **Data Protection**: No registration required, no data collection

## 🔧 Tech Stack

- **Frontend Framework**: Native HTML/CSS/JavaScript
- **UI Styling**: Tailwind CSS
- **Markdown Rendering**: Marked.js
- **AI Model**: Google Gemini 2.0 Flash
- **Typography**: Inter Font Family

## 📋 Prerequisites

### Obtain Google Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in to your Google account
3. Create a new API key
4. Copy the generated key

### System Requirements

- Modern web browser (Chrome, Firefox, Safari, Edge)
- Stable internet connection
- Valid Google Gemini API key

## 🎮 Usage Guide

### Step 1: Configure API Key
1. Open the application
2. Enter your Google Gemini API key in the settings area
3. Click the "Save Key" button

### Step 2: Start Brainstorming
1. Enter your idea or topic in the input field
   - Example: `"Using LLM for Human-Computer Interaction course project"`
2. Click "Assemble Team & Brainstorm"

### Step 3: Observe AI Workflow
1. **Team Assembly**: Watch how AI analyzes your topic and assembles expert team
2. **Idea Generation**: Expert agents sequentially generate innovative ideas
3. **Evaluation & Analysis**: System automatically analyzes, clusters, and evaluates all ideas
4. **Solution Selection**: Choose from the top 3 recommended ideas for detailed planning

### Step 4: Get Implementation Plan
- Click the "Plan" button for any recommended idea
- System generates detailed plans including requirements analysis, tech stack, timeline, and resource assessment

## 🌟 Use Cases

- **Academic Research**: Course projects, thesis topics, research direction exploration
- **Product Development**: New product concepts, feature design, user experience improvement
- **Business Planning**: Business model innovation, market strategy, solution design
- **Technical Innovation**: Technology applications, architecture design, tool development
- **Creative Writing**: Story conception, script writing, content planning

## 📁 Project Structure

```
agent-brainstorm/
├── index.html          # Main application file
├── README.md           # Project documentation (English)
├── README-zh.md        # Project documentation (Chinese)
└── (no other dependencies)
```

## 🎨 Interface Features

- **Responsive Design**: Adapts to desktop and mobile devices
- **Real-time Progress Feedback**: Clear loading states and processing progress
- **Elegant UI Animations**: Smooth transitions and interaction feedback
- **Staged Display**: Progressive revelation of workflow and results

## ⚡ Performance Optimization

- **API Rate Limiting**: Intelligent delays to avoid triggering frequency limits
- **Error Handling**: Comprehensive error catching with user-friendly error messages
- **Content Safety Filtering**: Automatic processing and display of safe content

## 🔒 Security Notes

- API key is only stored in current browser session
- Your key is never sent to any third-party services
- Need to re-enter key after page refresh
- Recommend regular API key rotation

## 🛠️ Local Development

1. Clone or download project files
2. Open `index.html` with a local server (recommended)
   ```bash
   # Using Python
   python -m http.server 8000
   
   # Using Node.js
   npx serve .
   ```
3. Or directly open `index.html` file in browser

## 📝 License

This project is licensed under the MIT License. See project files for details.

## 🤝 Contributing

Welcome to submit issue reports, feature requests, or improvement suggestions!

## 📞 Support

If you encounter problems, please check:
1. Whether API key is correctly set
2. Whether network connection is stable
3. Whether there are error messages in browser console

---

**Start your creative journey!** 🚀
