document.addEventListener("DOMContentLoaded", function () {
  // DOM elements
  const sidebar = document.getElementById("sidebar");
  const menuToggle = document.getElementById("menuToggle");
  const newChatBtn = document.getElementById("newChatBtn");
  const chatHistory = document.getElementById("chatHistory");
  const chatMessages = document.getElementById("chatMessages");
  const emptyState = document.getElementById("emptyState");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const logoutBtn = document.getElementById("logoutBtn");
  let fileStatus = false;

  // Sample responses for demonstration
  const botResponses = [
    "I'm happy to help! What else would you like to know?",
    "That's an interesting question. Let me think about that for a moment...",
    "Based on my knowledge, there are several approaches to this problem.",
    "I understand your concern. Here's what I can suggest...",
    "Thanks for sharing that with me! Is there anything specific you'd like me to help with?",
    "I'm not entirely sure about that, but here's what I can tell you based on my knowledge.",
  ];

  // Chat data
  let chats = [];
  let currentChatId = null;
  let chatCounter = 0;

  // Check for existing chats in localStorage
  const savedChats = localStorage.getItem("ai-chatbot-chats");
  if (savedChats) {
    chats = JSON.parse(savedChats);
    updateChatHistory();

    // Check for last active chat
    const lastActiveChat = localStorage.getItem("ai-chatbot-last-active");
    if (
      lastActiveChat &&
      chats.find((chat) => chat.id === parseInt(lastActiveChat))
    ) {
      loadChat(parseInt(lastActiveChat));
    } else if (chats.length > 0) {
      loadChat(chats[0].id);
    }
  }

  // Auto resize textarea
  chatInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = this.scrollHeight + "px";

    // Enable/disable send button based on input
    sendBtn.disabled = this.value.trim() === "";
  });

  // Handle pressing Enter to send message (but Shift+Enter for new line)
  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled) {
        sendMessage();
      }
    }
  });

  // Send message when button is clicked
  sendBtn.addEventListener("click", sendMessage);

  // Create a new chat
  function createNewChat() {
    chatCounter++;
    const newChatId = Date.now();
    const newChat = {
      id: newChatId,
      title: `Chat ${chatCounter}`,
      messages: [],
    };

    chats.unshift(newChat);
    saveChatData();
    updateChatHistory();
    loadChat(newChatId);

    // Hide empty state if visible
    emptyState.style.display = "none";
  }

  // New chat button click handlers
  newChatBtn.addEventListener("click", createNewChat);

  // Load chat when clicked in history
  function loadChat(chatId) {
    currentChatId = chatId;
    localStorage.setItem("ai-chatbot-last-active", chatId);

    // Update active state in sidebar
    const chatItems = document.querySelectorAll(".chat-item");
    chatItems.forEach((item) => {
      item.classList.remove("active");
      if (item.dataset.id == chatId) {
        item.classList.add("active");
      }
    });

    // Display chat messages
    displayChatMessages(chatId);

    // Hide empty state
    emptyState.style.display = "none";

    // Close sidebar on mobile after selection
    if (window.innerWidth <= 768) {
      sidebar.classList.remove("active");
    }
  }

  // Display messages for the selected chat
  function displayChatMessages(chatId) {
    const chat = chats.find((c) => c.id === chatId);
    if (!chat) return;

    chatMessages.innerHTML = "";

    if (chat.messages.length === 0) {
      // Add a welcome message if chat is empty
      const welcomeMessage = document.createElement("div");
      welcomeMessage.className = "message message-bot";
      welcomeMessage.textContent = "Hello! How can I assist you today?";
      chatMessages.appendChild(welcomeMessage);
    } else {
      // Display existing messages
      chat.messages.forEach((msg) => {
        const messageDiv = document.createElement("div");
        messageDiv.className = `message message-${msg.sender}`;
        messageDiv.textContent = msg.text;
        chatMessages.appendChild(messageDiv);
      });
    }

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // Update chat history in sidebar
  function updateChatHistory() {
    chatHistory.innerHTML = "";
    chatCounter = Math.max(chatCounter, chats.length);

    chats.forEach((chat) => {
      const li = document.createElement("li");
      li.className = "chat-item";
      li.dataset.id = chat.id;
      if (chat.id === currentChatId) {
        li.classList.add("active");
      }

      li.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
                        <span class="chat-item-text">${chat.title}</span>
                    `;

      li.addEventListener("click", () => loadChat(chat.id));
      chatHistory.appendChild(li);
    });
  }

  // Save chats to localStorage
  function saveChatData() {
    localStorage.setItem("ai-chatbot-chats", JSON.stringify(chats));
  }

  // Send a message
  function sendMessage() {
    const userQuery = chatInput.value.trim();
    if (!userQuery) return;

    // Create new chat if none exists
    if (!currentChatId || !chats.find((c) => c.id === currentChatId)) {
      createNewChat();
    }

    // Find current chat
    const chatIndex = chats.findIndex((c) => c.id === currentChatId);
    if (chatIndex === -1) return;

    // Add user message
    const userMessage = {
      sender: "user",
      text: userQuery,
      timestamp: Date.now(),
    };

    chats[chatIndex].messages.push(userMessage);

    // Update chat title if it's the first message
    if (chats[chatIndex].messages.length === 1) {
      // Use first few words of message as chat title
      const words = userQuery.split(" ");
      const title =
        words.slice(0, 4).join(" ") + (words.length > 4 ? "..." : "");
      chats[chatIndex].title = title;
    }

    // Display the message
    const messageDiv = document.createElement("div");
    messageDiv.className = "message message-user";
    messageDiv.textContent = userQuery;
    emptyState.style.display = "none";
    chatMessages.appendChild(messageDiv);

    // Clear input
    chatInput.value = "";
    chatInput.style.height = "auto";
    sendBtn.disabled = true;

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Show typing indicator
    const loadingIndicator = document.createElement("div");
    loadingIndicator.className = "loading-indicator";
    loadingIndicator.innerHTML = "<span></span><span></span><span></span>";
    chatMessages.appendChild(loadingIndicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Simulate bot response after delay
    setTimeout(() => {
      // Remove loading indicator
      chatMessages.removeChild(loadingIndicator);

      // Get random response for demo
      if (!fileStatus){
        console.log("Please upload a file first.");
        return;
      }
      const botResponseText =
        botResponses[Math.floor(Math.random() * botResponses.length)];

      // Add bot message
      const botMessage = {
        sender: "bot",
        text: botResponseText,
        timestamp: Date.now(),
      };

      chats[chatIndex].messages.push(botMessage);

      // Display the bot message
      const botMessageDiv = document.createElement("div");
      botMessageDiv.className = "message message-bot";
      botMessageDiv.textContent = botResponseText;
      chatMessages.appendChild(botMessageDiv);

      // Save chat data
      saveChatData();
      updateChatHistory();

      // Scroll to bottom
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }, 1000 + Math.random() * 1000); // Random delay between 1-2 seconds
  }

  // Logout button handler (for demo - just clears data)
  logoutBtn.addEventListener("click", function () {
    if (
      confirm("Are you sure you want to logout? This will clear all chat data.")
    ) {
      chats = [];
      currentChatId = null;
      chatCounter = 0;
      updateChatHistory();
      chatMessages.innerHTML = "";
      emptyState.style.display = "flex";
      fetch("/api/logout")
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            // Redirect to login page or perform any other action
            window.location.href = data.redirect;
          } else {
            console.error("Logout failed:", data.message);
            NotificationSystem.error("Sorry, something went wrong during logout.", "Error!", 2000);
          }
        })
        .catch((error) => {
          console.error("Error during logout:", error);
          NotificationSystem.error("Sorry, something went wrong during logout.", "Error!", 2000);
        });
    }
  });

  // Mobile menu toggle
  function setupMobileView() {
    if (window.innerWidth <= 768) {
      menuToggle.style.display = "block";
      sidebar.classList.remove("active");
    } else {
      menuToggle.style.display = "none";
      sidebar.classList.remove("active");
    }
  }

  menuToggle.addEventListener("click", function () {
    sidebar.classList.toggle("active");
  });

  // Close sidebar when clicking outside on mobile
  document.addEventListener("click", function (e) {
    if (
      window.innerWidth <= 768 &&
      !sidebar.contains(e.target) &&
      e.target !== menuToggle &&
      sidebar.classList.contains("active")
    ) {
      sidebar.classList.remove("active");
    }
  });

  // Handle window resize
  window.addEventListener("resize", setupMobileView);
  setupMobileView();

  // If no chats exist, show empty state
  if (chats.length === 0) {
    emptyState.style.display = "flex";
  } else {
    emptyState.style.display = "none";
  }
});
