/**
 * Authentication functionality for FaceGuard application
 * Handles form validation and submission for login and registration
 */

// DOM elements for forms and validation
document.addEventListener('DOMContentLoaded', () => {
    // Identify which form is present on the page
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    // Setup appropriate form handlers
    if (loginForm) setupLoginForm(loginForm);
    if (registerForm) setupRegisterForm(registerForm);
});

/**
 * Set up login form validation and submission
 * @param {HTMLFormElement} form - The login form element
 */
function setupLoginForm(form) {
    const emailInput = form.querySelector('#email');
    const passwordInput = form.querySelector('#password');
    const submitButton = form.querySelector('button[type="submit"]');
    
    // Add input event listeners for real-time validation
    emailInput.addEventListener('input', () => {
        validateEmail(emailInput);
        toggleSubmitButton(form, submitButton);
    });
    
    passwordInput.addEventListener('input', () => {
        validateRequired(passwordInput, 'Password is required');
        toggleSubmitButton(form, submitButton);
    });
    
    // Form submission handler
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        // Perform final validation before submission
        const isEmailValid = validateEmail(emailInput);
        const isPasswordValid = validateRequired(passwordInput, 'Password is required');
        
        if (isEmailValid && isPasswordValid) {
            // Show loading state
            submitButton.textContent = 'Logging in...';
            submitButton.disabled = true;
            
            // Simulate API call (replace with actual API call)
            setTimeout(() => {
                // For demonstration, we'll just show a success message
                const successMessage = document.querySelector('.success-message');
                if (successMessage) {
                    successMessage.textContent = 'Login successful! Redirecting...';
                    successMessage.style.display = 'block';
                    
                    // Redirect after delay (replace with actual redirect)
                    setTimeout(() => {
                        window.location.href = '../templates/index.html';
                    }, 2000);
                }
            }, 1500);
        } else {
            // If validation fails, ensure errors are shown
            validateEmail(emailInput);
            validateRequired(passwordInput, 'Password is required');
        }
    });
}

/**
 * Set up registration form validation and submission
 * @param {HTMLFormElement} form - The registration form element
 */
function setupRegisterForm(form) {
    const usernameInput = form.querySelector('#username');
    const emailInput = form.querySelector('#email');
    const passwordInput = form.querySelector('#password');
    const confirmPasswordInput = form.querySelector('#confirmPassword');
    const submitButton = form.querySelector('button[type="submit"]');
    
    // Add input event listeners for real-time validation
    usernameInput.addEventListener('input', () => {
        validateRequired(usernameInput, 'Username is required');
        toggleSubmitButton(form, submitButton);
    });
    
    emailInput.addEventListener('input', () => {
        validateEmail(emailInput);
        toggleSubmitButton(form, submitButton);
    });
    
    passwordInput.addEventListener('input', () => {
        validatePassword(passwordInput);
        // If confirm password has value, validate matching when password changes
        if (confirmPasswordInput.value) {
            validatePasswordsMatch(passwordInput, confirmPasswordInput);
        }
        toggleSubmitButton(form, submitButton);
    });
    
    confirmPasswordInput.addEventListener('input', () => {
        validatePasswordsMatch(passwordInput, confirmPasswordInput);
        toggleSubmitButton(form, submitButton);
    });
    
    // Form submission handler
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        
        // Perform final validation before submission
        const isUsernameValid = validateRequired(usernameInput, 'Username is required');
        const isEmailValid = validateEmail(emailInput);
        const isPasswordValid = validatePassword(passwordInput);
        const doPasswordsMatch = validatePasswordsMatch(passwordInput, confirmPasswordInput);
        
        if (isUsernameValid && isEmailValid && isPasswordValid && doPasswordsMatch) {
            // Show loading state
            submitButton.textContent = 'Creating Account...';
            submitButton.disabled = true;
            
            // Simulate API call (replace with actual API call)
            setTimeout(() => {
                // For demonstration, we'll just show a success message
                const successMessage = document.querySelector('.success-message');
                if (successMessage) {
                    successMessage.textContent = 'Account created successfully! Redirecting to login...';
                    successMessage.style.display = 'block';
                    
                    // Redirect after delay (replace with actual redirect)
                    setTimeout(() => {
                        window.location.href = 'login.html';
                    }, 2000);
                }
            }, 1500);
        } else {
            // If validation fails, ensure errors are shown
            validateRequired(usernameInput, 'Username is required');
            validateEmail(emailInput);
            validatePassword(passwordInput);
            validatePasswordsMatch(passwordInput, confirmPasswordInput);
        }
    });
}

