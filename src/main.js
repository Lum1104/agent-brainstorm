import { prompts } from "./prompts.js";
import { GoogleGenAI } from "https://cdn.jsdelivr.net/npm/@google/genai@1.5.1/+esm";

// --- CONFIGURATION & STATE ---
let userApiKey = null;
let genAI = null; // Instance of the GoogleGenAI SDK
let brainstormType = 'project';
let allParsedIdeas = [];
let chartZoomLevel = 1.0;
let pdfTextContext = '';
let brainstormState = {}; // Central state object for sharing

mermaid.initialize({ startOnLoad: false, theme: 'neutral' });


// --- DOM ELEMENT REFERENCES ---
const apiKeyInput = document.getElementById('api-key-input');
const saveKeyBtn = document.getElementById('save-key-btn');
const keyStatus = document.getElementById('key-status');
const brainstormForm = document.getElementById('brainstorm-form');
const brainstormTypeInput = document.getElementById('brainstorm-type');
const topicInput = document.getElementById('topic-input');
const pdfUploadInput = document.getElementById('pdf-upload');
const pdfStatus = document.getElementById('pdf-status');
const startBtn = document.getElementById('start-btn');
const previewAgentLoader = document.getElementById('preview-agent-loader');
const personaContainer = document.getElementById('persona-container');
const stageRagContainer = document.getElementById('stage-rag-container');
const ragLoader = document.getElementById('rag-loader');
const ragLoaderText = document.getElementById('rag-loader-text');
const ragSummaryContainer = document.getElementById('rag-summary-container');
const stage2Container = document.getElementById('stage-2-container');
const divergentLoader = document.getElementById('divergent-loader');
const ideasContainer = document.getElementById('ideas-container');
const toConvergentBtn = document.getElementById('to-convergent-btn');
const stage3Container = document.getElementById('stage-3-container');
const convergentLoader = document.getElementById('convergent-loader');
const evaluationContainer = document.getElementById('evaluation-container');
const evaluationControls = document.getElementById('evaluation-controls');
const topIdeasContainer = document.getElementById('top-ideas-container');
const stage4Container = document.getElementById('stage-4-container');
const stage4Subtitle = document.getElementById('stage-4-subtitle');
const planningLoader = document.getElementById('planning-loader');
const planningContainer = document.getElementById('planning-container');
const fullscreenModal = document.getElementById('fullscreen-modal');
const fullscreenModalContent = document.getElementById('fullscreen-modal-content');
const closeFullscreenBtn = document.getElementById('close-fullscreen');
const shareExportContainer = document.getElementById('share-export-container');
const exportMdBtn = document.getElementById('export-md-btn');
const modelSelect = document.getElementById('model-select');

// --- GEMINI API HELPER ---
async function callGemini(contents, generationConfig = {}) {
    if (!genAI) {
        alert("Please set your Google API Key in the settings before proceeding.");
        throw new Error("API Key not set.");
    }

    const modelName = modelSelect.value;

    // Add thinking mode config for supported models
    if (modelName.includes('gemini-2.5')) {
        generationConfig.thinkingConfig = { thinkingBudget: -1 };
    }

    try {
        // Get the generative model from the SDK
        const response = await genAI.models.generateContent({
            model: modelName,
            contents: contents,
            config: generationConfig
        });

        // Handle potential errors or empty responses
        if (!response) {
            throw new Error("Received an empty response from the Gemini API.");
        }

        if (response.candidates && response.candidates.length > 0 && response.candidates[0].content) {
            return response;
        } else {
            console.warn("API response missing candidates or content:", response);
            if (response.promptFeedback?.blockReason) {
                throw new Error(`Request was blocked due to: ${response.promptFeedback.blockReason}`);
            }
            if (response.candidates && response.candidates[0]?.finishReason === 'SAFETY') {
                throw new Error("Content blocked by safety settings. Please try a different topic.");
            }
            throw new Error("Received an invalid or empty response from the Gemini API.");
        }
    } catch (error) {
        console.error("Error in callGemini function:", error);
        alert(`An error occurred while communicating with the API. Please check the console for details. Error: ${error.message}`);
        throw error;
    }
}

// --- UI & WORKFLOW LOGIC ---
function updateProgress(currentStage) {
    const progressSteps = document.querySelectorAll('.progress-step');

    progressSteps.forEach((step, index) => {
        const stepNumber = index + 1;
        const stepEl = step.querySelector('.step-number');

        step.classList.remove('completed', 'active', 'pending');
        stepEl.classList.remove('completed', 'active', 'pending');

        if (stepNumber < currentStage) {
            step.classList.add('completed');
            stepEl.classList.add('completed');
            stepEl.textContent = '✓';
        } else if (stepNumber === currentStage) {
            step.classList.add('active');
            stepEl.classList.add('active');
            stepEl.textContent = stepNumber;
        } else {
            step.classList.add('pending');
            stepEl.classList.add('pending');
            stepEl.textContent = stepNumber;
        }
    });
}

