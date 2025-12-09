// State
let sessionId = localStorage.getItem('sessionId') || generateUUID();  // WebSocket session ID
let conversationId = localStorage.getItem('conversationId')
    ? parseInt(localStorage.getItem('conversationId'))
    : null;  // DB conversation ID (null for new, int for existing)
let ws = null;
let conversations = [];
let apiGateway = 'localhost:8084';
let wsApiGateway = `ws://${apiGateway}`;
let httpApiGateway = `http://${apiGateway}`;

// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const sessionIdDisplay = document.getElementById('session-id');
const newSessionBtn = document.getElementById('new-session-btn');
const wsStatus = document.getElementById('ws-status');
const wsStatusText = document.getElementById('ws-status-text');
const toastContainer = document.getElementById('toast-container');
const conversationList = document.getElementById('conversation-list');
const newChatBtn = document.getElementById('new-chat-btn');

document.addEventListener('DOMContentLoaded', async () => {
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,       // Convert \n to <br>
            gfm: true,          // GitHub Flavored Markdown
            headerIds: false,   // Don't add IDs to headers
            mangle: false       // Don't escape email addresses
        });
    }

    // Check authentication
    if (!checkAuth()) {
        return; // Will redirect to login
    }

    // Display user info
    displayUserInfo();

    // Display conversation ID (or "New" if null)
    updateConversationDisplay();
    localStorage.setItem('sessionId', sessionId);

    // Load conversation list
    await loadConversations();

    if (conversationId) {
        await loadConversationHistory(conversationId);
    }

    // Connect WebSocket
    connectWebSocket();

    // Setup event listeners
    setupEventListeners();
});

// TODO: có lỗi, một mở một tab nhưng lại có 2 connections trên cùng 1 sessionId, khi đẩy notification sẽ bị nhận 2 lần nếu 2 connection trên cùng 1 tab.
// TODO: xem các hàm không cần thiết
// TODO: viết thêm chat_app.py để gọi API sang service khác chứ không gọi trực tiếp trong JS

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
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('username');

    if (ws) {
        ws.close();
    }

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
    const wsUrl = `${wsApiGateway}/ws/${sessionId}?token=${encodeURIComponent(token)}`;
    console.log('Connecting to WebSocket:', wsUrl.replace(token, '***'));

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('WebSocket connected');
            updateConnectionStatus(true);

            // Only send register if we have an existing conversation
            if (conversationId) {
                const registerMessage = {
                    type: 'register',
                    conversation_id: conversationId
                };
                ws.send(JSON.stringify(registerMessage));
                console.log('Sent register message:', registerMessage);
            } else {
                // New chat - don't send register, wait for first chat message
                console.log('New chat - waiting for first message to create conversation');
                showToast('Ready for new chat', 'success');
            }
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
                            // Reload conversation list to include new conversation
                            loadConversations();
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

    // New chat button in sidebar
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            startNewSession();
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

    // Render markdown for agent messages, plain text for user messages
    if (role === 'agent' && typeof marked !== 'undefined') {
        const html = marked.parse(text);
        contentDiv.innerHTML = DOMPurify.sanitize(html);
        // Apply syntax highlighting to code blocks
        contentDiv.querySelectorAll('pre code').forEach((block) => {
            if (typeof hljs !== 'undefined') {
                hljs.highlightElement(block);
            }
        });
    } else {
        contentDiv.textContent = text;
    }

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

    // Show toast
    const statusText = getStatusText(notification.status);
    showToast(`Payment ${statusText}: Order ${notification.order_id}`, getStatusType(notification.status));

    // Also add to chat as a system message
    const chatMessage = `Payment Update: Order ${notification.order_id} - ${statusText}`;
    addSystemMessage(chatMessage, notification.status);
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
    renderConversationList();

    // Clear chat messages (keep welcome message)
    chatMessages.innerHTML = `
        <div class="message agent">
            <div class="message-content">
                Xin chao! Toi la tro ly ban hang. Toi co the giup gi cho ban?
            </div>
        </div>
    `;

    // Reconnect WebSocket with new context
    if (ws) {
        ws.close();
    }
    connectWebSocket();

    showToast('New session started', 'success');
}

/**
 * Load user's conversations from server
 */
async function loadConversations() {
    try {
        const response = await fetch(`${httpApiGateway}/auth/conversations?limit=20`, {
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            logout();
            return;
        }

        const result = await response.json();
        if (result.status === '00') {
            conversations = result.data || [];
            renderConversationList();
        } else {
            console.error('Failed to load conversations:', result.message);
            conversationList.innerHTML = `
                <div class="empty-state">Failed to load conversations</div>
            `;
        }
    } catch (error) {
        console.error('Failed to load conversations:', error);
        conversationList.innerHTML = `
            <div class="empty-state">Failed to load conversations</div>
        `;
    }
}

/**
 * Render conversation list in sidebar
 */
function renderConversationList() {
    if (!conversationList) return;

    if (conversations.length === 0) {
        conversationList.innerHTML = `
            <div class="empty-state">No conversations yet. Start chatting!</div>
        `;
        return;
    }

    conversationList.innerHTML = conversations.map(conv => `
        <div class="conversation-item ${conv.id === conversationId ? 'active' : ''}"
             data-id="${conv.id}"
             onclick="selectConversation(${conv.id})">
            <div class="title">${escapeHtml(conv.title)}</div>
            ${conv.updated_at ? `<div class="time">${formatTime(conv.updated_at)}</div>` : ''}
        </div>
    `).join('');
}

/**
 * Select a conversation and load its history
 */
async function selectConversation(id) {
    if (id === conversationId) return;

    conversationId = id;
    localStorage.setItem('conversationId', id);
    updateConversationDisplay();
    renderConversationList();

    // Load history for selected conversation
    await loadConversationHistory(id);

    // Re-register WebSocket for new conversation
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'register',
            conversation_id: id
        }));
    }
}

/**
 * Load conversation history from server
 */
async function loadConversationHistory(convId) {
    // Clear current messages and show loading
    chatMessages.innerHTML = `
        <div class="loading-state">Loading messages...</div>
    `;

    try {
        const response = await fetch(`${httpApiGateway}/auth/conversations/${convId}/messages?limit=50`, {
            headers: getAuthHeaders()
        });

        if (response.status === 401) {
            logout();
            return;
        }

        if (response.status === 404) {
            showToast('Conversation not found', 'error');
            startNewSession();
            return;
        }

        const result = await response.json();

        // Clear loading
        chatMessages.innerHTML = '';

        if (result.status === '00' && result.data) {
            const { messages } = result.data;

            // Add welcome message first
            addMessage('Xin chao! Toi la tro ly ban hang. Toi co the giup gi cho ban?', 'agent');

            // Render history messages
            messages.forEach(msg => {
                const role = msg.role === 'user' ? 'user' : 'agent';
                addMessage(msg.content, role);
            });

            // Scroll to bottom
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else {
            // Empty conversation - show welcome message
            addMessage('Xin chao! Toi la tro ly ban hang. Toi co the giup gi cho ban?', 'agent');
        }
    } catch (error) {
        console.error('Failed to load conversation history:', error);
        chatMessages.innerHTML = `
            <div class="message agent">
                <div class="message-content">
                    Xin chao! Toi la tro ly ban hang. Toi co the giup gi cho ban?
                </div>
            </div>
        `;
        showToast('Failed to load history', 'error');
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format timestamp to relative time or locale string
 */
function formatTime(isoString) {
    if (!isoString) return '';

    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('vi-VN');
}
