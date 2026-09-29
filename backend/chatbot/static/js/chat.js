// ============================================
// BUSINESS FINDER — CHAT UI CONTROLLER v3
// ============================================

const state = {
    latitude: null,
    longitude: null,
    locationEnabled: false,
    isRecording: false,
    recognition: null,
    conversationContext: [], // Stores conversation history for follow-up queries
};

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const voiceBtn = document.getElementById('voiceBtn');
const typingIndicator = document.getElementById('typingIndicator');
const locationBtn = document.getElementById('locationBtn');
const locationBar = document.getElementById('locationBar');
const locationText = document.getElementById('locationText');
const useMockLocation = document.getElementById('useMockLocation');
const clearChat = document.getElementById('clearChat');
const welcomeScreen = document.getElementById('welcomeScreen');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    messageInput.focus();
});

function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    voiceBtn.addEventListener('click', toggleVoiceInput);
    locationBtn.addEventListener('click', enableLocation);
    useMockLocation.addEventListener('click', useMockCoimbatore);
    clearChat.addEventListener('click', clearConversation);

    // Quick action buttons
    document.querySelectorAll('.quick-action').forEach(btn => {
        btn.addEventListener('click', () => {
            messageInput.value = btn.dataset.query;
            sendMessage();
        });
    });

    // Example query buttons on welcome screen
    document.querySelectorAll('.example-query').forEach(btn => {
        btn.addEventListener('click', () => {
            messageInput.value = btn.dataset.query;
            sendMessage();
        });
    });
}

function enableLocation() {
    if (!navigator.geolocation) {
        alert('Geolocation is not supported by your browser.');
        return;
    }

    locationText.textContent = 'Detecting...';

    navigator.geolocation.getCurrentPosition(
        (position) => {
            state.latitude = position.coords.latitude;
            state.longitude = position.coords.longitude;
            state.locationEnabled = true;
            locationText.textContent = `${state.latitude.toFixed(4)}, ${state.longitude.toFixed(4)}`;
            locationBar.classList.add('visible');
            locationBtn.classList.add('active');
            locationBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg><span>Location Active</span>`;
        },
        (error) => {
            locationText.textContent = 'Unable to detect';
            alert('Could not get your location. You can use the mock location or search by area name.');
        },
        { enableHighAccuracy: true, timeout: 10000 }
    );
}

function useMockCoimbatore() {
    state.latitude = 11.0168;
    state.longitude = 76.9558;
    state.locationEnabled = true;
    locationText.textContent = 'Coimbatore Center (11.0168, 76.9558)';
    locationBar.classList.add('visible');
    locationBtn.classList.add('active');
    locationBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg><span>Location Active</span>`;
}

function clearConversation() {
    chatMessages.innerHTML = '';
    chatMessages.appendChild(welcomeScreen);
    welcomeScreen.style.display = 'flex';
    state.conversationContext = []; // Reset conversation context
    messageInput.focus();
}

async function sendMessage() {
    const query = messageInput.value.trim();
    if (!query) return;

    // Hide welcome screen on first message
    if (welcomeScreen.style.display !== 'none') {
        welcomeScreen.style.display = 'none';
    }

    addMessage(query, 'user');
    messageInput.value = '';
    showTyping(true);

    // Add user message to conversation context
    state.conversationContext.push({
        role: 'user',
        content: query
    });

    try {
        const response = await fetch('/api/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: query,
                latitude: state.latitude,
                longitude: state.longitude,
                conversation_context: state.conversationContext,
            }),
        });

        const data = await response.json();
        showTyping(false);

        if (data.success) {
            addBotResponse(data.message, data.businesses);

            // Add bot response to conversation context
            state.conversationContext.push({
                role: 'assistant',
                content: data.message
            });

            // Keep only last 10 messages to avoid token limits
            if (state.conversationContext.length > 10) {
                state.conversationContext = state.conversationContext.slice(-10);
            }
        } else {
            addMessage(data.message || 'Sorry, something went wrong.', 'bot');
        }
    } catch (error) {
        showTyping(false);
        addMessage('Error connecting to server. Please try again.', 'bot');
        console.error('Chat error:', error);
    }
}