function showLoader(loaderElement, text = null) {
    loaderElement.classList.remove('hidden');
    loaderElement.classList.add('flex');
    if (text) {
        const textElement = loaderElement.querySelector('p');
        if (textElement) textElement.textContent = text;
    }
}

function hideLoader(loaderElement) {
    loaderElement.classList.add('hidden');
    loaderElement.classList.remove('flex');
}

function sanitizeHTML(str) {
    const temp = document.createElement('div');
    temp.textContent = str;
    return temp.innerHTML;
}


window.addEventListener('load', () => {
    const storedApiKey = sessionStorage.getItem('gemini-api-key');
    if (storedApiKey) {
        userApiKey = storedApiKey;
        genAI = new GoogleGenAI({ apiKey: userApiKey });
        keyStatus.textContent = "API Key restored from session.";
        keyStatus.classList.remove('hidden');
        startBtn.disabled = false;
        setTimeout(() => keyStatus.classList.add('hidden'), 3000);
    }

    document.querySelectorAll('.progress-step').forEach(step => {
        step.addEventListener('click', () => {
            const stage = parseInt(step.dataset.stage);
            const targetContainer = document.getElementById(`stage-${stage === 1 ? '1' : stage === 2 ? '2' : stage === 3 ? '3' : '4'}-container`);
            if (targetContainer && !targetContainer.classList.contains('hidden')) {
                targetContainer.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
});

saveKeyBtn.addEventListener('click', () => {
    const key = apiKeyInput.value.trim();
    if (key) {
        userApiKey = key;
        genAI = new GoogleGenAI({ apiKey: userApiKey });
        sessionStorage.setItem('gemini-api-key', key); // Save key to session storage
        keyStatus.textContent = "API Key has been set for this session.";
        keyStatus.classList.remove('hidden');
        apiKeyInput.value = '';
        apiKeyInput.type = "password";
        startBtn.disabled = false;
        setTimeout(() => keyStatus.classList.add('hidden'), 3000);
    } else {
        alert("Please enter a valid API key.");
    }
});

pdfUploadInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (!file || file.type !== 'application/pdf') {
        pdfStatus.textContent = 'Please select a PDF file.';
        pdfTextContext = '';
        return;
    }

    pdfStatus.textContent = `Processing "${file.name}"...`;
    pdfTextContext = '';

    try {
        const reader = new FileReader();
        reader.onload = async (e) => {
            const typedarray = new Uint8Array(e.target.result);
            const pdf = await pdfjsLib.getDocument(typedarray).promise;
            let fullText = '';
            for (let i = 1; i <= pdf.numPages; i++) {
                const page = await pdf.getPage(i);
                const textContent = await page.getTextContent();
                const pageText = textContent.items.map(item => item.str).join(' ');
                fullText += pageText + '\n\n';
            }
            pdfTextContext = fullText;
            pdfStatus.textContent = `Successfully extracted text from "${file.name}".`;
        };
        reader.readAsArrayBuffer(file);
    } catch (error) {
        console.error('Error processing PDF:', error);
        pdfStatus.textContent = 'Failed to process PDF. Please try another file.';
        pdfTextContext = '';
    }
});


brainstormForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!userApiKey) {
        alert("Please save your API key first!");
        return;
    }
    const topic = topicInput.value.trim();
    if (!topic) {
        alert('Please enter a topic to brainstorm.');
        return;
    }
    brainstormType = brainstormTypeInput.value;

    // --- Reset UI for a new run ---
    [stageRagContainer, stage2Container, stage3Container, stage4Container, shareExportContainer].forEach(el => el.classList.add('hidden'));
    [personaContainer, ragSummaryContainer, ideasContainer, evaluationContainer, topIdeasContainer, planningContainer].forEach(el => el.innerHTML = '');
    toConvergentBtn.classList.add('hidden');
    evaluationControls.classList.add('hidden');
    allParsedIdeas = [];
    startBtn.disabled = true;

    // Initialize state object for this run
    brainstormState = {
        topic: topic,
        type: brainstormType,
        pdfStatus: pdfStatus.textContent
    };

    updateProgress(1);

    const combinedContext = await runRagAndCombineContext(topic, pdfTextContext);
    brainstormState.combinedContext = combinedContext;

    if (combinedContext && combinedContext !== "Could not generate context.") {
        const personas = await runPreviewAgent(topic, combinedContext);
        if (personas && personas.length > 0) {
            brainstormState.personas = personas;
            await runDivergentIdeation(topic, personas, combinedContext);
        }
    }
    startBtn.disabled = false;
});

