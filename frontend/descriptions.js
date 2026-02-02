/**
 * Widget Descriptions Manager
 * ===========================
 * Manages informational description boxes for each widget with localStorage persistence.
 *
 * Features:
 * - Shows/hides description boxes
 * - Remembers which descriptions user has closed
 * - Uses localStorage for persistence across sessions
 */

const WidgetDescriptions = {
    STORAGE_KEY: 'closedWidgetDescriptions',

    /**
     * Initialize description boxes on page load
     */
    init() {
        this.applyClosedState();
        this.attachEventListeners();
    },

    /**
     * Get list of closed descriptions from localStorage
     */
    getClosedDescriptions() {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            return stored ? JSON.parse(stored) : {};
        } catch (e) {
            console.error('Failed to read closed descriptions:', e);
            return {};
        }
    },

    /**
     * Save closed descriptions to localStorage
     */
    saveClosedDescriptions(closedDescriptions) {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(closedDescriptions));
        } catch (e) {
            console.error('Failed to save closed descriptions:', e);
        }
    },

    /**
     * Apply closed state to all description boxes on page load
     */
    applyClosedState() {
        const closedDescriptions = this.getClosedDescriptions();

        Object.keys(closedDescriptions).forEach(widgetId => {
            if (closedDescriptions[widgetId]) {
                const descBox = document.getElementById(`${widgetId}-description`);
                if (descBox) {
                    descBox.style.display = 'none';
                }
            }
        });
    },

    /**
     * Attach click event listeners to all close buttons
     */
    attachEventListeners() {
        const closeButtons = document.querySelectorAll('.description-close');

        closeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const widgetId = e.target.getAttribute('data-widget-id');
                if (widgetId) {
                    this.closeDescription(widgetId);
                }
            });
        });
    },

    /**
     * Close a specific description box
     */
    closeDescription(widgetId) {
        const descBox = document.getElementById(`${widgetId}-description`);
        if (!descBox) {
            console.warn(`Description box not found for widget: ${widgetId}`);
            return;
        }

        // Hide the description box with animation
        descBox.style.opacity = '0';
        descBox.style.transition = 'opacity 0.3s ease-out';

        setTimeout(() => {
            descBox.style.display = 'none';
        }, 300);

        // Save to localStorage
        const closedDescriptions = this.getClosedDescriptions();
        closedDescriptions[widgetId] = true;
        this.saveClosedDescriptions(closedDescriptions);
    },

    /**
     * Show a specific description box (for debugging or reset)
     */
    showDescription(widgetId) {
        const descBox = document.getElementById(`${widgetId}-description`);
        if (!descBox) {
            console.warn(`Description box not found for widget: ${widgetId}`);
            return;
        }

        descBox.style.display = 'block';
        descBox.style.opacity = '1';

        // Remove from closed list
        const closedDescriptions = this.getClosedDescriptions();
        delete closedDescriptions[widgetId];
        this.saveClosedDescriptions(closedDescriptions);
    },

    /**
     * Reset all descriptions (show all)
     */
    resetAll() {
        localStorage.removeItem(this.STORAGE_KEY);

        const allDescriptions = document.querySelectorAll('[id$="-description"]');
        allDescriptions.forEach(descBox => {
            descBox.style.display = 'block';
            descBox.style.opacity = '1';
        });
    },

    /**
     * Get statistics about closed descriptions
     */
    getStats() {
        const closedDescriptions = this.getClosedDescriptions();
        const totalDescriptions = document.querySelectorAll('[id$="-description"]').length;
        const closedCount = Object.keys(closedDescriptions).length;

        return {
            total: totalDescriptions,
            closed: closedCount,
            open: totalDescriptions - closedCount,
            closedIds: Object.keys(closedDescriptions)
        };
    }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => WidgetDescriptions.init());
} else {
    WidgetDescriptions.init();
}

// Expose to window for debugging
window.WidgetDescriptions = WidgetDescriptions;
