// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// State
let selectedMode = 'fast';
let modes = [];
let currentQuestions = []; // For Max mode

// DOM Elements
const modesContainer = document.getElementById('modes-container');
const queryInput = document.getElementById('query-input');
const generateBtn = document.getElementById('generate-btn');
const questionsSection = document.getElementById('questions-section');
const questionsContainer = document.getElementById('questions-container');
const generateWithAnswersBtn = document.getElementById('generate-with-answers-btn');
const statusSection = document.getElementById('status-section');
const statusContent = document.getElementById('status-content');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadModes();
    setupEventListeners();
    // Hide questions/answers controls initially and set label
    clearQuestionsPanel();
    updateGenerateButtonLabel();
});

// Load available modes from API
async function loadModes() {
    try {
        const response = await fetch(`${API_BASE_URL}/modes`);
        if (!response.ok) throw new Error('Failed to load modes');

        modes = await response.json();
        renderModes();
    } catch (error) {
        modesContainer.innerHTML = `
            <div class="status-card error">
                <h3>Error Loading Modes</h3>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Render mode selection cards
function renderModes() {
    modesContainer.innerHTML = modes.map(mode => `
        <div class="mode-card ${mode.id === selectedMode ? 'selected' : ''}"
             data-mode="${mode.id}">
            <h3>${mode.label}</h3>
            <p>${mode.description}</p>
        </div>
    `).join('');

    // Add click handlers
    document.querySelectorAll('.mode-card').forEach(card => {
        card.addEventListener('click', () => {
            selectedMode = card.dataset.mode;
            document.querySelectorAll('.mode-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');

            // Clear questions panel when switching modes
            clearQuestionsPanel();

            // Update generate button label for max vs fast
            updateGenerateButtonLabel();
        });
    });
}

// Update the main generate button label depending on selected mode
function updateGenerateButtonLabel() {
    if (selectedMode === 'max') {
        generateBtn.textContent = 'Generate Questions';
    } else {
        generateBtn.textContent = 'Generate Presentation';
    }
    validateInput();
}

// Setup event listeners
function setupEventListeners() {
    // Example chips
    document.querySelectorAll('.example-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            queryInput.value = chip.dataset.query;
            validateInput();
        });
    });

    // Query input validation
    queryInput.addEventListener('input', validateInput);

    // Generate button
    generateBtn.addEventListener('click', handleGenerate);

    // Generate with answers button (Max mode)
    generateWithAnswersBtn.addEventListener('click', handleGenerateWithAnswers);
}


// Validate input and enable/disable generate button
function validateInput() {
    const query = queryInput.value.trim();
    generateBtn.disabled = query.length < 5;
}

// Handle presentation generation
async function handleGenerate() {
    const query = queryInput.value.trim();
    if (query.length < 5) return;

    // Branch by mode BEFORE choosing endpoint
    if (selectedMode === 'max') {
        // MAX MODE: Two-phase flow - start Phase 1 (questions)
        await handleMaxModePhase1(query);
        return;
    }

    // FAST MODE: Direct generation against /generate
    await generatePresentation(query, 'fast', null);
}

// Max mode Phase 1: Get clarifying questions
async function handleMaxModePhase1(query) {
    // Show loading state
    generateBtn.disabled = true;
    generateBtn.classList.add('loading');
    generateBtn.textContent = 'Loading Questions...';

    showStatus('loading', 'Generating Questions',
        'Analyzing your query to generate relevant clarifying questions...');

    try {
        const response = await fetch(`${API_BASE_URL}/max/questions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        });
        console.log('POST', `${API_BASE_URL}/max/questions`, { query });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate questions');
        }

        const result = await response.json();

        if (result.valid === false) {
            // Query was rejected
            showStatus('error', 'Query Rejected', result.user_message);
            clearQuestionsPanel();
        } else {
            // Show questions panel
            currentQuestions = result.questions;
            renderQuestions(result.questions);

            // Hide status, show questions
            statusSection.classList.add('hidden');

            // Hide generate button, user will click "Generate with Answers" next
            generateBtn.style.display = 'none';
        }
    } catch (error) {
        showStatus('error', 'Failed to Load Questions', error.message);
        clearQuestionsPanel();
    } finally {
        // Reset button
        generateBtn.disabled = false;
        generateBtn.classList.remove('loading');
        // Respect current mode when restoring label
        updateGenerateButtonLabel();
    }
}

