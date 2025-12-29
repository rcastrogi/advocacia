/**
 * Performance Optimizations for Petitio
 * Reduces DOMContentLoaded and forced reflow violations
 */

// Performance utilities
window.PerformanceUtils = {
    // Debounce function to limit execution frequency
    debounce: function(func, wait, immediate) {
        let timeout;
        return function executedFunction() {
            const context = this;
            const args = arguments;
            const later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    },

    // Throttle function to limit execution frequency
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    },

    // Schedule task for next animation frame
    scheduleTask: function(callback) {
        if (window.requestAnimationFrame) {
            requestAnimationFrame(callback);
        } else {
            setTimeout(callback, 16); // Fallback to ~60fps
        }
    },

    // Batch DOM reads to avoid forced reflows
    batchDOMReads: function(callbacks) {
        const results = [];
        callbacks.forEach(callback => {
            results.push(callback());
        });
        return results;
    },

    // Batch DOM writes to avoid multiple reflows
    batchDOMWrites: function(callbacks) {
        this.scheduleTask(() => {
            callbacks.forEach(callback => callback());
        });
    }
};

// Optimized DOMContentLoaded handler
document.addEventListener('DOMContentLoaded', function() {
    // Mark DOM as ready for performance monitoring
    window.domReadyTime = performance.now();

    // Defer non-critical initialization
    setTimeout(function() {
        // Dispatch custom event for deferred initialization
        const deferredInitEvent = new CustomEvent('deferredInit');
        document.dispatchEvent(deferredInitEvent);
    }, 100);
});

// Performance monitoring (development only)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.addEventListener('load', function() {
        setTimeout(function() {
            const domReadyTime = window.domReadyTime || 0;
            const loadTime = performance.now();

            console.log('🚀 Performance Metrics:');
            console.log(`  DOMContentLoaded: ${domReadyTime.toFixed(2)}ms`);
            console.log(`  Page Load: ${loadTime.toFixed(2)}ms`);

            if (domReadyTime > 200) {
                console.warn('⚠️  DOMContentLoaded took longer than 200ms. Consider optimizing initialization code.');
            }
        }, 0);
    });
}