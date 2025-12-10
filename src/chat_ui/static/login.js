// DOM Elements
const loginForm = document.getElementById('login-form');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginBtn = document.getElementById('login-btn');
const errorMessage = document.getElementById('error-message');

const authApiUrl = '';

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Check if already logged in
    const token = localStorage.getItem('authToken');
    if (token) {
        // Already logged in, redirect to chat
        window.location.href = '/';
        return;
    }

    // Setup form submission
    loginForm.addEventListener('submit', handleLogin);
});

/**
 * Handle login form submission
 */
async function handleLogin(event) {
    event.preventDefault();

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    if (!username || !password) {
        showError('Vui long nhap day du thong tin');
        return;
    }

    // Show loading state
    setLoading(true);
    hideError();

    try {
        const authUrl = `${authApiUrl}/api/login`;
        console.log('Logging in to:', authUrl);

        const response = await fetch(authUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();
        console.log('Login response:', data);

        // Check for success (status "00" from ResponseFormat)
        if (data.status === '00' && data.data) {
            // Store auth data in localStorage
            localStorage.setItem('authToken', data.data.access_token);
            localStorage.setItem('userId', data.data.user_id);
            localStorage.setItem('username', data.data.username);

            console.log('Login successful, redirecting to chat...');

            // Redirect to chat page
            window.location.href = '/';
        } else {
            // Login failed
            showError(data.message || 'Dang nhap that bai');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Loi ket noi. Vui long thu lai.');
    } finally {
        setLoading(false);
    }
}

/**
 * Show error message
 */
function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
}

/**
 * Hide error message
 */
function hideError() {
    errorMessage.textContent = '';
    errorMessage.style.display = 'none';
}

/**
 * Set loading state
 */
function setLoading(loading) {
    loginBtn.disabled = loading;
    const btnText = loginBtn.querySelector('.btn-text');
    const btnLoading = loginBtn.querySelector('.btn-loading');

    if (loading) {
        btnText.style.display = 'none';
        btnLoading.style.display = 'inline-flex';
    } else {
        btnText.style.display = 'inline';
        btnLoading.style.display = 'none';
    }
}
