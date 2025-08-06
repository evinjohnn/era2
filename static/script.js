// static/script.js
const chatMessagesDiv = document.getElementById('chat-messages');
const productRecommendationsDiv = document.getElementById('product-recommendations');
const userInput = document.getElementById('userInput');
const sendButton = document.getElementById('sendButton');
const micButton = document.getElementById('micButton');
const actionButtonsContainer = document.getElementById('action-buttons-container');

let sessionId = localStorage.getItem('retailAiSessionId'); // Persist session ID in local storage

// Use a relative URL for production-readiness
const API_URL = '/chat';

function appendMessage(text, sender, isHTML = false) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    if (isHTML) {
        messageDiv.innerHTML = text;
    } else {
        messageDiv.textContent = text;
    }
    chatMessagesDiv.appendChild(messageDiv);
    chatMessagesDiv.scrollTop = chatMessagesDiv.scrollHeight; // Auto-scroll
}

function displayProducts(products) {
    productRecommendationsDiv.innerHTML = ''; // Clear previous products
    if (!products || products.length === 0) return;

    products.forEach(product => {
        const card = document.createElement('div');
        card.classList.add('product-card');
        card.innerHTML = `
            <img src="${product.image_url}" alt="${product.name}">
            <div class="product-name">${product.name}</div>
            <div class="product-metal">${product.metal}</div>
            <div class="product-price">$${product.price.toFixed(2)}</div>
        `;
        // Add event listener for card click to show details or select
        card.addEventListener('click', () => {
            // For now, just log or could send a message like "Tell me more about [product name]"
            console.log("Clicked product:", product.name);
            sendMessage(`Tell me more about ${product.id}`);
        });
        productRecommendationsDiv.appendChild(card);
    });
}

function displayActionButtons(buttons) {
    actionButtonsContainer.innerHTML = '';
    if (!buttons || buttons.length === 0) return;

    buttons.forEach(buttonInfo => {
        const button = document.createElement('button');
        button.textContent = buttonInfo.label;
        button.addEventListener('click', () => {
            sendMessage(buttonInfo.value); // Send the button's value as a message
            actionButtonsContainer.innerHTML = ''; // Clear buttons after click
        });
        actionButtonsContainer.appendChild(button);
    });
}

async function sendMessage(messageText) {
    const trimmedMessage = messageText.trim();
    if (!trimmedMessage) return; // Don't send empty messages

    // Don't display the initial handshake message to the user
    if (trimmedMessage !== "hi_ai_assistant") {
        appendMessage(trimmedMessage, 'user');
    }
    
    productRecommendationsDiv.innerHTML = ''; // Clear products when user sends a new message
    userInput.value = '';
    
    // Show a thinking indicator if you want
    // appendMessage("...", 'assistant-thinking'); 

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: trimmedMessage,
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        sessionId = data.session_id; // Update session ID (especially if it was new)
        localStorage.setItem('retailAiSessionId', sessionId);

        appendMessage(data.reply, 'assistant');
        displayProducts(data.products);
        displayActionButtons(data.action_buttons);

        if (data.end_conversation) {
            userInput.disabled = true;
            sendButton.disabled = true;
            micButton.disabled = true;
            appendMessage("<em>Session ended. Please wait for staff or refresh to start a new session.</em>", "assistant", true);
        }

    } catch (error) {
        console.error('Error sending message:', error);
        appendMessage('Sorry, I encountered an error. Please try again. If the problem persists, a staff member can assist you.', 'assistant');
    }
}

sendButton.addEventListener('click', () => sendMessage(userInput.value));
userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendMessage(userInput.value);
    }
});

micButton.addEventListener('click', () => {
    appendMessage("Voice input is not implemented yet, but I appreciate your interest! Please type your message.", 'assistant');
});


// Initial welcome message
window.addEventListener('load', () => {
    // Send an initial silent message to get the welcome from the bot
    // Using a special keyword that the backend can recognize
    sendMessage("hi_ai_assistant");
});