document.addEventListener('DOMContentLoaded', () => {
    const chatMessagesDiv = document.getElementById('chat-messages');
    const productRecommendationsDiv = document.getElementById('product-recommendations');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const actionButtonsContainer = document.getElementById('action-buttons-container');

    let sessionId = null;

    const API_URL = '/chat';

    function setInputState(enabled, placeholder = "Type your answer...") {
        userInput.disabled = !enabled;
        sendButton.disabled = !enabled;
        userInput.placeholder = placeholder;
        if (enabled) {
            userInput.focus();
        }
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
                <img src="${product.image_url}" alt="${product.name}">
                <div class="product-name">${product.name}</div>
                <div class="product-price">$${product.price.toFixed(2)}</div>
            `;
            productRecommendationsDiv.appendChild(card);
        });
    }

    function displayActionButtons(options) {
        actionButtonsContainer.innerHTML = '';
        if (!options || options.length === 0) {
            setInputState(true); // Enable text input if no buttons
            return;
        }

        setInputState(false, "Please select an option above"); // Disable text input when buttons are shown

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
        const trimmedMessage = messageText.trim();
        if (!trimmedMessage) return;

        // Clear UI for next turn
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

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();

            sessionId = data.session_id;

            if (data.reply) {
                appendMessage(data.reply, 'assistant');
            }
            if (data.products) {
                displayProducts(data.products);
            }
            if (data.ui_options) {
                displayActionButtons(data.ui_options);
            } else {
                // If no more options, re-enable text input
                setInputState(true);
            }

        } catch (error) {
            console.error('Error sending message:', error);
            appendMessage('Sorry, I encountered a technical issue. Please try again.', 'assistant');
            setInputState(true);
        }
    }

    sendButton.addEventListener('click', () => {
        appendMessage(userInput.value, 'user');
        sendMessage(userInput.value);
    });

    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !userInput.disabled) {
            event.preventDefault();
            appendMessage(userInput.value, 'user');
            sendMessage(userInput.value);
        }
    });

    // Initial greeting from the assistant
    sendMessage(""); // Send an empty message to trigger the first step
});