async function runPreviewAgent(topic, combinedContext) {
    showLoader(previewAgentLoader);
    personaContainer.innerHTML = '';

    const prompt = prompts.persona[brainstormType]
        .replace('{topic}', sanitizeHTML(topic))
        .replace('{combined_context}', combinedContext);

    // Define a variable to hold the raw text for logging in case of an error
    let rawResponseText = "";

    try {
        const response = await callGemini([{ role: "user", parts: [{ text: prompt }] }]);
        rawResponseText = response.candidates[0].content.parts[0].text;

        const jsonRegex = /```json\s*([\s\S]*?)\s*```/;
        const match = rawResponseText.match(jsonRegex);

        const jsonString = match ? match[1] : rawResponseText;

        const personaData = JSON.parse(jsonString);

        hideLoader(previewAgentLoader);
        stage2Container.classList.remove('hidden');
        personaData.personas.forEach(p => renderPersonaCard(p));
        return personaData.personas;

    } catch (error) {
        hideLoader(previewAgentLoader);
        personaContainer.innerHTML = `<p class="text-red-500 text-center col-span-full">Error: Could not parse the agent team data.</p>`;
        console.error("Error in runPreviewAgent:", error);
        // Log the actual text that failed to parse for easier debugging
        console.error("Failed to parse the following text:", rawResponseText);
        return null;
    }
}

function renderPersonaCard(persona) {
    const card = document.createElement('div');
    card.className = 'agent-card bg-white p-4 rounded-lg border';
    card.innerHTML = `<h3 class="font-bold text-blue-600">${sanitizeHTML(persona.Role)}</h3><p class="text-sm text-gray-500 mt-1"><strong>Goal:</strong> ${sanitizeHTML(persona.Goal)}</p><p class="text-sm text-gray-500 mt-1"><strong>Backstory:</strong> ${sanitizeHTML(persona.Backstory)}</p>`;
    personaContainer.appendChild(card);
}

async function duckDuckGoSearch(query) {
    const proxyUrls = [
        'https://api.allorigins.win/raw?url=', // Primary proxy
        'https://corsproxy.io/?url='           // Backup proxy
    ];
    const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;

    for (const proxyUrl of proxyUrls) {
        try {
            // console.log(`Attempting search with proxy: ${proxyUrl}`);
            const response = await fetch(proxyUrl + searchUrl);

            if (!response.ok) {
                throw new Error(`Network response was not ok. Status: ${response.status}`);
            }

            const htmlText = await response.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(htmlText, 'text/html');

            const snippets = [];
            const snippetNodes = doc.querySelectorAll('.result__snippet');

            if (snippetNodes.length === 0) {
                throw new Error("Proxy returned no valid search snippets.");
            }

            snippetNodes.forEach(node => {
                snippets.push(node.innerText.trim());
            });

            // console.log(`Successfully fetched results with: ${proxyUrl}`);
            return snippets.join('\n\n');

        } catch (error) {
            console.warn(`Proxy failed: ${proxyUrl}`, error.message);
        }
    }

    console.error("All proxies failed.");
    throw new Error("Failed to retrieve search results after trying all backup proxies.");
}


async function runRagAndCombineContext(topic, pdfContent) {
    stageRagContainer.classList.remove('hidden');
    showLoader(ragLoader, 'Research Agent is performing a web search via DuckDuckGo...');
    ragSummaryContainer.innerHTML = '';

    try {
        const searchResults = await duckDuckGoSearch(topic);
        ragLoaderText.textContent = 'Web search complete. Summarizing results...';
        const summarizerPromptText = prompts.rag_summary.replace('{search_results}', searchResults);
        const response = await callGemini([{ role: "user", parts: [{ text: summarizerPromptText }] }]);
        const webSummaryText = response.candidates[0].content.parts[0].text;

        let combinedContext = `**Web Search Summary:**\n${webSummaryText}`;
        if (pdfContent) {
            const pdfSummaryPrompt = prompts.pdf.replace('{pdf_content}', pdfContent);
            const pdf_response = await callGemini([{ role: "user", parts: [{ text: pdfSummaryPrompt }] }]);
            const pdfSummaryText = pdf_response.candidates[0].content.parts[0].text;
            combinedContext += `\n\n---\n\n**Uploaded Document Context:**\n${pdfSummaryText}`;
        }

        ragSummaryContainer.innerHTML = marked.parse(combinedContext);
        hideLoader(ragLoader);
        return combinedContext;

    } catch (error) {
        console.error("Error in RAG process:", error);
        hideLoader(ragLoader);
        ragSummaryContainer.innerHTML = `<p class="text-red-500">Error during context generation: ${error.message}</p>`;
        return "Could not generate context.";
    }
}


