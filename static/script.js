document.addEventListener('DOMContentLoaded', () => {
    const chatMessagesDiv = document.getElementById('chat-messages');
    const productRecommendationsDiv = document.getElementById('product-recommendations');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const actionButtonsContainer = document.getElementById('action-buttons-container');
    const newConversationButton = document.getElementById('newConversationButton');
    const dashboardButton = document.getElementById('dashboardButton');
    const welcomeCard = document.getElementById('welcomeCard');
    const dashboardPanel = document.getElementById('dashboardPanel');
    const chatWindow = document.getElementById('chatWindow');
    const chatInputArea = document.getElementById('chatInputArea');
    const closeDashboard = document.getElementById('closeDashboard');

    let sessionId = localStorage.getItem('aiAssistantSessionId');
    const API_URL = '/chat';

    // Global functions for onclick handlers
    window.startShopping = startShopping;
    window.showDashboard = showDashboard;
    window.trackOrder = trackOrder;
    window.viewCollections = viewCollections;
    window.viewWishlist = viewWishlist;
    window.viewHistory = viewHistory;

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
            button.classList.add('action-button');
            button.textContent = option.label;
            button.addEventListener('click', () => {
                appendMessage(option.label, 'user');
                sendMessage(option.value);
            });
            actionButtonsContainer.appendChild(button);
        });
    }

    async function sendMessage(messageText) {
        // Handle empty or null messages for initial greeting
        const trimmedMessage = messageText ? messageText.trim() : "";
        
        // Only show the user's message if it's not empty
        if (trimmedMessage) {
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
                body: JSON.stringify({
                    session_id: sessionId,
                    message: trimmedMessage,
                }),
            });

            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            
            const data = await response.json();

            sessionId = data.session_id;
            localStorage.setItem('aiAssistantSessionId', sessionId);

            if (data.reply) {
                appendMessage(data.reply, 'assistant');
            }
            if (data.products) {
                displayProducts(data.products);
            }
            if (data.action_buttons) {
                displayActionButtons(data.action_buttons);
            } else {
                setInputState(true);
            }

        } catch (error) {
            console.error('Error communicating with backend:', error);
            appendMessage('Sorry, I encountered a connection issue. Please try again.', 'assistant');
            setInputState(true);
        }
    }

    async function startNewConversation() {
        try {
            // Clear the current session on the backend
            if (sessionId) {
                await fetch('/new-session', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ session_id: sessionId })
                });
            }
            
            // Clear the UI
            chatMessagesDiv.innerHTML = '';
            productRecommendationsDiv.innerHTML = '';
            actionButtonsContainer.innerHTML = '';
            
            // Clear session storage
            localStorage.removeItem('aiAssistantSessionId');
            sessionId = null;
            
            // Start the initial greeting
            sendMessage("");

        } catch (error) {
            console.error('Error starting new conversation:', error);
            appendMessage('Could not start a new session. Please refresh the page.', 'assistant');
        }
    }

    function startShopping() {
        // Add smooth transition effect
        welcomeCard.style.transform = 'scale(0.95)';
        welcomeCard.style.opacity = '0';
        
        setTimeout(() => {
            welcomeCard.classList.add('hidden');
            dashboardPanel.classList.add('hidden');
            chatWindow.classList.remove('hidden');
            chatInputArea.classList.remove('hidden');
            
            // Reset transform and opacity
            welcomeCard.style.transform = '';
            welcomeCard.style.opacity = '';
            
            // Start the conversation
            startNewConversation();
        }, 200);
    }

    function showDashboard() {
        // Add smooth transition effect
        if (!welcomeCard.classList.contains('hidden')) {
            welcomeCard.style.transform = 'scale(0.95)';
            welcomeCard.style.opacity = '0';
        }
        if (!chatWindow.classList.contains('hidden')) {
            chatWindow.style.transform = 'scale(0.95)';
            chatWindow.style.opacity = '0';
        }
        if (!chatInputArea.classList.contains('hidden')) {
            chatInputArea.style.transform = 'scale(0.95)';
            chatInputArea.style.opacity = '0';
        }
        
        setTimeout(() => {
            welcomeCard.classList.add('hidden');
            chatWindow.classList.add('hidden');
            chatInputArea.classList.add('hidden');
            dashboardPanel.classList.remove('hidden');
            
            // Reset transforms and opacity
            welcomeCard.style.transform = '';
            welcomeCard.style.opacity = '';
            chatWindow.style.transform = '';
            chatWindow.style.opacity = '';
            chatInputArea.style.transform = '';
            chatInputArea.style.opacity = '';
        }, 200);
    }

    function hideDashboard() {
        // Show welcome card, hide dashboard and chat
        dashboardPanel.classList.add('hidden');
        chatWindow.classList.add('hidden');
        chatInputArea.classList.add('hidden');
        welcomeCard.classList.remove('hidden');
    }

    function trackOrder() {
        appendMessage('I\'d be happy to help you track your order! Please provide your order number or email address.', 'assistant');
        showChatInterface();
    }

    function viewCollections() {
        appendMessage('Here are our featured collections! What type of jewelry are you looking for today?', 'assistant');
        showChatInterface();
    }

    function viewWishlist() {
        appendMessage('Let me show you your saved items. You can also add new items to your wishlist while browsing!', 'assistant');
        showChatInterface();
    }

    function viewHistory() {
        appendMessage('Here\'s your browsing and purchase history. Is there anything specific you\'d like to revisit?', 'assistant');
        showChatInterface();
    }

    function showChatInterface() {
        // Hide dashboard and show chat interface
        dashboardPanel.classList.add('hidden');
        welcomeCard.classList.add('hidden');
        chatWindow.classList.remove('hidden');
        chatInputArea.classList.remove('hidden');
        
        // Focus on input
        setInputState(true);
    }

    // Event Listeners
    sendButton.addEventListener('click', () => {
        if (userInput.value.trim()) {
            sendMessage(userInput.value);
        }
    });

    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !userInput.disabled && userInput.value.trim()) {
            event.preventDefault();
            sendMessage(userInput.value);
        }
    });
    
    newConversationButton.addEventListener('click', startNewConversation);
    dashboardButton.addEventListener('click', showDashboard);
    closeDashboard.addEventListener('click', hideDashboard);

    // Show welcome card by default
    welcomeCard.classList.remove('hidden');
    dashboardPanel.classList.add('hidden');
    chatWindow.classList.add('hidden');
    chatInputArea.classList.add('hidden');
});