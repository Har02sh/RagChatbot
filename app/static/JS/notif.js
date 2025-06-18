// Default notification messages
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

function showNotification(type, customTitle, customMessage, duration = 5000, position = 'top-right') {
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
        <button class="notification-close" onclick="removeNotification('${id}')">×</button>
        <div class="notification-progress"></div>
    `;
    
    // Add to container
    const container = document.getElementById('notifications-container');
    container.appendChild(notification);
    
    // Set timeout for auto-removal
    activeTimeouts[id] = setTimeout(() => {
        removeNotification(id);
    }, duration);
    
    // Reset progress animation duration
    const progressBar = notification.querySelector('.notification-progress');
    progressBar.style.animation = `progress ${duration/1000}s linear forwards`;
    
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
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 300);
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