async function runDivergentIdeation(topic, personas, combinedContext) {
    updateProgress(2);
    showLoader(divergentLoader);
    ideasContainer.innerHTML = '';
    allParsedIdeas = [];
    const RATE_LIMIT_DELAY = 1000;
    let ideaCounter = 0;
    brainstormState.ideationOutputs = {}; // Store raw outputs

    for (const persona of personas) {
        const prompt = prompts.ideation[brainstormType]
            .replace('{role}', persona.Role)
            .replace('{backstory}', persona.Backstory)
            .replace('{goal}', persona.Goal)
            .replace('{topic}', sanitizeHTML(topic))
            .replace('{combined_context}', combinedContext);

        let rawResponseText = "";

        try {
            const response = await callGemini([{ role: "user", parts: [{ text: prompt }] }]);
            rawResponseText = response.candidates[0].content.parts[0].text;


            // 1. PARSE: Safely parse the JSON response from the model
            const jsonRegex = /```json\s*([\s\S]*?)\s*```/;
            const match = rawResponseText.match(jsonRegex);
            const jsonString = match ? match[1] : rawResponseText;
            const ideasData = JSON.parse(jsonString);

            const ideasKey = brainstormType === 'project' ? 'project_ideas' : 'research_ideas';
            const ideasArray = ideasData[ideasKey];

            if (!ideasArray || !Array.isArray(ideasArray)) {
                throw new Error(`Parsed JSON from ${persona.Role} does not contain a valid '${ideasKey}' array.`);
            }

            let reconstructedMarkdown = "";
            if (brainstormType === 'project') {
                reconstructedMarkdown = ideasArray.map(idea =>
                    `- **Idea:** ${sanitizeHTML(idea.idea || '')}\n- **Target Audience:** ${sanitizeHTML(idea.target_audience || '')}\n- **Problem Solved:** ${sanitizeHTML(idea.problem_solved || '')}\n- **My Rationale:** ${sanitizeHTML(idea.rationale || '')}`
                ).join('\n\n<hr class="my-3">\n\n'); // Use an <hr> for clear visual separation
            } else { // research_paper
                reconstructedMarkdown = ideasArray.map(idea =>
                    `- **Research Question:** ${sanitizeHTML(idea.research_question || '')}\n- **Potential Methodology:** ${sanitizeHTML(idea.potential_methodology || '')}\n- **Potential Contribution:** ${sanitizeHTML(idea.potential_contribution || '')}\n- **My Rationale:** ${sanitizeHTML(idea.rationale || '')}`
                ).join('\n\n<hr class="my-3">\n\n');
            }

            brainstormState.ideationOutputs[persona.Role] = reconstructedMarkdown; // Save for restoration

            const startingIdeaCounter = ideaCounter;
            const ideasWithContext = ideasArray.map(idea => ({
                ...idea,
                persona: persona,
                id: `idea-${ideaCounter++}`
            }));
            allParsedIdeas.push(...ideasWithContext);

            renderIdeationBlock(persona, reconstructedMarkdown, startingIdeaCounter);

        } catch (error) {
            console.error("Error in runDivergentIdeation for persona " + persona.Role, error);
            console.error("Failed to parse or process the following text:", rawResponseText);
            const errorCard = document.createElement('div');
            errorCard.className = 'agent-card bg-white p-4 rounded-lg border';
            errorCard.innerHTML = `<h3 class="font-bold text-blue-600 mb-2">${sanitizeHTML(persona.Role)}</h3><p class="text-red-500 p-2 text-center">Error parsing ideas.</p>`;
            ideasContainer.appendChild(errorCard);
        }
        await new Promise(resolve => setTimeout(resolve, RATE_LIMIT_DELAY));
    }

    hideLoader(divergentLoader);
    if (allParsedIdeas.length > 0) {
        toConvergentBtn.classList.remove('hidden');
    }
}