/**
 * Validate email format
 * @param {HTMLInputElement} input - The email input element
 * @returns {boolean} - Is the email valid
 */
function validateEmail(input) {
    const value = input.value.trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (!value) {
        showError(input, 'Email is required');
        return false;
    } else if (!emailRegex.test(value)) {
        showError(input, 'Please enter a valid email address');
        return false;
    } else {
        clearError(input);
        return true;
    }
}

/**
 * Validate password strength
 * @param {HTMLInputElement} input - The password input element
 * @returns {boolean} - Is the password valid
 */
function validatePassword(input) {
    const value = input.value;
    
    if (!value) {
        showError(input, 'Password is required');
        return false;
    } else if (value.length < 8) {
        showError(input, 'Password must be at least 8 characters');
        return false;
    } else if (!/[A-Z]/.test(value)) {
        showError(input, 'Password must contain at least one uppercase letter');
        return false;
    } else if (!/[a-z]/.test(value)) {
        showError(input, 'Password must contain at least one lowercase letter');
        return false;
    } else if (!/[0-9]/.test(value)) {
        showError(input, 'Password must contain at least one number');
        return false;
    } else {
        clearError(input);
        return true;
    }
}

/**
 * Validate that both passwords match
 * @param {HTMLInputElement} passwordInput - The password input element
 * @param {HTMLInputElement} confirmInput - The confirm password input element
 * @returns {boolean} - Do the passwords match
 */
function validatePasswordsMatch(passwordInput, confirmInput) {
    if (!confirmInput.value) {
        showError(confirmInput, 'Please confirm your password');
        return false;
    } else if (passwordInput.value !== confirmInput.value) {
        showError(confirmInput, 'Passwords do not match');
        return false;
    } else {
        clearError(confirmInput);
        return true;
    }
}

/**
 * Validate that a required field has a value
 * @param {HTMLInputElement} input - The input element
 * @param {string} errorMessage - The error message to display
 * @returns {boolean} - Is the field valid
 */
function validateRequired(input, errorMessage) {
    if (!input.value.trim()) {
        showError(input, errorMessage);
        return false;
    } else {
        clearError(input);
        return true;
    }
}

/**
 * Show error message for an input
 * @param {HTMLInputElement} input - The input element
 * @param {string} message - The error message
 */
function showError(input, message) {
    input.classList.add('input-error');
    
    // Find or create error message element
    let errorElement = input.parentElement.querySelector('.error-message');
    if (!errorElement) {
        errorElement = document.createElement('div');
        errorElement.className = 'error-message';
        input.parentElement.appendChild(errorElement);
    }
    
    errorElement.textContent = message;
    errorElement.style.display = 'block';
}

/**
 * Clear error message for an input
 * @param {HTMLInputElement} input - The input element
 */
function clearError(input) {
    input.classList.remove('input-error');
    
    const errorElement = input.parentElement.querySelector('.error-message');
    if (errorElement) {
        errorElement.style.display = 'none';
    }
}

/**
 * Toggle submit button enabled/disabled state based on form validity
 * @param {HTMLFormElement} form - The form element
 * @param {HTMLButtonElement} button - The submit button
 */
function toggleSubmitButton(form, button) {
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (input.classList.contains('input-error') || !input.value.trim()) {
            isValid = false;
        }
    });
    
    button.disabled = !isValid;
}

