const NotificationSystem = (function() {
    const defaultMessages = {
        success: {
            title: "Success!",
            message: "The operation was completed successfully."
        },
        error: {
            title: "Error!",
            message: "An error occurred. Please try again."
        },
        warning: {
            title: "Warning!",
            message: "Please proceed with caution."
        },
        info: {
            title: "Information",
            message: "Here's something you should know."
        }
    };

    // Icons for each notification type
    const icons = {
        success: "✓",
        error: "✕",
        warning: "!",
        info: "ℹ"
    };

    // Counter to generate unique IDs
    let notificationCounter = 0;
    
    // Store active notification timeouts
    const activeTimeouts = {};

    function init() {
        if (!document.getElementById('notifications-container')) {
            const container = document.createElement('div');
            container.id = 'notifications-container';
            document.body.appendChild(container);
            
            // Add styles if they don't exist
            if (!document.getElementById('notification-styles')) {
                const styleEl = document.createElement('style');
                styleEl.id = 'notification-styles';
                styleEl.textContent = `
                    #notifications-container {
                        position: fixed;
                        top: 20px;
                        right: 20px;
                        width: 320px;
                        max-width: calc(100vw - 40px);
                        z-index: 9999;
                        display: flex;
                        flex-direction: column;
                        gap: 10px;
                    }
                    
                    .notification {
                        display: flex;
                        padding: 16px;
                        border-radius: 8px;
                        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                        margin-bottom: 10px;
                        animation: notification-slideIn 0.5s ease forwards;
                        transition: opacity 0.3s ease, transform 0.3s ease;
                        position: relative;
                        overflow: hidden;
                    }
                    
                    .notification.hiding {
                        opacity: 0;
                        transform: translateX(30px);
                    }
                    
                    .notification-icon {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-right: 14px;
                        font-size: 24px;
                    }
                    
                    .notification-content {
                        flex: 1;
                    }
                    
                    .notification-title {
                        font-weight: 600;
                        margin-bottom: 4px;
                        font-size: 16px;
                    }
                    
                    .notification-message {
                        font-size: 14px;
                        opacity: 0.9;
                        line-height: 1.4;
                    }
                    
                    .notification-close {
                        background: none;
                        color: red;
                        border: none;
                        font-size: 18px;
                        cursor: pointer;
                        opacity: 0.7;
                        padding: 0;
                        margin-left: 12px;
                        transition: opacity 0.2s;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        height: 24px;
                        width: 24px;
                        border-radius: 50%;
                    }
                    
                    .notification-close:hover {
                        opacity: 1;
                    }
                    
                    .notification-progress {
                        position: absolute;
                        bottom: 0;
                        left: 0;
                        height: 3px;
                        width: 100%;
                        transform: scaleX(0);
                        transform-origin: right;
                        animation: notification-progress 5s linear forwards;
                    }
                    
                    .notification.success {
                        background-color: #E8F5E9;
                        color: #2E7D32;
                        border-left: 4px solid #4CAF50;
                    }
                    
                    .notification.success .notification-progress {
                        background-color: #4CAF50;
                    }
                    
                    .notification.error {
                        background-color: #FFEBEE;
                        color: #C62828;
                        border-left: 4px solid #F44336;
                    }
                    
                    .notification.error .notification-progress {
                        background-color: #F44336;
                    }
                    
                    .notification.warning {
                        background-color: #FFF8E1;
                        color: #F57F17;
                        border-left: 4px solid #FFC107;
                    }
                    
                    .notification.warning .notification-progress {
                        background-color: #FFC107;
                    }
                    
                    .notification.info {
                        background-color: #E3F2FD;
                        color: #1565C0;
                        border-left: 4px solid #2196F3;
                    }
                    
                    .notification.info .notification-progress {
                        background-color: #2196F3;
                    }
                    
                    @keyframes notification-slideIn {
                        from {
                            transform: translateX(100%);
                            opacity: 0;
                        }
                        to {
                            transform: translateX(0);
                            opacity: 1;
                        }
                    }
                    
                    @keyframes notification-progress {
                        from {
                            transform: scaleX(1);
                        }
                        to {
                            transform: scaleX(0);
                        }
                    }
                `;
                document.head.appendChild(styleEl);
            }
        }
    }

    function updateContainerPosition(position) {
        const container = document.getElementById('notifications-container');
        
        // Reset all positioning
        container.style.top = null;
        container.style.right = null;
        container.style.bottom = null;
        container.style.left = null;
        
        // Set new position
        switch (position) {
            case 'top-right':
                container.style.top = '20px';
                container.style.right = '20px';
                break;
            case 'top-left':
                container.style.top = '20px';
                container.style.left = '20px';
                break;
            case 'bottom-right':
                container.style.bottom = '20px';
                container.style.right = '20px';
                break;
            case 'bottom-left':
                container.style.bottom = '20px';
                container.style.left = '20px';
                break;
        }
    }


    function showNotification(type, customTitle, customMessage, duration = 5000, position = 'top-right') {
        // Initialize if needed
        init();
        
        // Update container position
        updateContainerPosition(position);
        
        // Create notification
        const id = 'notification-' + notificationCounter++;
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.id = id;
        
        // Set title and message
        const title = customTitle || defaultMessages[type].title;
        const message = customMessage || defaultMessages[type].message;
        
        // Create notification content
        notification.innerHTML = `
            <div class="notification-icon">${icons[type]}</div>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close" aria-label="Close notification">×</button>
            <div class="notification-progress"></div>
        `;
        
        // Add click handler for close button
        const closeButton = notification.querySelector('.notification-close');
        closeButton.addEventListener('click', function() {
            removeNotification(id);
        });
        
        // Add to container
        const container = document.getElementById('notifications-container');
        container.appendChild(notification);
        
        // Set timeout for auto-removal
        activeTimeouts[id] = setTimeout(() => {
            removeNotification(id);
        }, duration);
        
        // Reset progress animation duration
        const progressBar = notification.querySelector('.notification-progress');
        progressBar.style.animation = `notification-progress ${duration/1000}s linear forwards`;
        
        return id; // Return ID so caller can remove it early if needed
    }

    function removeNotification(id) {
        const notification = document.getElementById(id);
        if (!notification) return;
        
        // Clear any pending timeout
        if (activeTimeouts[id]) {
            clearTimeout(activeTimeouts[id]);
            delete activeTimeouts[id];
        }
        
        // Add hiding class for animation
        notification.classList.add('hiding');
        
        // Remove after animation completes
        setTimeout(() => {
            if (notification && notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    function setGlobalOptions(options) {
        if (options.position) {
            updateContainerPosition(options.position);
        }
        
        // Store other global options if needed
        if (options.duration) {
            defaultDuration = options.duration;
        }
    }

    // Public API
    return {
        init: init,
        show: showNotification,
        remove: removeNotification,
        setOptions: setGlobalOptions,
        
        success: function(message, title, duration, position) {
            return showNotification('success', title, message, duration, position);
        },
        
        error: function(message, title, duration, position) {
            return showNotification('error', title, message, duration, position);
        },
        
        warning: function(message, title, duration, position) {
            return showNotification('warning', title, message, duration, position);
        },
        
        info: function(message, title, duration, position) {
            return showNotification('info', title, message, duration, position);
        }
    };
})();

// If in a CommonJS environment
if (typeof module !== 'undefined' && typeof module.exports !== 'undefined') {
    module.exports = NotificationSystem;
}
// If in an ES module environment
else if (typeof define === 'function' && define.amd) {
    define([], function() {
        return NotificationSystem;
    });
}
else {
    window.NotificationSystem = NotificationSystem; // Otherwise, add to global window object
}