function renderIdeationBlock(persona, ideasText, ideaCounterStart) {
    let ideaCounter = ideaCounterStart;
    const personaIdeasContainer = document.createElement('div');
    personaIdeasContainer.className = 'agent-card bg-white p-4 rounded-lg border';
    personaIdeasContainer.innerHTML = `<h3 class="font-bold text-blue-600 mb-2">${sanitizeHTML(persona.Role)}</h3>`;

    const ideaBlockRegex = /- \*\*(Idea|Research Question):\*\*([\s\S]*?)(?=- \*\*(Idea|Research Question):\*\*|$)/g;
    const matches = [...ideasText.matchAll(ideaBlockRegex)];

    if (matches.length === 0) {
        personaIdeasContainer.innerHTML += `<p class="text-gray-500 italic">This agent did not generate any ideas in the correct format.</p>`;
        console.log(ideasText); // Debugging output
    }

    for (const match of matches) {
        const block = match[0];
        // Match title which is mandatory
        const ideaTitleMatch = block.match(/- \*\*(?:Idea|Research Question):\*\*\s*(.*?)(?:\n|$)/);

        if (!ideaTitleMatch || !ideaTitleMatch[1].trim()) {
            console.warn(`[${persona.Role}] Skipped block due to missing title. Content:`, block);
            continue; // Skip this block if it doesn't even have a title
        }
        const title = ideaTitleMatch[1].trim();

        let ideaData = { title: title };

        // Optional fields, grab them if they exist. Use N/A if not found.
        const rationaleMatch = block.match(/- \*\*My Rationale:\*\*\s*(.*)/s);
        ideaData.rationale = rationaleMatch ? rationaleMatch[1].trim() : 'N/A';

        if (brainstormType === 'project') {
            const targetAudienceMatch = block.match(/- \*\*Target Audience:\*\*\s*(.*?)(?:\n|$)/);
            const problemSolvedMatch = block.match(/- \*\*Problem Solved:\*\*\s*(.*?)(?:\n|$)/);
            ideaData.targetAudience = targetAudienceMatch ? targetAudienceMatch[1].trim() : 'N/A';
            ideaData.problemSolved = problemSolvedMatch ? problemSolvedMatch[1].trim() : 'N/A';
        } else { // research_paper
            const methodologyMatch = block.match(/- \*\*Potential Methodology:\*\*\s*(.*?)(?:\n|$)/);
            const contributionMatch = block.match(/- \*\*Potential Contribution:\*\*\s*(.*?)(?:\n|$)/);
            ideaData.potentialMethodology = methodologyMatch ? methodologyMatch[1].trim() : 'N/A';
            ideaData.potentialContribution = contributionMatch ? contributionMatch[1].trim() : 'N/A';
        }

        const ideaId = `idea-${ideaCounter++}`;
        allParsedIdeas.push({ role: persona.Role, idea: ideaData, id: ideaId });

        const checkboxContainer = document.createElement('div');
        checkboxContainer.className = 'flex items-start gap-3 p-3 rounded-md hover:bg-gray-50 border-b';
        const ideaDataString = JSON.stringify(ideaData);

        let displayHTML = `<label for="${ideaId}" class="font-semibold text-gray-800">${sanitizeHTML(ideaData.title)}</label><div class="text-sm text-gray-600 pl-2">`;
        if (brainstormType === 'project') {
            displayHTML += `<p class="mt-1"><strong class="text-gray-700">For:</strong> ${sanitizeHTML(ideaData.targetAudience)}</p><p class="mt-1"><strong class="text-gray-700">Problem:</strong> ${sanitizeHTML(ideaData.problemSolved)}</p>`;
        } else {
            displayHTML += `<p class="mt-1"><strong class="text-gray-700">Methodology:</strong> ${sanitizeHTML(ideaData.potentialMethodology)}</p><p class="mt-1"><strong class="text-gray-700">Contribution:</strong> ${sanitizeHTML(ideaData.potentialContribution)}</p>`;
        }
        displayHTML += `<p class="mt-1"><strong class="text-gray-700">Rationale:</strong> <em class="text-gray-500">${sanitizeHTML(ideaData.rationale)}</em></p></div>`;

        checkboxContainer.innerHTML = `<input type="checkbox" id="${ideaId}" data-idea='${sanitizeHTML(ideaDataString)}' checked class="mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500 shrink-0"><div>${displayHTML}</div>`;
        personaIdeasContainer.appendChild(checkboxContainer);
    }
    ideasContainer.appendChild(personaIdeasContainer);
}

toConvergentBtn.addEventListener('click', () => {
    updateProgress(3);
    const selectedIdeaIds = Array.from(ideasContainer.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.id);
    if (selectedIdeaIds.length === 0) {
        alert("Please select at least one idea to proceed.");
        return;
    }

    brainstormState.selectedIdeaIds = selectedIdeaIds; // Save for restoration

    const selectedIdeas = allParsedIdeas.filter(parsedIdea => selectedIdeaIds.includes(parsedIdea.id));
    const rawIdeasString = selectedIdeas.map(item => {
        const ideaObj = item.idea;
        let summary = `- (From ${item.role}) **${ideaObj.title}**\n`;
        if (brainstormType === 'project') {
            summary += `  - **For:** ${ideaObj.targetAudience}\n  - **Problem:** ${ideaObj.problemSolved}\n`;
        } else {
            summary += `  - **Methodology:** ${ideaObj.potentialMethodology}\n  - **Contribution:** ${ideaObj.potentialContribution}\n`;
        }
        summary += `  - **Rationale:** ${ideaObj.rationale}`;
        return summary;
    }).join('\n\n---\n\n');

    stage3Container.classList.remove('hidden');
    window.scrollTo({ top: stage3Container.offsetTop, behavior: 'smooth' });
    toConvergentBtn.classList.add('hidden');
    runConvergentEvaluation(rawIdeasString);
});