// Max mode Phase 2: Generate with answers
async function handleGenerateWithAnswers() {
    const query = queryInput.value.trim();

    // Collect answers from input fields
    const answers = {};
    currentQuestions.forEach((q, index) => {
        const input = document.getElementById(`question-${index}`);
        if (input && input.value.trim()) {
            // q is a string (question text)
            answers[q] = input.value.trim();
        }
    });

    // Validate at least one answer
    if (Object.keys(answers).length === 0) {
        showStatus('error', 'No Answers Provided',
            'Please answer at least one clarifying question before generating.');
        return;
    }

    // Generate presentation with answers
    await generatePresentation(query, 'max', answers);
}

// Common generation function for both modes
async function generatePresentation(query, mode, answers) {
    // Show loading state
    const btn = mode === 'max' ? generateWithAnswersBtn : generateBtn;
    btn.disabled = true;
    btn.classList.add('loading');
    btn.textContent = 'Generating...';

    showStatus('loading', 'Generating Presentation',
        'Running AI agents to analyze context and generate slides. This takes about 60 seconds...');

    try {
        // Safety: enforce two-phase requirement for max mode
        if (mode === 'max' && (!answers || Object.keys(answers).length === 0)) {
            showStatus('error', 'Missing Answers',
                'Max mode requires answers to clarifying questions. Please answer the questions first.');
            return;
        }

        const body = {
            mode: mode,
            query: query
        };

        if (answers && Object.keys(answers).length > 0) {
            body.answers = answers;
        }

        console.log('POST', `${API_BASE_URL}/generate`, body);
        const response = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Generation failed');
        }

        const result = await response.json();

        if (result.valid === false) {
            // Query was rejected
            showStatus('error', 'Query Rejected', result.user_message);
        } else {
            // Success - display the deck
            await displayDeck(result);

            // Clear questions panel after successful generation
            clearQuestionsPanel();
        }
    } catch (error) {
        showStatus('error', 'Generation Failed', error.message);
    } finally {
        // Reset button
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = mode === 'max' ? 'Generate with Answers' : 'Generate Presentation';

        // Restore generate button visibility if hidden
        if (mode === 'max') {
            generateBtn.style.display = '';
        }

        validateInput();
    }
}

