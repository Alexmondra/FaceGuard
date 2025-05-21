/**
 * Dark Mode functionality for FaceGuard application
 * Handles theme toggling and localStorage persistence
 */

// DOM elements to be used for theme switching
const themeToggle = document.querySelector('.theme-switch input[type="checkbox"]');
const currentTheme = localStorage.getItem('theme');

/**
 * Apply theme to document and update toggle switch
 * @param {string} theme - The theme to apply ('dark' or null for light)
 */
function applyTheme(theme) {
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        if (themeToggle) {
            themeToggle.checked = true;
        }
    } else {
        document.documentElement.removeAttribute('data-theme');
        if (themeToggle) {
            themeToggle.checked = false;
        }
    }
}

/**
 * Switch theme based on toggle state
 * @param {Event} e - The change event from the toggle
 */
function switchTheme(e) {
    if (e.target.checked) {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
        updateThemeLabel('Dark Mode');
    } else {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
        updateThemeLabel('Light Mode');
    }
}

/**
 * Update the theme label text
 * @param {string} text - The text to display in the label
 */
function updateThemeLabel(text) {
    const label = document.querySelector('.dark-mode-label');
    if (label) {
        label.textContent = text;
    }
}

// Initialize theme from localStorage on page load
document.addEventListener('DOMContentLoaded', () => {
    // Apply saved theme (if exists)
    if (currentTheme) {
        applyTheme(currentTheme);
        updateThemeLabel(currentTheme === 'dark' ? 'Dark Mode' : 'Light Mode');
    } else {
        // Default to system preference if available
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            applyTheme('dark');
            localStorage.setItem('theme', 'dark');
            updateThemeLabel('Dark Mode');
        } else {
            updateThemeLabel('Light Mode');
        }
    }

    // Add event listener to toggle switch
    if (themeToggle) {
        themeToggle.addEventListener('change', switchTheme);
    }
});

// Listen for system theme changes
if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        const newTheme = e.matches ? 'dark' : 'light';
        applyTheme(newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeLabel(newTheme === 'dark' ? 'Dark Mode' : 'Light Mode');
    });
}