async function runConvergentEvaluation(rawIdeasString) {
    showLoader(convergentLoader);
    evaluationContainer.innerHTML = '';
    topIdeasContainer.innerHTML = '';
    evaluationControls.classList.add('hidden');
    brainstormState.rawIdeasForEvaluation = rawIdeasString;

    const prompt = prompts.evaluation[brainstormType].replace('{raw_ideas}', rawIdeasString);

    try {
        const response = await callGemini([{ role: "user", parts: [{ text: prompt }] }]);
        const evaluationText = response.candidates[0].content.parts[0].text;
        brainstormState.evaluationOutput = evaluationText; // Save for restoration
        renderConvergentEvaluation(evaluationText);
    } catch (error) {
        console.error("Error in runConvergentEvaluation:", error);
        evaluationContainer.innerHTML = `<p class="text-red-500">Error during evaluation: ${error.message}</p>`;
    } finally {
        hideLoader(convergentLoader);
    }
}

function renderConvergentEvaluation(evaluationText) {
    const jsonMatch = evaluationText.match(/```json\s*([\s\S]*?)\s*```/);
    let topIdeas = [];
    let evaluationMarkdown = evaluationText;

    if (jsonMatch && jsonMatch[1]) {
        try {
            topIdeas = JSON.parse(jsonMatch[1]);
            evaluationMarkdown = evaluationText.replace(jsonMatch[0], '').replace(/\s*\(\d+-\d+\)/g, '').trim();
        } catch (e) {
            console.error("Failed to parse top ideas JSON:", e);
        }
    }

    const parsedHTML = marked.parse(evaluationMarkdown);

    const tableRegex = /(<table[\s\S]*?<\/table>)/gi;
    const parts = parsedHTML.split(tableRegex);

    let finalHTML = '';
    let hasCollapsibleContent = false;

    for (let i = 0; i < parts.length; i++) {
        if (parts[i].match(tableRegex)) {
            finalHTML += `
                        <div class="mb-4 flex flex-wrap gap-2">
                            <button class="table-toggle-btn text-sm bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-lg">
                                Show the Evaluation Table
                            </button>
                            <button class="table-expand-all-btn text-sm bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded-lg" style="display: none;">
                                Expand All
                            </button>
                            <button class="table-collapse-all-btn text-sm bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded-lg" style="display: none;">
                                Collapse All
                            </button>
                        </div>
                        <div class="evaluation-table-wrapper hidden">${parts[i]}</div>
                    `;
        } else {
            finalHTML += parts[i];
        }
    }

    evaluationContainer.innerHTML = finalHTML;

    const tableToggleBtns = evaluationContainer.querySelectorAll('.table-toggle-btn');
    const tableExpandAllBtns = evaluationContainer.querySelectorAll('.table-expand-all-btn');
    const tableCollapseAllBtns = evaluationContainer.querySelectorAll('.table-collapse-all-btn');

    tableToggleBtns.forEach((btn, index) => {
        btn.addEventListener('click', () => {
            const tableWrapper = btn.parentElement.nextElementSibling;
            const expandBtn = tableExpandAllBtns[index];
            const collapseBtn = tableCollapseAllBtns[index];

            if (tableWrapper && tableWrapper.classList.contains('evaluation-table-wrapper')) {
                const isHidden = tableWrapper.classList.toggle('hidden');
                btn.textContent = isHidden ? 'Show the Evaluation Table' : 'Hide the Evaluation Table';

                if (isHidden) {
                    expandBtn.style.display = 'none';
                    collapseBtn.style.display = 'none';
                } else {
                    const hasCollapsible = tableWrapper.querySelectorAll('.collapsible-content').length > 0;
                    if (hasCollapsible) {
                        expandBtn.style.display = 'inline-block';
                        collapseBtn.style.display = 'inline-block';
                    }
                }
            }
        });
    });

    tableExpandAllBtns.forEach((btn, index) => {
        btn.addEventListener('click', () => {
            const tableWrapper = btn.parentElement.nextElementSibling;
            if (tableWrapper) {
                tableWrapper.querySelectorAll('.collapsible-content').forEach(content => {
                    content.classList.remove('collapsed');
                    content.nextElementSibling.textContent = 'Show less';
                });
            }
        });
    });

    tableCollapseAllBtns.forEach((btn, index) => {
        btn.addEventListener('click', () => {
            const tableWrapper = btn.parentElement.nextElementSibling;
            if (tableWrapper) {
                tableWrapper.querySelectorAll('.collapsible-content').forEach(content => {
                    content.classList.add('collapsed');
                    content.nextElementSibling.textContent = 'Read more';
                });
            }
        });
    });

    makeTableCellsCollapsible();

    if (topIdeas.length > 0) {
        const header = document.createElement('h3');
        header.className = 'text-xl font-semibold text-gray-700 stage-title';
        header.textContent = 'Select a Top Idea to Plan';
        topIdeasContainer.appendChild(header);
        const listContainer = document.createElement('div');
        listContainer.className = 'flex flex-col sm:flex-row gap-4 mt-4';
        topIdeas.forEach(idea => {
            const planBtn = document.createElement('button');
            planBtn.className = 'bg-purple-600 text-white font-semibold py-2 px-4 rounded-lg hover:bg-purple-700 transition-all duration-200 text-left';
            planBtn.innerHTML = `<span class="font-bold">Plan:</span> ${sanitizeHTML(idea.title)}`;
            planBtn.onclick = () => runImplementationPlanning(idea);
            listContainer.appendChild(planBtn);
        });
        topIdeasContainer.appendChild(listContainer);
    }
}

