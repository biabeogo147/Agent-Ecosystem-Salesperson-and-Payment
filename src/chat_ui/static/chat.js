// State
let sessionId = localStorage.getItem('sessionId') || generateUUID();  // WebSocket session ID
let conversationId = localStorage.getItem('conversationId')
    ? parseInt(localStorage.getItem('conversationId'))
    : null;  // DB conversation ID (null for new, int for existing)
let ws = null;
let config = null;

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const sessionIdDisplay = document.getElementById('session-id');
const newSessionBtn = document.getElementById('new-session-btn');
const wsStatus = document.getElementById('ws-status');
const wsStatusText = document.getElementById('ws-status-text');
const notificationsList = document.getElementById('notifications');
const toastContainer = document.getElementById('toast-container');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication
    if (!checkAuth()) {
        return; // Will redirect to login
    }

    // Display user info
    displayUserInfo();

    // Display conversation ID (or "New" if null)
    updateConversationDisplay();
    localStorage.setItem('sessionId', sessionId);

    // Load config
    await loadConfig();

    // Connect WebSocket
    connectWebSocket();

    // Setup event listeners
    setupEventListeners();
});

/**
 * Update conversation ID display
 */
function updateConversationDisplay() {
    if (conversationId) {
        sessionIdDisplay.textContent = `Conv #${conversationId}`;
    } else {
        sessionIdDisplay.textContent = 'New Chat';
    }
}

/**
 * Check if user is authenticated
 */
function checkAuth() {
    const token = localStorage.getItem('authToken');
    if (!token) {
        console.log('No auth token found, redirecting to login');
        window.location.href = '/login';
        return false;
    }
    return true;
}

/**
 * Display user info in header
 */
function displayUserInfo() {
    const username = localStorage.getItem('username');
    const usernameDisplay = document.getElementById('username-display');
    if (usernameDisplay && username) {
        usernameDisplay.textContent = username;
    }
}

/**
 * Logout user
 */
function logout() {
    // Clear auth data
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('username');

    // Close WebSocket
    if (ws) {
        ws.close();
    }

    // Redirect to login
    window.location.href = '/login';
}

/**
 * Get authorization headers with Bearer token
 */
function getAuthHeaders() {
    const token = localStorage.getItem('authToken');
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };
}

/**
 * Generate a UUID v4 (for WebSocket session ID only)
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Load configuration from server
 */
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        config = await response.json();
        console.log('Config loaded:', config);
    } catch (error) {
        console.error('Failed to load config:', error);
        config = {
            ws_url: 'ws://localhost:8084'
        };
    }
}

/**
 * Connect to WebSocket server
 */
function connectWebSocket() {
    const token = localStorage.getItem('authToken');

    // Redirect to login if no token
    if (!token) {
        console.log('No auth token, redirecting to login');
        window.location.href = '/login';
        return;
    }

    // Build WebSocket URL with token (sessionId is for WS session, not conversation)
    const wsUrl = `${config?.ws_url || 'ws://localhost:8084'}/ws/${sessionId}?token=${encodeURIComponent(token)}`;
    console.log('Connecting to WebSocket:', wsUrl.replace(token, '***'));

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);

            // Send register message with conversation_id (null for new, int for existing)
            const registerMessage = {
                type: 'register',
                conversation_id: conversationId  // null or integer
            };
            ws.send(JSON.stringify(registerMessage));
            console.log('Sent register message:', registerMessage);
        };

        ws.onmessage = (event) => {
            console.log('WebSocket message:', event.data);
            try {
                const message = JSON.parse(event.data);

                // Handle different message types
                switch (message.type) {
                    case 'registered':
                        console.log('Session registered:', message);
                        showToast('Connected to notification server', 'success');
                        break;

                    case 'chat_response':
                        // Chat response from agent (complete message)
                        console.log('Chat response received:', message);
                        hideTypingIndicator();

                        // Store conversation_id from server (important for new chats)
                        if (message.conversation_id && message.conversation_id !== conversationId) {
                            conversationId = message.conversation_id;
                            localStorage.setItem('conversationId', conversationId);
                            updateConversationDisplay();
                            console.log('Stored new conversation_id:', conversationId);
                        }

                        if (message.content) {
                            addMessage(message.content, 'agent');
                        }
                        sendBtn.disabled = false;
                        messageInput.focus();
                        break;

                    case 'chat_token':
                        // Streaming token (TODO: implement utils UI)
                        console.log('Streaming token:', message.token);
                        break;

                    case 'payment_status':
                        // Payment notification
                        console.log('Payment status update:', message);
                        handleNotification(message);
                        break;

                    case 'error':
                        console.error('WebSocket error message:', message);
                        hideTypingIndicator();
                        showToast(message.message || 'Connection error', 'error');
                        sendBtn.disabled = false;
                        break;

                    case 'pong':
                        // Heartbeat response, ignore
                        break;

                    default:
                        console.warn('Unknown message type:', message.type);
                        // Try to handle as notification for backward compatibility
                        if (message.order_id) {
                            handleNotification(message);
                        }
                }
            } catch (error) {
                console.error('Failed to parse message:', error);
            }
        };

        ws.onclose = (event) => {
            console.log('WebSocket disconnected, code:', event.code);
            updateConnectionStatus(false);

            // Check for auth errors (4001 = missing token, 4002 = invalid token)
            if (event.code === 4001 || event.code === 4002) {
                console.log('Auth error, redirecting to login');
                logout();
                return;
            }

            // Reconnect after 3 seconds for other disconnections
            setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateConnectionStatus(false);
        };
    } catch (error) {
        console.error('Failed to connect WebSocket:', error);
        updateConnectionStatus(false);
    }
}