// Display generated deck
async function displayDeck(result) {
    const { deck_id, deck_path, slide_count } = result;

    // Try to fetch deck content from /deck/{deck_id} endpoint
    let deckContent = null;
    try {
        console.log(`Fetching deck content from: ${API_BASE_URL}/deck/${deck_id}`);
        const deckResponse = await fetch(`${API_BASE_URL}/deck/${deck_id}`);
        console.log('Deck fetch response status:', deckResponse.status, deckResponse.ok);
        if (deckResponse.ok) {
            const deckData = await deckResponse.json();
            deckContent = deckData.content || deckData.markdown;
            console.log('Deck content fetched:', deckContent ? `${deckContent.length} chars` : 'null/empty');
        }
    } catch (error) {
        // Endpoint doesn't exist - we'll show info without rendering
        console.log('Deck endpoint error:', error);
    }

    statusContent.innerHTML = `
        <div class="status-card success">
            <h3>✓ Presentation Generated Successfully</h3>

            <div class="deck-info">
                <div class="info-item">
                    <label>Deck ID</label>
                    <div class="value">${deck_id}</div>
                </div>
                <div class="info-item">
                    <label>Slides</label>
                    <div class="value">${slide_count}</div>
                </div>
                <div class="info-item">
                    <label>Location</label>
                    <div class="value">${deck_path}</div>
                </div>
            </div>

            <div class="deck-actions">
                <button class="btn btn-primary" onclick="downloadDeck('${deck_id}', '${deck_path}')">
                    Download Markdown
                </button>
                ${deckContent ? `
                    <button class="btn" onclick="toggleDeckView()">
                        Toggle Markdown Preview
                    </button>
                ` : ''}
                <button class="btn btn-primary" onclick="buildSlidevDeck('${deck_id}')">
                    🎨 Render Slidev Deck
                </button>
            </div>

            <div id="slidev-container" style="display: none; margin-top: 1.5rem;">
                <div class="status-card loading" id="slidev-building" style="display: none;">
                    <h3><span class="loading-spinner"></span>Building Slidev Presentation</h3>
                    <p class="loading-dots">This takes about 20 seconds</p>
                </div>

                <div id="slidev-viewer" style="display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h3 style="margin: 0;">Slidev Presentation</h3>
                        <a href="http://localhost:8000/slides/" target="_blank" class="btn btn-primary">
                            Open in New Tab
                        </a>
                    </div>
                    <iframe
                        id="slidev-iframe"
                        src=""
                        style="width: 100%; height: 600px; border: 1px solid var(--border); border-radius: 8px;"
                        title="Slidev Presentation"
                    ></iframe>
                </div>
            </div>

            ${deckContent ? `
                <div id="deck-preview" class="deck-viewer">
                    ${renderMarkdown(deckContent)}
                </div>
            ` : `
                <p style="margin-top: 1rem; color: var(--text-dim);">
                    Deck saved to: <code>${deck_path}</code><br>
                    To view: open the file or use the fallback renderer with
                    <code>python backend/render_fallback.py</code>
                </p>
            `}
        </div>
    `;

    statusSection.classList.remove('hidden');
}

// Simple markdown to HTML renderer for deck preview
function renderMarkdown(markdown) {
    // Strip YAML frontmatter
    markdown = markdown.replace(/^---\s*\n.*?\n---\s*\n/s, '');

    // Split by slide separator
    const slides = markdown.split(/\n---\s*\n/);

    return slides.map((slide, index) => {
        const lines = slide.trim().split('\n');
        let html = '';

        lines.forEach(line => {
            line = line.trim();
            if (!line) return;

            if (line.startsWith('# ')) {
                html += `<h2>${escapeHtml(line.substring(2))}</h2>`;
            } else if (line.startsWith('## ')) {
                html += `<h3>${escapeHtml(line.substring(3))}</h3>`;
            } else if (line.startsWith('- ') || line.startsWith('* ')) {
                if (!html.includes('<ul>')) html += '<ul>';
                html += `<li>${escapeHtml(line.substring(2))}</li>`;
            } else {
                if (html.endsWith('</li>')) html += '</ul>';
                html += `<p>${escapeHtml(line)}</p>`;
            }
        });

        if (html.includes('<li>') && !html.endsWith('</ul>')) {
            html += '</ul>';
        }

        return html + (index < slides.length - 1 ? '<hr>' : '');
    }).join('');
}

// Escape HTML special characters
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Toggle deck preview visibility
function toggleDeckView() {
    console.log('toggleDeckView() called');
    const preview = document.getElementById('deck-preview');
    console.log('Preview element found:', !!preview);
    if (preview) {
        console.log('Current display style:', preview.style.display);
        // Initially, style.display is '' (empty string), not 'none'
        // So we need to check if it's currently hidden
        const isHidden = preview.style.display === 'none';
        preview.style.display = isHidden ? 'block' : 'none';
        console.log('Toggled display to:', preview.style.display);
    } else {
        console.log('Preview element not found in DOM');
    }
}