function makeTableCellsCollapsible() {
    const cells = evaluationContainer.querySelectorAll('table td');
    const CHARACTER_THRESHOLD = 50; // Collapse if content is longer than this
    let collapsibleFound = false;

    cells.forEach(cell => {
        if (cell.textContent.length > CHARACTER_THRESHOLD) {
            collapsibleFound = true;
            const originalContent = cell.innerHTML;
            cell.innerHTML = `
                        <div class="collapsible-wrapper">
                            <div class="collapsible-content collapsed">${originalContent}</div>
                            <button class="toggle-expand">Read more</button>
                        </div>
                    `;
        }
    });

    if (collapsibleFound) {
        evaluationControls.classList.remove('hidden');
        evaluationControls.classList.add('flex');
    } else {
        evaluationControls.classList.add('hidden');
    }
}

evaluationContainer.addEventListener('click', (e) => {
    if (e.target.classList.contains('toggle-expand')) {
        const button = e.target;
        const contentWrapper = button.previousElementSibling;
        contentWrapper.classList.toggle('collapsed');
        button.textContent = contentWrapper.classList.contains('collapsed') ? 'Read more' : 'Show less';
    }
});

async function runImplementationPlanning(idea) {
    updateProgress(4);
    stage4Container.classList.remove('hidden');
    stage4Subtitle.textContent = `The AI expert has generated a high-level ${brainstormType === 'project' ? 'implementation plan' : 'research outline'} for the selected idea.`;
    window.scrollTo({ top: stage4Container.offsetTop, behavior: 'smooth' });
    showLoader(planningLoader);
    planningContainer.innerHTML = '';

    brainstormState.finalSelectedIdea = idea; // Save for restoration
    const prompt = prompts.planning[brainstormType]
        .replace('{title}', sanitizeHTML(idea.title))
        .replace('{description}', sanitizeHTML(idea.description));

    try {
        const response = await callGemini([{ role: "user", parts: [{ text: prompt }] }]);
        let planText = response.candidates[0].content.parts[0].text;
        brainstormState.finalPlanOutput = planText; // Save for restoration
        renderImplementationPlan(planText);
        shareExportContainer.classList.remove('hidden');
        shareExportContainer.classList.add('flex');
        updateProgress(5);
    } catch (error) {
        console.error("Error in runImplementationPlanning:", error);
        planningContainer.innerHTML = `<p class="text-red-500">Error generating the final document: ${error.message}</p>`;
    } finally {
        hideLoader(planningLoader);
    }
}