/**
 * Update connection status UI
 */
function updateConnectionStatus(connected) {
    if (connected) {
        wsStatus.classList.remove('disconnected');
        wsStatus.classList.add('connected');
        wsStatusText.textContent = 'Connected';
    } else {
        wsStatus.classList.remove('connected');
        wsStatus.classList.add('disconnected');
        wsStatusText.textContent = 'Disconnected';
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Send message on button click
    sendBtn.addEventListener('click', sendMessage);

    // Send message on Enter key
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // New session button
    newSessionBtn.addEventListener('click', () => {
        if (confirm('Start a new session? This will clear the chat history.')) {
            startNewSession();
        }
    });

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to logout?')) {
                logout();
            }
        });
    }
}

/**
 * Send message to agent
 */
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Check if WebSocket is connected
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showToast('Not connected to server. Reconnecting...', 'error');
        connectWebSocket();
        return;
    }

    // Clear input
    messageInput.value = '';

    // Add user message to chat
    addMessage(message, 'user');

    // Show typing indicator
    showTypingIndicator();

    // Disable send button
    sendBtn.disabled = true;

    try {
        // Send message via WebSocket
        // conversation_id can be null (new) or int (existing)
        const chatMessage = {
            type: 'chat',
            message: message,
            conversation_id: conversationId  // null or integer
        };

        ws.send(JSON.stringify(chatMessage));
        console.log('Sent chat message via WebSocket:', chatMessage);

        // Response will be handled by ws.onmessage handler
        // Server will return conversation_id in response for new chats

    } catch (error) {
        console.error('Failed to send message:', error);
        hideTypingIndicator();
        showToast('Failed to send message', 'error');
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

/**
 * Add a message to the chat
 */
function addMessage(text, role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = text;

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message agent typing';
    typingDiv.id = 'typing-indicator';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';

    contentDiv.appendChild(indicator);
    typingDiv.appendChild(contentDiv);
    chatMessages.appendChild(typingDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Hide typing indicator
 */
function hideTypingIndicator() {
    const typingDiv = document.getElementById('typing-indicator');
    if (typingDiv) {
        typingDiv.remove();
    }
}

/**
 * Handle incoming notification
 */
function handleNotification(notification) {
    console.log('Handling notification:', notification);

    // Add to notifications list
    addNotificationItem(notification);

    // Show toast
    const statusText = getStatusText(notification.status);
    showToast(`Payment ${statusText}: Order ${notification.order_id}`, getStatusType(notification.status));

    // Also add to chat as a system message
    const chatMessage = `Payment Update: Order ${notification.order_id} - ${statusText}`;
    addSystemMessage(chatMessage, notification.status);
}

/**
 * Add notification item to panel
 */
function addNotificationItem(notification) {
    // Remove empty state if present
    const emptyState = notificationsList.querySelector('.empty-state');
    if (emptyState) {
        emptyState.remove();
    }

    const item = document.createElement('div');
    item.className = `notification-item ${notification.status.toLowerCase()}`;

    const statusText = getStatusText(notification.status);
    const timestamp = new Date(notification.timestamp).toLocaleTimeString('vi-VN');

    item.innerHTML = `
        <div class="status">${statusText}</div>
        <div class="order-id">Order: ${notification.order_id}</div>
        <div class="timestamp">${timestamp}</div>
    `;

    // Add to top of list
    notificationsList.insertBefore(item, notificationsList.firstChild);
}

/**
 * Add system message to chat
 */
function addSystemMessage(text, status) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message agent';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.style.background = getStatusColor(status);
    contentDiv.style.color = 'white';
    contentDiv.innerHTML = `<strong>${text}</strong>`;

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

/**
 * Get status text in Vietnamese
 */
function getStatusText(status) {
    const statusMap = {
        'SUCCESS': 'Thanh toan thanh cong',
        'CANCELLED': 'Da huy',
        'FAILED': 'That bai',
        'PENDING': 'Dang xu ly'
    };
    return statusMap[status] || status;
}

/**
 * Get status type for toast
 */
function getStatusType(status) {
    const typeMap = {
        'SUCCESS': 'success',
        'CANCELLED': 'warning',
        'FAILED': 'error',
        'PENDING': 'warning'
    };
    return typeMap[status] || 'info';
}

/**
 * Get status color
 */
function getStatusColor(status) {
    const colorMap = {
        'SUCCESS': '#22c55e',
        'CANCELLED': '#ef4444',
        'FAILED': '#ef4444',
        'PENDING': '#f59e0b'
    };
    return colorMap[status] || '#6b7280';
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    toastContainer.appendChild(toast);

    // Remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

/**
 * Start a new chat session
 */
function startNewSession() {
    // Clear conversation ID (server will create new one)
    conversationId = null;
    localStorage.removeItem('conversationId');

    // Generate new WebSocket session ID
    sessionId = generateUUID();
    localStorage.setItem('sessionId', sessionId);

    // Update display
    updateConversationDisplay();

    // Clear chat messages (keep welcome message)
    chatMessages.innerHTML = `
        <div class="message agent">
            <div class="message-content">
                Xin chao! Toi la tro ly ban hang. Toi co the giup gi cho ban?
            </div>
        </div>
    `;

    // Clear notifications
    notificationsList.innerHTML = `
        <div class="empty-state">
            Chua co thong bao thanh toan
        </div>
    `;

    // Reconnect WebSocket with new context
    if (ws) {
        ws.close();
    }
    connectWebSocket();

    showToast('New session started', 'success');
}
