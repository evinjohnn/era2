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
    let isPageRefresh = false;

    // Check if this is a page refresh
    if (performance.navigation.type === 1) {
        isPageRefresh = true;
        console.log('Page refreshed - analytics tracking disabled');
    }

    // Track actual user interactions only (not page refreshes)
    function trackUserInteraction(action, data = {}) {
        if (isPageRefresh) return; // Don't track on page refresh
        
        // Send analytics data to backend
        fetch('/analytics/track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: sessionId,
                action: action,
                data: data,
                timestamp: new Date().toISOString()
            })
        }).catch(err => console.log('Analytics tracking failed:', err));
    }

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
        // Scroll chat messages to bottom
        chatMessagesDiv.scrollTo({ top: chatMessagesDiv.scrollHeight, behavior: 'smooth' });
        
        // Also scroll the main page to ensure new content is visible
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    }

    function scrollToTop() {
        // Scroll to top of chat messages
        chatMessagesDiv.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Also scroll the main page to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function createInitialView() {
        const initialViewHTML = `
            <div class="welcome-card">
                <div class="welcome-text">
                    <h1 id="greeting-text">Good Afternoon!</h1>
                    <p>I'm Joxy, your personal jewelry assistant. I'm here to help you with all your luxury jewelry needs.</p>
                </div>
                <div class="bot-avatar-container">
                    <img src="/static/logo.png" alt="Joxy, the AI assistant">
                </div>
            </div>
            <div class="quick-actions">
                <button class="action-button" data-action="new-arrivals">
                    <span class="material-symbols-outlined">diamond</span>
                    <span>New Arrivals</span>
                </button>
                <button class="action-button" data-action="collections">
                    <span class="material-symbols-outlined">widgets</span>
                    <span>Collections</span>
                </button>
                <button class="action-button" data-action="track-order">
                    <span class="material-symbols-outlined">local_shipping</span>
                    <span>Track an Order</span>
                </button>
                <button class="action-button" data-action="store-locator">
                    <span class="material-symbols-outlined">location_on</span>
                    <span>Store Locator</span>
                </button>
            </div>`;
        chatMessagesDiv.innerHTML = initialViewHTML;
        updateGreeting();
        document.querySelectorAll('.action-button').forEach(button => {
            button.addEventListener('click', () => {
                const action = button.dataset.action;
                handleActionButton(action);
            });
        });
    }

    // Handle different action button types
    async function handleActionButton(action) {
        trackUserInteraction('action_button_click', { action: action });
        
        switch(action) {
            case 'new-arrivals':
                await showNewArrivals();
                break;
            case 'collections':
                await showCollections();
                break;
            case 'track-order':
                await showTrackOrder();
                break;
            case 'store-locator':
                await showStoreLocator();
                break;
            default:
                console.log('Unknown action:', action);
        }
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
        messageDiv.innerHTML = text; // Use innerHTML to support potential formatting
        
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

    // --- START: CORRECTED FUNCTION ---
    function displayProductCards(products) {
        if (!products || products.length === 0) {
            console.log("No products to display.");
            return;
        }
        console.log("Attempting to display products:", products);

        const productContainer = document.createElement('div');
        productContainer.className = 'product-cards-container animate__animated animate__fadeInUp';
        
        products.forEach((product, index) => {
            const card = document.createElement('div');
            card.className = 'product-card animate__animated animate__fadeInUp';
            card.style.setProperty('--animate-duration', '0.6s');
            card.style.setProperty('--animate-delay', `${index * 0.1}s`);

            // Defensive checks for potentially missing or malformed data
            const imageUrl = product.image_url || 'https://via.placeholder.com/340x200/cccccc/FFFFFF?Text=No+Image';
            const name = product.name || 'Unnamed Product';
            const price = typeof product.price === 'number' ? `$${product.price.toFixed(2)}` : 'Price not available';
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
            
            // Add click event for product cards
            card.addEventListener('click', () => {
                // Add visual feedback
                card.style.transform = 'scale(0.98)';
                setTimeout(() => {
                    card.style.transform = '';
                }, 150);
                
                // You can add more functionality here like opening a product detail modal
                console.log('Product clicked:', product);
            });
            
            productContainer.appendChild(card);
        });
        
        chatMessagesDiv.appendChild(productContainer);
        
        // Scroll to show the new products
        setTimeout(() => {
            scrollToBottom();
            
            // Add smooth scrolling to the product container
            if (productContainer.scrollWidth > productContainer.clientWidth) {
                // Show scroll indicator
                productContainer.style.borderBottom = '2px solid var(--accent-color)';
                
                // Add scroll indicator text
                const scrollIndicator = document.createElement('div');
                scrollIndicator.className = 'scroll-indicator';
                scrollIndicator.innerHTML = '<span>← Scroll for more products →</span>';
                scrollIndicator.style.cssText = `
                    text-align: center;
                    color: var(--accent-color);
                    font-size: 12px;
                    font-weight: 500;
                    margin-top: var(--space-sm);
                    opacity: 0.8;
                    animation: pulse 2s infinite;
                `;
                
                // Add CSS animation for the pulse effect
                if (!document.querySelector('#scroll-indicator-style')) {
                    const style = document.createElement('style');
                    style.id = 'scroll-indicator-style';
                    style.textContent = `
                        @keyframes pulse {
                            0%, 100% { opacity: 0.8; }
                            50% { opacity: 0.4; }
                        }
                    `;
                    document.head.appendChild(style);
                }
                
                productContainer.appendChild(scrollIndicator);
                
                // Remove indicator after 5 seconds
                setTimeout(() => {
                    productContainer.style.borderBottom = '';
                    scrollIndicator.remove();
                }, 5000);
            }
        }, 100);
        
        return productContainer;
    }
    // --- END: CORRECTED FUNCTION ---

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
        
        // Create session ID if it doesn't exist
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('retailAiSessionId', sessionId);
        }
        
        if (trimmedMessage === '__type__') {
            setUiMode('text_input_only');
            return;
        }

        // Handle special button actions
        if (trimmedMessage === 'similar_design') {
            appendMessage('I\'ll show you similar designs. What specific style are you looking for?', 'assistant');
            setUiMode('text_input_only');
            return;
        }
        
        if (trimmedMessage === 'adjust_filter') {
            appendMessage('Let me help you adjust the filters. What would you like to change?', 'assistant');
            setUiMode('text_input_only');
            return;
        }
        
        if (trimmedMessage === 'show_more') {
            appendMessage('Here are more products for you to explore:', 'assistant');
            // You could implement logic to show more products here
            setUiMode('text_input_only');
            return;
        }
        
        if (trimmedMessage === 'filter_category') {
            appendMessage('What category would you like to filter by? (e.g., rings, necklaces, earrings)', 'assistant');
            setUiMode('text_input_only');
            return;
        }
        
        if (trimmedMessage === 'start_over') {
            appendMessage('Great! Let\'s start fresh. What\'s your name?', 'assistant');
            setUiMode('text_input_only');
            return;
        }
        
        if (trimmedMessage === 'browse') {
            appendMessage('Perfect! Here are some products for you to browse:', 'assistant');
            // You could implement logic to show more products here
            setUiMode('text_input_only');
            return;
        }
        
        // Handle special action button values
        if (trimmedMessage === 'back-to-menu') {
            handleBackToMenu();
            return;
        }
        
        if (trimmedMessage === 'back-to-collections') {
            showCollections();
            return;
        }
        
        if (trimmedMessage.startsWith('new-arrivals-page-')) {
            const page = parseInt(trimmedMessage.split('-').pop());
            showNewArrivals(page);
            return;
        }
        
        if (trimmedMessage.startsWith('category-')) {
            const parts = trimmedMessage.split('-');
            const category = parts[1];
            const page = parts.length > 2 ? parseInt(parts[3]) : 1;
            showCategoryProducts(category, page);
            return;
        }

        appendMessage(trimmedMessage, 'user');
        userInput.value = '';
        setUiMode('chat');
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

            if (data.reply) appendMessage(data.reply, 'assistant');
            
            // This is the crucial part
            if (data.products && data.products.length > 0) {
                displayProductCards(data.products);
            }
            
            if (data.action_buttons && data.action_buttons.length > 0) {
                displayInteractiveBubbles(data.action_buttons);
            }
            
            // Correct UI mode logic
            if (data.products || (data.action_buttons && data.action_buttons.length > 0)) {
                 setUiMode('chat');
            } else {
                 setUiMode('text_input_only');
            }

        } catch (error) {
            console.error('Error sending message:', error);
            thinkingIndicator?.remove();
            appendMessage('Sorry, I encountered an error. Please try again.', 'assistant');
            setUiMode('text_input_only');
        }
    }

    function resetConversation() {
        // Clear the chat messages
        chatMessagesDiv.innerHTML = '';
        
        // Remove session ID
        localStorage.removeItem('retailAiSessionId');
        sessionId = null;
        
        // Create the initial view again
        createInitialView();
        
        // Set UI mode to allow text input
        setUiMode('text_input_only');
        
        // Close the menu
        menuCheckbox.checked = false;
        
        // Scroll to top to show the welcome card
        scrollToTop();
    }

    // Show New Arrivals - Real products with pagination
    async function showNewArrivals(page = 1) {
        try {
            const response = await fetch('/products/new-arrivals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    session_id: sessionId, 
                    page: page,
                    limit: 5 
                })
            });

            if (!response.ok) throw new Error('Failed to fetch new arrivals');
            
            const data = await response.json();
            
            if (data.products && data.products.length > 0) {
                // Remove welcome card and show products
                document.querySelector('.welcome-card')?.remove();
                document.querySelector('.quick-actions')?.remove();
                
                // Check if we already have a new arrivals section
                let newArrivalsSection = document.querySelector('.new-arrivals-section');
                
                if (!newArrivalsSection) {
                    // Create new arrivals section if it doesn't exist
                    newArrivalsSection = document.createElement('div');
                    newArrivalsSection.className = 'new-arrivals-section';
                    chatMessagesDiv.appendChild(newArrivalsSection);
                }
                
                // Clear previous content in the section
                newArrivalsSection.innerHTML = '';
                
                // Add header
                const header = document.createElement('div');
                header.className = 'section-header';
                header.innerHTML = `
                    <h2>New Arrivals</h2>
                    <p>Discover our latest jewelry pieces</p>
                `;
                newArrivalsSection.appendChild(header);
                
                // Show products
                const productContainer = document.createElement('div');
                productContainer.className = 'product-cards-container';
                
                data.products.forEach(product => {
                    const card = document.createElement('div');
                    card.className = 'product-card animate__animated animate__fadeInUp';
                    
                    // Defensive checks for potentially missing or malformed data
                    const imageUrl = product.image_url || 'https://via.placeholder.com/340x200/cccccc/FFFFFF?Text=No+Image';
                    const name = product.name || 'Unnamed Product';
                    const price = typeof product.price === 'number' ? `$${product.price.toFixed(2)}` : 'Price not available';
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
                
                newArrivalsSection.appendChild(productContainer);
                
                // Add pagination controls at the bottom
                if (data.total_pages > 1) {
                    const paginationContainer = document.createElement('div');
                    paginationContainer.className = 'pagination-container';
                    paginationContainer.innerHTML = `
                        <div class="pagination-info">
                            <span>Page ${page} of ${data.total_pages}</span>
                            <span>•</span>
                            <span>${data.total_products} products total</span>
                        </div>
                        <div class="pagination-controls">
                            ${page > 1 ? `<button class="pagination-btn prev-btn" data-page="${page - 1}">← Previous</button>` : ''}
                            <div class="page-numbers">
                                ${generatePageNumbers(page, data.total_pages)}
                            </div>
                            ${page < data.total_pages ? `<button class="pagination-btn next-btn" data-page="${page + 1}">Next →</button>` : ''}
                        </div>
                    `;
                    
                    // Add event listeners for pagination buttons
                    paginationContainer.querySelectorAll('.pagination-btn').forEach(btn => {
                        btn.addEventListener('click', () => {
                            const targetPage = parseInt(btn.dataset.page);
                            showNewArrivals(targetPage);
                        });
                    });
                    
                    // Add event listeners for page number buttons
                    paginationContainer.querySelectorAll('.page-number').forEach(btn => {
                        btn.addEventListener('click', () => {
                            const targetPage = parseInt(btn.dataset.page);
                            showNewArrivals(targetPage);
                        });
                    });
                    
                    newArrivalsSection.appendChild(paginationContainer);
                }
                
                // Add action buttons at the very bottom
                const actionButtons = [
                    { label: "Back to Menu", value: "back-to-menu" },
                    { label: "Type your answer", value: "__type__" }
                ];
                displayInteractiveBubbles(actionButtons);
                
                setUiMode('chat');
                scrollToBottom();
            } else {
                appendMessage('No new arrivals found at the moment. Please check back later!', 'assistant');
                setUiMode('text_input_only');
            }
        } catch (error) {
            console.error('Error fetching new arrivals:', error);
            appendMessage('Sorry, I couldn\'t fetch the new arrivals. Please try again.', 'assistant');
            setUiMode('text_input_only');
        }
    }

    // Helper function to generate page numbers
    function generatePageNumbers(currentPage, totalPages) {
        let pageNumbers = '';
        const maxVisiblePages = 5;
        
        if (totalPages <= maxVisiblePages) {
            // Show all pages if total is small
            for (let i = 1; i <= totalPages; i++) {
                pageNumbers += `<button class="page-number ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
            }
        } else {
            // Show smart pagination for many pages
            if (currentPage <= 3) {
                // Near start: show 1, 2, 3, 4, 5, ..., last
                for (let i = 1; i <= 5; i++) {
                    pageNumbers += `<button class="page-number ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
                }
                pageNumbers += '<span class="page-ellipsis">...</span>';
                pageNumbers += `<button class="page-number" data-page="${totalPages}">${totalPages}</button>`;
            } else if (currentPage >= totalPages - 2) {
                // Near end: show 1, ..., last-4, last-3, last-2, last-1, last
                pageNumbers += `<button class="page-number" data-page="1">1</button>`;
                pageNumbers += '<span class="page-ellipsis">...</span>';
                for (let i = totalPages - 4; i <= totalPages; i++) {
                    pageNumbers += `<button class="page-number ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
                }
            } else {
                // Middle: show 1, ..., current-1, current, current+1, ..., last
                pageNumbers += `<button class="page-number" data-page="1">1</button>`;
                pageNumbers += '<span class="page-ellipsis">...</span>';
                for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                    pageNumbers += `<button class="page-number ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
                }
                pageNumbers += '<span class="page-ellipsis">...</span>';
                pageNumbers += `<button class="page-number" data-page="${totalPages}">${totalPages}</button>`;
            }
        }
        
        return pageNumbers;
    }

    // Show Collections - Jewelry categories with bigger cards
    async function showCollections() {
        try {
            const response = await fetch('/products/categories', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId })
            });

            if (!response.ok) throw new Error('Failed to fetch categories');
            
            const data = await response.json();
            
            if (data.categories && data.categories.length > 0) {
                // Remove welcome card and show categories
                document.querySelector('.welcome-card')?.remove();
                document.querySelector('.quick-actions')?.remove();
                
                // Check if we already have a collections section
                let collectionsSection = document.querySelector('.collections-section');
                
                if (!collectionsSection) {
                    // Create collections section if it doesn't exist
                    collectionsSection = document.createElement('div');
                    collectionsSection.className = 'collections-section';
                    chatMessagesDiv.appendChild(collectionsSection);
                }
                
                // Clear previous content in the section
                collectionsSection.innerHTML = '';
                
                // Add header
                const header = document.createElement('div');
                header.className = 'section-header';
                header.innerHTML = `
                    <h2>Collections</h2>
                    <p>Browse our jewelry by category</p>
                `;
                collectionsSection.appendChild(header);
                
                // Display category cards
                displayCategoryCards(data.categories, collectionsSection);
                
                // Add action buttons at the bottom of the collections section
                const actionButtonsContainer = document.createElement('div');
                actionButtonsContainer.className = 'collections-actions';
                
                const actionButtons = [
                    { label: "Back to Menu", value: "back-to-menu" },
                    { label: "Type your answer", value: "__type__" }
                ];
                
                // Create action buttons within the collections section
                actionButtons.forEach(action => {
                    const button = document.createElement('button');
                    button.className = 'bubble-button';
                    button.textContent = action.label;
                    button.onclick = () => {
                        if (action.value === 'back-to-menu') {
                            handleBackToMenu();
                        } else if (action.value === '__type__') {
                            setUiMode('text_input_only');
                        }
                    };
                    actionButtonsContainer.appendChild(button);
                });
                
                collectionsSection.appendChild(actionButtonsContainer);
                
                setUiMode('chat');
                scrollToBottom();
            } else {
                appendMessage('No categories found at the moment. Please check back later!', 'assistant');
                setUiMode('text_input_only');
            }
        } catch (error) {
            console.error('Error fetching categories:', error);
            appendMessage('Sorry, I couldn\'t fetch the categories. Please try again.', 'assistant');
            setUiMode('text_input_only');
        }
    }

    // Display category cards (bigger than product cards)
    function displayCategoryCards(categories, parentSection = null) {
        const categoryContainer = document.createElement('div');
        categoryContainer.className = 'category-cards-container animate__animated animate__fadeInUp';
        
        // Limit to 6 categories to fit in the fixed container
        const displayCategories = categories.slice(0, 6);
        
        displayCategories.forEach(category => {
            const card = document.createElement('div');
            card.className = 'category-card';
            card.onclick = () => showCategoryProducts(category.name.toLowerCase());
            
            card.innerHTML = `
                <span class="material-symbols-outlined">${category.icon || 'diamond'}</span>
                <h3>${category.name}</h3>
                <p>${category.description}</p>
                <span class="product-count">${category.product_count} items</span>
            `;
            
            categoryContainer.appendChild(card);
        });
        
        if (parentSection) {
            parentSection.appendChild(categoryContainer);
        } else {
            chatMessagesDiv.appendChild(categoryContainer);
        }
        scrollToBottom();
        return categoryContainer;
    }

    // Get appropriate icon for each category
    function getCategoryIcon(categoryName) {
        const iconMap = {
            'rings': 'diamond',
            'necklaces': 'favorite',
            'earrings': 'star',
            'bracelets': 'circle',
            'watches': 'schedule',
            'pendants': 'favorite_border'
        };
        return iconMap[categoryName.toLowerCase()] || 'category';
    }

    // Show Track Order - Order ID input and demo map
    async function showTrackOrder() {
        // Remove welcome card and show track order interface
        document.querySelector('.welcome-card')?.remove();
        document.querySelector('.quick-actions')?.remove();
        
        const trackOrderContainer = document.createElement('div');
        trackOrderContainer.className = 'track-order-container animate__animated animate__fadeInUp';
        
        trackOrderContainer.innerHTML = `
            <div class="track-order-card">
                <h3>Track Your Order</h3>
                <p>Enter your order ID to track the delivery status</p>
                
                <div class="order-input-section">
                    <input type="text" id="orderIdInput" placeholder="Enter Order ID (e.g., ORD-12345)" class="order-input">
                    <button id="trackOrderBtn" class="track-button">
                        <span class="material-symbols-outlined">search</span>
                        Track Order
                    </button>
                </div>
                
                <div class="demo-map-section" id="demoMapSection" style="display: none;">
                    <h4>Order Status: In Transit</h4>
                    <div class="map-container">
                        <img src="https://via.placeholder.com/400x250/4CAF50/FFFFFF?text=Demo+Map+View" alt="Order Tracking Map" class="demo-map">
                        <div class="tracking-info">
                            <div class="tracking-step active">
                                <span class="step-icon">✓</span>
                                <span>Order Confirmed</span>
                            </div>
                            <div class="tracking-step active">
                                <span class="step-icon">✓</span>
                                <span>Processing</span>
                            </div>
                            <div class="tracking-step active">
                                <span class="step-icon">🚚</span>
                                <span>In Transit</span>
                            </div>
                            <div class="tracking-step">
                                <span class="step-icon">📦</span>
                                <span>Out for Delivery</span>
                            </div>
                            <div class="tracking-step">
                                <span class="step-icon">🏠</span>
                                <span>Delivered</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        chatMessagesDiv.appendChild(trackOrderContainer);
        
        // Add event listeners
        const trackButton = trackOrderContainer.querySelector('#trackOrderBtn');
        const orderInput = trackOrderContainer.querySelector('#orderIdInput');
        const demoMapSection = trackOrderContainer.querySelector('#demoMapSection');
        
        trackButton.addEventListener('click', () => {
            const orderId = orderInput.value.trim();
            if (orderId) {
                trackOrder(orderId, demoMapSection);
            } else {
                orderInput.focus();
                orderInput.style.borderColor = '#ff6b6b';
                setTimeout(() => orderInput.style.borderColor = '', 2000);
            }
        });
        
        orderInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                trackButton.click();
            }
        });
        
        // Add action buttons
        const actionButtons = [
            { label: "Back to Menu", value: "back-to-menu" },
            { label: "Type your answer", value: "__type__" }
        ];
        displayInteractiveBubbles(actionButtons);
        
        setUiMode('chat');
        scrollToBottom();
    }

    // Track order function
    async function trackOrder(orderId, demoMapSection) {
        try {
            // Show loading state
            const trackButton = document.querySelector('#trackOrderBtn');
            const originalText = trackButton.innerHTML;
            trackButton.innerHTML = '<span class="material-symbols-outlined">hourglass_empty</span> Tracking...';
            trackButton.disabled = true;
            
            // Simulate API call delay
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Show demo map and tracking info
            demoMapSection.style.display = 'block';
            demoMapSection.scrollIntoView({ behavior: 'smooth' });
            
            // Track user interaction
            trackUserInteraction('order_tracked', { order_id: orderId });
            
            // Reset button
            trackButton.innerHTML = originalText;
            trackButton.disabled = false;
            
        } catch (error) {
            console.error('Error tracking order:', error);
            appendMessage('Sorry, there was an error tracking your order. Please try again.', 'assistant');
        }
    }

    // Show Store Locator - Real store location with map
    async function showStoreLocator() {
        // Remove welcome card and show store locator
        document.querySelector('.welcome-card')?.remove();
        document.querySelector('.quick-actions')?.remove();
        
        const storeLocatorContainer = document.createElement('div');
        storeLocatorContainer.className = 'store-locator-container animate__animated animate__fadeInUp';
        
        storeLocatorContainer.innerHTML = `
            <div class="store-locator-card">
                <h3>Store Location</h3>
                <p>Visit our flagship store in the heart of the city</p>
                
                <div class="store-map-section">
                    <div class="map-container">
                        <img src="https://via.placeholder.com/400x250/2196F3/FFFFFF?text=Store+Location+Map" alt="Store Location Map" class="store-map">
                        <div class="map-overlay">
                            <div class="location-pin">📍</div>
                        </div>
                    </div>
                    
                    <div class="store-info">
                        <h4>Joxy Luxury Jewelry</h4>
                        <div class="store-details">
                            <div class="detail-item">
                                <span class="material-symbols-outlined">location_on</span>
                                <span>123 Luxury Avenue, Downtown District</span>
                            </div>
                            <div class="detail-item">
                                <span class="material-symbols-outlined">schedule</span>
                                <span>Mon-Sat: 10:00 AM - 8:00 PM</span>
                            </div>
                            <div class="detail-item">
                                <span class="material-symbols-outlined">phone</span>
                                <span>+1 (555) 123-4567</span>
                            </div>
                            <div class="detail-item">
                                <span class="material-symbols-outlined">email</span>
                                <span>info@joxyjewelry.com</span>
                            </div>
                        </div>
                        
                        <div class="store-actions">
                            <button class="action-btn directions-btn">
                                <span class="material-symbols-outlined">directions</span>
                                Get Directions
                            </button>
                            <button class="action-btn call-btn">
                                <span class="material-symbols-outlined">call</span>
                                Call Store
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        chatMessagesDiv.appendChild(storeLocatorContainer);
        
        // Add event listeners for store actions
        const directionsBtn = storeLocatorContainer.querySelector('.directions-btn');
        const callBtn = storeLocatorContainer.querySelector('.call-btn');
        
        directionsBtn.addEventListener('click', () => {
            // Open Google Maps with store location
            const address = encodeURIComponent('123 Luxury Avenue, Downtown District');
            window.open(`https://www.google.com/maps/search/?api=1&query=${address}`, '_blank');
            trackUserInteraction('get_directions_clicked');
        });
        
        callBtn.addEventListener('click', () => {
            // Initiate phone call
            window.location.href = 'tel:+15551234567';
            trackUserInteraction('call_store_clicked');
        });
        
        // Add action buttons
        const actionButtons = [
            { label: "Back to Menu", value: "back-to-menu" },
            { label: "Type your answer", value: "__type__" }
        ];
        displayInteractiveBubbles(actionButtons);
        
        setUiMode('chat');
        scrollToBottom();
    }

    // Display pagination controls
    function displayPaginationControls(type, currentPage, totalPages, totalProducts) {
        const paginationContainer = document.createElement('div');
        paginationContainer.className = 'pagination-container';
        
        let paginationHTML = `<div class="pagination-info">Showing page ${currentPage} of ${totalPages} (${totalProducts} total products)</div>`;
        
        if (totalPages > 1) {
            paginationHTML += '<div class="pagination-buttons">';
            
            if (currentPage > 1) {
                paginationHTML += `<button class="pagination-btn" data-page="${currentPage - 1}" data-type="${type}">← Previous</button>`;
            }
            
            // Show page numbers
            for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
                const activeClass = i === currentPage ? 'active' : '';
                paginationHTML += `<button class="pagination-btn ${activeClass}" data-page="${i}" data-type="${type}">${i}</button>`;
            }
            
            if (currentPage < totalPages) {
                paginationHTML += `<button class="pagination-btn" data-page="${currentPage + 1}" data-type="${type}">Next →</button>`;
            }
            
            paginationHTML += '</div>';
        }
        
        paginationContainer.innerHTML = paginationHTML;
        
        // Add event listeners
        paginationContainer.querySelectorAll('.pagination-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = parseInt(btn.dataset.page);
                const type = btn.dataset.type;
                
                if (type === 'new-arrivals') {
                    showNewArrivals(page);
                }
            });
        });
        
        chatMessagesDiv.appendChild(paginationContainer);
    }

    // Show products from a specific category
    async function showCategoryProducts(categoryName, page = 1) {
        try {
            const response = await fetch('/products/category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    session_id: sessionId, 
                    category: categoryName,
                    page: page,
                    limit: 5 
                })
            });

            if (!response.ok) throw new Error('Failed to fetch category products');
            
            const data = await response.json();
            
            if (data.products && data.products.length > 0) {
                // Check if we already have a category products section
                let categorySection = document.querySelector('.category-products-section');
                
                if (!categorySection) {
                    // Create category products section if it doesn't exist
                    categorySection = document.createElement('div');
                    categorySection.className = 'category-products-section';
                    chatMessagesDiv.appendChild(categorySection);
                }
                
                // Clear previous content in the section
                categorySection.innerHTML = '';
                
                // Add header
                const header = document.createElement('div');
                header.className = 'section-header';
                header.innerHTML = `
                    <h2>${categoryName.charAt(0).toUpperCase() + categoryName.slice(1)}</h2>
                    <p>Browse our ${categoryName.toLowerCase()} collection</p>
                `;
                categorySection.appendChild(header);
                
                // Show products
                const productContainer = document.createElement('div');
                productContainer.className = 'product-cards-container';
                
                data.products.forEach(product => {
                    const card = document.createElement('div');
                    card.className = 'product-card animate__animated animate__fadeInUp';
                    
                    // Defensive checks for potentially missing or malformed data
                    const imageUrl = product.image_url || 'https://via.placeholder.com/340x200/cccccc/FFFFFF?Text=No+Image';
                    const name = product.name || 'Unnamed Product';
                    const price = typeof product.price === 'number' ? `$${product.price.toFixed(2)}` : 'Price not available';
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
                
                categorySection.appendChild(productContainer);
                
                // Add pagination controls at the bottom
                if (data.total_pages > 1) {
                    const paginationContainer = document.createElement('div');
                    paginationContainer.className = 'pagination-container';
                    paginationContainer.innerHTML = `
                        <div class="pagination-info">
                            <span>Page ${page} of ${data.total_pages}</span>
                            <span>•</span>
                            <span>${data.total_products} products total</span>
                        </div>
                        <div class="pagination-controls">
                            ${page > 1 ? `<button class="pagination-btn prev-btn" data-page="${page - 1}">← Previous</button>` : ''}
                            <div class="page-numbers">
                                ${generatePageNumbers(page, data.total_pages)}
                            </div>
                            ${page < data.total_pages ? `<button class="pagination-btn next-btn" data-page="${page + 1}">Next →</button>` : ''}
                        </div>
                    `;
                    
                    // Add event listeners for pagination buttons
                    paginationContainer.querySelectorAll('.pagination-btn').forEach(btn => {
                        btn.addEventListener('click', () => {
                            const targetPage = parseInt(btn.dataset.page);
                            showCategoryProducts(categoryName, targetPage);
                        });
                    });
                    
                    // Add event listeners for page number buttons
                    paginationContainer.querySelectorAll('.page-number').forEach(btn => {
                        btn.addEventListener('click', () => {
                            const targetPage = parseInt(btn.dataset.page);
                            showCategoryProducts(categoryName, targetPage);
                        });
                    });
                    
                    categorySection.appendChild(paginationContainer);
                }
                
                // Add action buttons at the very bottom
                const actionButtons = [
                    { label: "Back to Collections", value: "back-to-collections" },
                    { label: "Back to Menu", value: "back-to-menu" },
                    { label: "Type your answer", value: "__type__" }
                ];
                displayInteractiveBubbles(actionButtons);
                
                setUiMode('chat');
                scrollToBottom();
            } else {
                appendMessage(`No ${categoryName} products found at the moment. Please check back later!`, 'assistant');
                setUiMode('text_input_only');
            }
        } catch (error) {
            console.error('Error fetching category products:', error);
            appendMessage('Sorry, I couldn\'t fetch the category products. Please try again.', 'assistant');
            setUiMode('text_input_only');
        }
    }

    // Handle back to menu functionality
    function handleBackToMenu() {
        // Clear all content
        document.querySelector('.welcome-card')?.remove();
        document.querySelector('.quick-actions')?.remove();
        document.querySelector('.new-arrivals-section')?.remove();
        document.querySelector('.collections-section')?.remove();
        document.querySelector('.category-products-section')?.remove();
        document.querySelector('.track-order-section')?.remove();
        document.querySelector('.store-locator-section')?.remove();
        document.querySelector('.product-cards-container')?.remove();
        document.querySelector('.pagination-container')?.remove();
        
        // Recreate initial view
        createInitialView();
        setUiMode('text_input_only');
        scrollToTop();
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
            resetConversation();
        }
    });

    // Initialize - Create welcome card immediately
    updateGreeting();
    createInitialView();
    setUiMode('text_input_only');
});