function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = sender === 'user' ? '👤' : '🤖';

    const content = document.createElement('div');
    content.className = 'message-content';

    const p = document.createElement('p');
    p.textContent = text;
    content.appendChild(p);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function addBotResponse(text, businesses) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = '🤖';

    const content = document.createElement('div');
    content.className = 'message-content';

    const p = document.createElement('p');
    p.textContent = text;
    content.appendChild(p);

    if (businesses && businesses.length > 0) {
        const cardsContainer = document.createElement('div');
        cardsContainer.className = 'business-cards';

        businesses.forEach(biz => {
            const card = createBusinessCard(biz);
            cardsContainer.appendChild(card);
        });

        content.appendChild(cardsContainer);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function createBusinessCard(biz) {
    const card = document.createElement('div');
    card.className = 'business-card';

    const header = document.createElement('div');
    header.className = 'card-header';

    const title = document.createElement('span');
    title.className = 'card-title';
    title.textContent = biz.name;

    const rating = document.createElement('span');
    rating.className = 'card-rating';
    rating.textContent = `⭐ ${biz.rating}`;

    header.appendChild(title);
    header.appendChild(rating);

    const category = document.createElement('div');
    category.className = 'card-category';
    category.textContent = biz.subcategory || biz.category;

    const address = document.createElement('div');
    address.className = 'card-info';
    address.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg><span>${biz.area}, Coimbatore</span>`;

    const phone = document.createElement('div');
    phone.className = 'card-info';
    phone.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg><span>${biz.phone}</span>`;

    const footer = document.createElement('div');
    footer.className = 'card-footer';

    const price = document.createElement('span');
    price.className = 'card-price';
    price.textContent = biz.price_range || '';

    const distance = document.createElement('span');
    distance.className = 'card-distance';
    distance.textContent = biz.distance_km ? `${biz.distance_km} km away` : '';

    footer.appendChild(price);
    footer.appendChild(distance);

    card.appendChild(header);
    card.appendChild(category);
    card.appendChild(address);
    card.appendChild(phone);
    card.appendChild(footer);

    return card;
}

function toggleVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Speech recognition is not supported in your browser. Try Chrome.');
        return;
    }

    if (state.isRecording) {
        state.recognition?.stop();
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = true;           // Keep listening until user stops
    recognition.interimResults = true;       // Show partial results while speaking
    recognition.maxAlternatives = 1;

    let silenceTimer = null;
    const SILENCE_TIMEOUT = 2000;            // Stop after 2 seconds of silence
    let finalTranscript = '';

    recognition.onstart = () => {
        state.isRecording = true;
        voiceBtn.classList.add('recording');
        voiceBtn.innerHTML = '<span class="voice-wave"><span></span><span></span><span></span><span></span></span>';
        messageInput.placeholder = 'Listening... speak now';
        finalTranscript = '';
    };

    recognition.onresult = (event) => {
        let interimTranscript = '';

        // Collect final results
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }

        // Show interim results in input while speaking
        messageInput.value = finalTranscript || interimTranscript;

        // Reset silence timer on each result
        if (silenceTimer) clearTimeout(silenceTimer);

        // If we have a final result, start silence timer
        if (finalTranscript) {
            silenceTimer = setTimeout(() => {
                recognition.stop();
            }, SILENCE_TIMEOUT);
        }
    };

    recognition.onerror = (event) => {
        state.isRecording = false;
        voiceBtn.classList.remove('recording');
        voiceBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
        messageInput.placeholder = 'Ask about nearby businesses...';

        if (event.error === 'no-speech') {
            // No speech detected, don't show error to user
            console.log('No speech detected');
        } else if (event.error === 'audio-capture') {
            alert('No microphone found. Please check your microphone.');
        } else if (event.error === 'not-allowed') {
            alert('Microphone access denied. Please allow microphone access.');
        } else {
            console.log('Speech recognition error:', event.error);
        }
    };

    recognition.onend = () => {
        state.isRecording = false;
        voiceBtn.classList.remove('recording');
        voiceBtn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>';
        messageInput.placeholder = 'Ask about nearby businesses...';

        // Send the final transcript if we have one
        if (finalTranscript.trim()) {
            messageInput.value = finalTranscript.trim();
            sendMessage();
        }
    };

    state.recognition = recognition;
    recognition.start();
}

function showTyping(show) {
    typingIndicator.classList.toggle('visible', show);
    if (show) {
        scrollToBottom();
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
