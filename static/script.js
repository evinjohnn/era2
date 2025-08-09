// /static/script.js
document.addEventListener('DOMContentLoaded', () => {
    const chatMessagesDiv = document.getElementById('chat-messages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const chatInputArea = document.getElementById('chat-input-area');
    const inputWrapper = document.getElementById('input-wrapper');
    const interactiveBubblesContainer = document.getElementById('interactive-bubbles');
    const menuCheckbox = document.getElementById('checkbox');
    const menuOverlay = document.getElementById('overlay');
    const resetConversationBtn = document.getElementById('reset-conversation-btn');

    let sessionId = localStorage.getItem('retailAiSessionId');
    let isTyping = false;

    function updateGreeting() {
        const greetingElement = document.getElementById('greeting-text');
        if (!greetingElement) return;
        const currentHour = new Date().getHours();
        let greeting = 'Good Afternoon!';
        if (currentHour < 12) greeting = 'Good Morning!';
        else if (currentHour >= 17) greeting = 'Good Evening!';
        greetingElement.textContent = greeting;
    }

    function scrollToBottom() {
        chatMessagesDiv.scrollTo({ top: chatMessagesDiv.scrollHeight, behavior: 'smooth' });
    }

    function createInitialView() {
        // Only create the initial view if no messages are present
        if (chatMessagesDiv.querySelector('.message-wrapper')) {
            return;
        }
        const initialViewHTML = `
            <div class="welcome-card animate__animated animate__fadeIn">
                <div class="welcome-text">
                    <h1 id="greeting-text">Good Afternoon!</h1>
                    <p>I'm Joxy, your personal jewelry assistant. I'm here to help you with all your luxury jewelry needs.</p>
                </div>
                <div class="bot-avatar-container">
                    <img src="/static/logo.png" alt="Joxy, the AI assistant">
                </div>
            </div>
            <div class="quick-actions animate__animated animate__fadeInUp">
                <button class="action-button" data-message="New Arrivals">
                    <span class="material-symbols-outlined">diamond</span>
                    <span>New Arrivals</span>
                </button>
                <button class="action-button" data-message="Show me rings">
                    <span class="material-symbols-outlined">ring_volume</span>
                    <span>Rings</span>
                </button>
                <button class="action-button" data-message="I need a gift">
                    <span class="material-symbols-outlined">card_giftcard</span>
                    <span>Find a Gift</span>
                </button>
                <button class="action-button" data-message="Help me choose">
                    <span class="material-symbols-outlined">support_agent</span>
                    <span>Help Me Choose</span>
                </button>
            </div>`;
        chatMessagesDiv.innerHTML = initialViewHTML;
        updateGreeting();
        document.querySelectorAll('.action-button').forEach(button => {
            button.addEventListener('click', () => {
                const message = button.dataset.message;
                sendMessage(message);
            });
        });
    }

    function appendMessage(text, sender) {
        if (sender === 'user') {
            document.querySelector('.welcome-card')?.remove();
            document.querySelector('.quick-actions')?.remove();
        }

        const wrapper = document.createElement('div');
        wrapper.className = `message-wrapper ${sender} animate__animated animate__fadeInUp`;
        wrapper.style.setProperty('--animate-duration', '0.5s');

        if (sender === 'assistant') {
            const avatar = document.createElement('img');
            avatar.src = '/static/logo.png';
            avatar.className = 'avatar';
            wrapper.appendChild(avatar);
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        messageDiv.innerHTML = text.replace(/\n/g, '<br>'); // Support newlines in bot responses
        
        wrapper.appendChild(messageDiv);
        chatMessagesDiv.appendChild(wrapper);
        scrollToBottom();
        return wrapper;
    }

    function showThinkingIndicator() {
        document.querySelector('.welcome-card')?.remove();
        document.querySelector('.quick-actions')?.remove();
        const wrapper = document.createElement('div');
        wrapper.className = 'message-wrapper assistant';
        
        const avatar = document.createElement('img');
        avatar.src = '/static/logo.png';
        avatar.className = 'avatar';
        wrapper.appendChild(avatar);

        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message assistant thinking-animation';
        thinkingDiv.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        wrapper.appendChild(thinkingDiv);

        chatMessagesDiv.appendChild(wrapper);
        scrollToBottom();
        return wrapper;
    }

    function displayProductCards(products) {
        if (!products || products.length === 0) return;

        const productContainer = document.createElement('div');
        productContainer.className = 'product-cards-container';
        
        products.forEach(product => {
            const card = document.createElement('div');
            card.className = 'product-card animate__animated animate__fadeInUp';

            const imageUrl = product.image_url || 'https://via.placeholder.com/200/cccccc/FFFFFF?Text=No+Image';
            const name = product.name || 'Unnamed Product';
            const price = (product.price || 0).toFixed(2);
            const description = product.description || 'A beautiful piece of jewelry.';
            const metal = product.metal || '';
            const category = product.category || '';
            const styleTags = Array.isArray(product.style_tags) ? product.style_tags : [];

            card.innerHTML = `
                <img src="${imageUrl}" alt="${name}" class="product-image">
                <div class="product-info">
                    <h3 class="product-name">${name}</h3>
                    <p class="product-price">${price}</p>
                    <p class="product-description">${description}</p>
                    <div class="product-tags">
                        ${metal ? `<span class="tag">${metal}</span>` : ''}
                        ${category ? `<span class="tag">${category}</span>` : ''}
                        ${styleTags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                    </div>
                </div>
            `;
            productContainer.appendChild(card);
        });
        
        chatMessagesDiv.appendChild(productContainer);
        scrollToBottom();
    }

    function displayInteractiveBubbles(options) {
        interactiveBubblesContainer.innerHTML = '';
        if (!options || options.length === 0) {
            interactiveBubblesContainer.classList.add('hidden');
            return;
        };

        interactiveBubblesContainer.classList.remove('hidden');
        options.forEach(option => {
            const button = document.createElement('button');
            button.className = 'bubble-button';
            button.textContent = option.label;
            button.onclick = () => {
                interactiveBubblesContainer.innerHTML = '';
                sendMessage(option.value);
            };
            interactiveBubblesContainer.appendChild(button);
        });
    }

    function setUiMode(mode) {
        if (mode === 'chat') {
            inputWrapper.classList.add('hidden');
            interactiveBubblesContainer.classList.remove('hidden');
        } else { // 'text_input_only'
            inputWrapper.classList.remove('hidden');
            interactiveBubblesContainer.classList.add('hidden');
            userInput.focus();
        }
    }

    async function sendMessage(messageText) {
        const trimmedMessage = String(messageText).trim();
        if (!trimmedMessage) return;

        // Special command from buttons to switch to typing
        if (trimmedMessage === '__type__') {
            setUiMode('text_input_only');
            return;
        }

        appendMessage(trimmedMessage, 'user');
        userInput.value = '';
        setUiMode('chat'); // Default to hiding input after sending
        displayInteractiveBubbles([]);
        const thinkingIndicator = showThinkingIndicator();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, message: trimmedMessage }),
            });

            thinkingIndicator.remove();
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            
            sessionId = data.session_id; // Always update session ID
            localStorage.setItem('retailAiSessionId', sessionId);

            if (data.reply) appendMessage(data.reply, 'assistant');
            if (data.products && data.products.length > 0) {
                displayProductCards(data.products);
            }
            if (data.interactive_options) {
                displayInteractiveBubbles(data.interactive_options);
            }
            
            setUiMode(data.ui_mode);

        } catch (error) {
            console.error('Error sending message:', error);
            thinkingIndicator?.remove();
            appendMessage('Sorry, I encountered an error. Please try again.', 'assistant');
            setUiMode('text_input_only');
        }
    }

    async function startConversation(isReset = false) {
        if (isReset) {
            localStorage.removeItem('retailAiSessionId');
            sessionId = null;
        }

        try {
            const response = await fetch('/start', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId })
            });
            if (!response.ok) throw new Error('Failed to start conversation');
            const data = await response.json();
            sessionId = data.session_id;
            localStorage.setItem('retailAiSessionId', sessionId);
            
            if (isReset || !document.querySelector('.message-wrapper')) {
                chatMessagesDiv.innerHTML = ''; // Clear everything for a fresh start
                createInitialView();
                appendMessage(data.reply, 'assistant');
            }
            
            setUiMode(data.ui_mode);
            
        } catch (error) {
            console.error('Error starting conversation:', error);
            appendMessage('Sorry, I am currently unavailable. Please try again later.', 'assistant');
        }
    }

    // --- Event Listeners ---
    sendButton.addEventListener('click', () => sendMessage(userInput.value));
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage(userInput.value);
        }
    });

    menuOverlay.addEventListener('click', () => {
        if (menuCheckbox.checked) {
            menuCheckbox.checked = false;
        }
    });

    resetConversationBtn.addEventListener('click', (e) => {
        e.preventDefault();
        if (confirm('Are you sure you want to reset the conversation?')) {
            menuCheckbox.checked = false;
            startConversation(true);
        }
    });

    // Initialize
    startConversation();
});