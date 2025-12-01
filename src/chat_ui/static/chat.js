/**
 * Chat UI JavaScript
 * Handles chat messages and WebSocket notifications
 */

// State
let sessionId = localStorage.getItem('sessionId') || generateUUID();
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
    // Display session ID
    sessionIdDisplay.textContent = sessionId.substring(0, 8) + '...';
    localStorage.setItem('sessionId', sessionId);

    // Load config
    await loadConfig();

    // Connect WebSocket
    connectWebSocket();

    // Setup event listeners
    setupEventListeners();
});

/**
 * Generate a UUID v4
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
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
    const wsUrl = `${config?.ws_url || 'ws://localhost:8084'}/ws/${sessionId}`;
    console.log('Connecting to WebSocket:', wsUrl);

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);
        };

        ws.onmessage = (event) => {
            console.log('WebSocket message:', event.data);
            try {
                const notification = JSON.parse(event.data);
                handleNotification(notification);
            } catch (error) {
                console.error('Failed to parse notification:', error);
            }
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            updateConnectionStatus(false);
            // Reconnect after 3 seconds
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
}

/**
 * Send message to agent
 */
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Clear input
    messageInput.value = '';

    // Add user message to chat
    addMessage(message, 'user');

    // Show typing indicator
    showTypingIndicator();

    // Disable send button
    sendBtn.disabled = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: message
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Remove typing indicator
        hideTypingIndicator();

        // Add agent response
        addMessage(data.response, 'agent');

    } catch (error) {
        console.error('Failed to send message:', error);
        hideTypingIndicator();
        addMessage('Sorry, an error occurred. Please try again.', 'agent');
        showToast('Failed to send message', 'error');
    } finally {
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
    // Generate new session ID
    sessionId = generateUUID();
    localStorage.setItem('sessionId', sessionId);
    sessionIdDisplay.textContent = sessionId.substring(0, 8) + '...';

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