// Build Slidev deck
async function buildSlidevDeck(deckId) {
    console.log('buildSlidevDeck() called for deck:', deckId);

    const container = document.getElementById('slidev-container');
    const buildingCard = document.getElementById('slidev-building');
    const viewer = document.getElementById('slidev-viewer');
    const iframe = document.getElementById('slidev-iframe');

    // Show container and building status
    container.style.display = 'block';
    buildingCard.style.display = 'block';
    viewer.style.display = 'none';

    try {
        console.log(`Calling POST ${API_BASE_URL}/build/${deckId}`);
        const response = await fetch(`${API_BASE_URL}/build/${deckId}`, {
            method: 'POST'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Build failed');
        }

        const result = await response.json();
        console.log('Build result:', result);

        // Hide building status, show viewer
        buildingCard.style.display = 'none';
        viewer.style.display = 'block';

        // Load the built presentation in iframe
        const slidesUrl = `http://localhost:8000${result.url}`;
        console.log('Loading Slidev in iframe:', slidesUrl);
        iframe.src = slidesUrl;

        // Update the "Open in new tab" link
        const newTabLink = viewer.querySelector('a[target="_blank"]');
        if (newTabLink) {
            newTabLink.href = slidesUrl;
        }

    } catch (error) {
        console.error('Build failed:', error);
        buildingCard.innerHTML = `
            <h3 style="color: var(--error);">Build Failed</h3>
            <p>${error.message}</p>
        `;
    }
}

// Download deck as markdown file
async function downloadDeck(deckId, deckPath) {
    try {
        // Try to fetch from /deck/{deck_id} endpoint
        const response = await fetch(`${API_BASE_URL}/deck/${deckId}`);

        let content;
        if (response.ok) {
            const data = await response.json();
            content = data.content || data.markdown;
        } else {
            // If endpoint doesn't exist, show error
            showStatus('error', 'Download Failed',
                'Deck download endpoint not available. Check slidev/slides.md directly.');
            return;
        }

        // Create download
        const blob = new Blob([content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `deck-${deckId}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (error) {
        showStatus('error', 'Download Failed',
            `Could not download deck. File location: ${deckPath}`);
    }
}

// Show status message
function showStatus(type, title, message) {
    const loadingSpinner = type === 'loading'
        ? '<span class="loading-spinner"></span>'
        : '';

    const dots = type === 'loading' ? ' class="loading-dots"' : '';

    statusContent.innerHTML = `
        <div class="status-card ${type}">
            <h3>${loadingSpinner}${title}</h3>
            <p${dots}>${message}</p>
        </div>
    `;

    statusSection.classList.remove('hidden');
}

// Render clarifying questions panel (Max mode)
function renderQuestions(questions) {
    // Backend returns questions as strings. Render accordingly.
    questionsContainer.innerHTML = questions.map((q, index) => `
        <div class="question-item" style="margin-bottom: 1.5rem;">
            <label for="question-${index}" style="display: block; font-weight: 600; margin-bottom: 0.5rem;">
                ${escapeHtml(q)}
            </label>
            <input
                type="text"
                id="question-${index}"
                placeholder="${escapeHtml('Enter your answer...')}"
                style="width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 6px; font-size: 1rem;"
            />
        </div>
    `).join('');

    questionsSection.classList.remove('hidden');
    // Show the Generate Presentation button below the questions
    generateWithAnswersBtn.textContent = 'Generate Presentation';
    generateWithAnswersBtn.style.display = '';
}

// Clear questions panel
function clearQuestionsPanel() {
    questionsSection.classList.add('hidden');
    questionsContainer.innerHTML = '';
    currentQuestions = [];
    generateBtn.style.display = '';
    // Hide the answers button until questions are generated
    generateWithAnswersBtn.style.display = 'none';

    // Reset main generate button label according to mode
    updateGenerateButtonLabel();
}