async function renderImplementationPlan(planText) {
    planningContainer.innerHTML = '';
    chartZoomLevel = 1.0;
    const mermaidRegex = /```mermaid\s*([\s\S]*?)```/;
    const mermaidMatch = planText.match(mermaidRegex);
    const markdownContent = planText.replace(mermaidRegex, '').replace(/^```markdown\s*|```\s*$/g, '').trim();
    planningContainer.innerHTML = marked.parse(markdownContent);

    if (mermaidMatch && mermaidMatch[1]) {
        const mermaidCode = mermaidMatch[1].trim();
        const chartWrapper = document.createElement('div');
        chartWrapper.className = 'mt-6';
        chartWrapper.innerHTML = `
                    <div id="chart-controls">
                        <button id="zoom-in-btn" class="text-sm bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-1 px-3 rounded-lg">Zoom In</button>
                        <button id="zoom-out-btn" class="text-sm bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-1 px-3 rounded-lg">Zoom Out</button>
                        <button id="reset-zoom-btn" class="text-sm bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-1 px-3 rounded-lg">Reset</button>
                        <button id="fullscreen-btn" class="text-sm bg-blue-500 hover:bg-blue-600 text-white font-semibold py-1 px-3 rounded-lg ml-auto">Fullscreen</button>
                    </div>`;
        const chartContainer = document.createElement('div');
        chartContainer.id = 'chart-container';
        const mermaidDiv = document.createElement('div');
        mermaidDiv.className = 'mermaid';
        chartContainer.appendChild(mermaidDiv);
        chartWrapper.appendChild(chartContainer);
        planningContainer.appendChild(chartWrapper);

        try {
            const { svg } = await mermaid.render(`mermaid-diag-${Date.now()}`, mermaidCode);
            mermaidDiv.innerHTML = svg;
            const svgElement = mermaidDiv.querySelector('svg');

            const updateZoom = () => { svgElement.style.transform = `scale(${chartZoomLevel})`; };
            chartWrapper.querySelector('#zoom-in-btn').onclick = () => { chartZoomLevel += 0.1; updateZoom(); };
            chartWrapper.querySelector('#zoom-out-btn').onclick = () => { chartZoomLevel = Math.max(0.1, chartZoomLevel - 0.1); updateZoom(); };
            chartWrapper.querySelector('#reset-zoom-btn').onclick = () => { chartZoomLevel = 1.0; updateZoom(); };
            chartWrapper.querySelector('#fullscreen-btn').onclick = () => {
                fullscreenModalContent.innerHTML = '';
                const clonedSvg = svgElement.cloneNode(true);
                clonedSvg.style.transform = '';
                clonedSvg.style.maxWidth = '95vw';
                clonedSvg.style.maxHeight = '95vh';
                fullscreenModalContent.appendChild(clonedSvg);
                fullscreenModal.classList.remove('hidden');
                document.body.style.overflow = 'hidden';
            };
        } catch (e) {
            console.error("Error rendering Mermaid chart:", e);
            mermaidDiv.innerHTML = `<p class="text-red-500 font-bold">Mermaid Chart Error:</p><pre>${e.message}</pre><pre>${sanitizeHTML(mermaidCode)}</pre>`;
        }
    }
}

exportMdBtn.addEventListener('click', () => {
    const markdownContent = generateMarkdownExport();
    downloadMarkdown('brainstorm-export.md', markdownContent);
});

function generateMarkdownExport() {
    const md = [];
    md.push(`# Brainstorm Session: ${brainstormState.topic}`);
    md.push(`**Type:** ${brainstormState.type}`);

    if (brainstormState.combinedContext) {
        md.push('\n## Stage 1: Context & Team');
        md.push('### Research Context');
        md.push(brainstormState.combinedContext);
    }
    if (brainstormState.personas) {
        md.push('\n### Assembled Agent Team');
        brainstormState.personas.forEach(p => {
            md.push(`- **${p.Role}**`);
            md.push(`  - **Goal:** ${p.Goal}`);
            md.push(`  - **Backstory:** ${p.Backstory}`);
        });
    }
    if (brainstormState.ideationOutputs) {
        md.push('\n## Stage 2: Divergent Ideation');
        for (const role in brainstormState.ideationOutputs) {
            md.push(`\n### Ideas from ${role}`);
            md.push(brainstormState.ideationOutputs[role]);
        }
    }
    if (brainstormState.evaluationOutput) {
        md.push('\n## Stage 3: Convergent Evaluation');
        // Remove the JSON block from the evaluation for a cleaner md export
        const cleanEvaluation = brainstormState.evaluationOutput.replace(/```json\s*([\s\S]*?)\s*```/, '').trim();
        md.push(cleanEvaluation);
    }
    if (brainstormState.finalPlanOutput) {
        md.push('\n## Stage 4: Final Plan');
        md.push(brainstormState.finalPlanOutput);
    }

    return md.join('\n\n');
}

function downloadMarkdown(filename, text) {
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
    element.setAttribute('download', filename);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

closeFullscreenBtn.addEventListener('click', () => {
    fullscreenModal.classList.add('hidden');
    fullscreenModalContent.innerHTML = '';
    document.body.style.overflow = 'auto';
});
