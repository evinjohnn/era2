document.addEventListener('DOMContentLoaded', () => {
    const chatMessagesDiv = document.getElementById('chat-messages');
    const productRecommendationsDiv = document.getElementById('product-recommendations');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const actionButtonsContainer = document.getElementById('action-buttons-container');
    const newConversationButton = document.getElementById('newConversationButton');
    const dashboardButton = document.getElementById('dashboardButton');
    const welcomeCard = document.getElementById('welcomeCard');
    const chatWindow = document.getElementById('chatWindow');
    const chatInputArea = document.getElementById('chatInputArea');

    let sessionId = localStorage.getItem('aiAssistantSessionId');
    const API_URL = '/chat';

    function setInputState(enabled, placeholder = "Type your answer...") {
        userInput.disabled = !enabled;
        sendButton.disabled = !enabled;
        userInput.placeholder = placeholder;
        if (enabled) userInput.focus();
    }

    function appendMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        messageDiv.textContent = text;
        chatMessagesDiv.appendChild(messageDiv);
        chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight;
    }

    function displayProducts(products) {
        productRecommendationsDiv.innerHTML = '';
        if (!products || products.length === 0) return;

        products.forEach(product => {
            const card = document.createElement('div');
            card.classList.add('product-card');
            card.innerHTML = `
                <img src="${product.image_url || 'https://via.placeholder.com/150'}" alt="${product.name}">
                <div class="product-name">${product.name || 'N/A'}</div>
                <div class="product-price">$${(product.price || 0).toFixed(2)}</div>
            `;
            productRecommendationsDiv.appendChild(card);
        });
    }

    function displayActionButtons(options) {
        actionButtonsContainer.innerHTML = '';
        if (!options || options.length === 0) {
            setInputState(true);
            return;
        }
        setInputState(false, "Please select an option above");

        options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option.label;
            button.addEventListener('click', () => {
                appendMessage(option.label, 'user');
                sendMessage(option.value);
            });
            actionButtonsContainer.appendChild(button);
        });
    }

    async function sendMessage(messageText) {
        const isInitialHandshake = (messageText === null);
        const trimmedMessage = isInitialHandshake ? "" : messageText.trim();

        if (!isInitialHandshake && !trimmedMessage) return;

        if (!isInitialHandshake) {
            appendMessage(trimmedMessage, 'user');
        }

        actionButtonsContainer.innerHTML = '';
        productRecommendationsDiv.innerHTML = '';
        userInput.value = '';
        setInputState(false, "Thinking...");

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, message: trimmedMessage }),
            });

            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            
            const data = await response.json();

            sessionId = data.session_id;
            localStorage.setItem('aiAssistantSessionId', sessionId);

            if (data.reply) appendMessage(data.reply, 'assistant');
            if (data.products) displayProducts(data.products);
            if (data.action_buttons) displayActionButtons(data.action_buttons);
            else setInputState(true);

        } catch (error) {
            console.error('Error communicating with backend:', error);
            appendMessage('Sorry, I encountered a connection issue. Please try again.', 'assistant');
            setInputState(true);
        }
    }
    
    function showChatInterface() {
        welcomeCard.classList.add('hidden');
        chatWindow.classList.remove('hidden');
        chatInputArea.classList.remove('hidden');
    }

    async function startNewConversation() {
        try {
            if (sessionId) {
                await fetch('/new-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                });
            }
            
            chatMessagesDiv.innerHTML = '';
            productRecommendationsDiv.innerHTML = '';
            actionButtonsContainer.innerHTML = '';
            localStorage.removeItem('aiAssistantSessionId');
            sessionId = null;
            
            showChatInterface();
            sendMessage(null); // Trigger initial greeting

        } catch (error) {
            console.error('Error starting new conversation:', error);
            appendMessage('Could not start a new session. Please refresh the page.', 'assistant');
        }
    }

    sendButton.addEventListener('click', () => sendMessage(userInput.value));
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !userInput.disabled) {
            e.preventDefault();
            sendMessage(userInput.value);
        }
    });
    
    newConversationButton.addEventListener('click', startNewConversation);
    dashboardButton.addEventListener('click', () => {
        window.open('/staff/dashboard', '_blank');
    });

    // Add a click listener to the welcome card to start the conversation
    welcomeCard.addEventListener('click', startNewConversation);
});