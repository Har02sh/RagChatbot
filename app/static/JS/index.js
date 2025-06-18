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

  const pdfUpload = document.getElementById("pdfUpload");
  const uploadPreview = document.getElementById("uploadPreview");
  const uploadProgressContainer = document.getElementById(
    "uploadProgressContainer"
  );
  const uploadProgressBar = document.getElementById("uploadProgressBar");
  const uploadProgressText = document.getElementById("uploadProgressText");
  let fileStatus = false;

  // Chat data
  let chats = [];
  let currentChatId = null;

  // API endpoints
  const API = {
    getChats: "/api/chats",
    createChat: "/api/chats",
    getMessages: "/api/chats/:id/messages",
    sendMessage: "/api/chats/:id/messages",
    deleteChat: "/api/chats/:id",
    uploadFile: "/api/uploadPdf",
    logout: "/api/logout",
  };

  // Initialize the app
  init();

  async function init() {
    // Load chats from server
    await loadChats();

    // Set up event listeners
    setupEventListeners();

    setupPdfUpload();
  }

  // Set up all event listeners
  function setupEventListeners() {
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

    // New chat button click handler
    newChatBtn.addEventListener("click", createNewChat);

    // Logout button handler
    logoutBtn.addEventListener("click", handleLogout);

    // Mobile menu toggle
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
  }

  // Load all chats from server
  async function loadChats() {
    try {
      const response = await fetch(API.getChats);
      if (!response.ok) throw new Error("Failed to fetch chats");

      const data = await response.json();
      chats = data.chats || [];

      updateChatHistory();

      // // Load last active chat or first chat if available
      // if (chats.length > 0) {
      //   // Check if there's a last active chat ID in URL or session storage
      //   const urlParams = new URLSearchParams(window.location.search);
      //   const lastActiveChatId =
      //     urlParams.get("chat") || sessionStorage.getItem("last-active-chat");

      //   if (
      //     lastActiveChatId &&
      //     chats.find((chat) => chat.id == lastActiveChatId)
      //   ) {
      //     loadChat(parseInt(lastActiveChatId));
      //   } else {
      //     loadChat(chats[0].id);
      //   }
      // } else {
      //   // Show empty state if no chats
      emptyState.style.display = "flex";
      // }
    } catch (error) {
      console.error("Error loading chats:", error);
      showNotification("Failed to load chats", "error");
      emptyState.style.display = "flex";
    }
  }

  // Create a new chat
  async function createNewChat() {
    try {
      const response = await fetch(API.createChat, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: "New Chat",
        }),
      });

      if (!response.ok) throw new Error("Failed to create chat");

      const newChat = await response.json();

      // Add the new chat to the beginning of the chats array
      chats.unshift(newChat);
      updateChatHistory();
      loadChat(newChat.id);

      // Hide empty state if visible
      emptyState.style.display = "none";
    } catch (error) {
      console.error("Error creating new chat:", error);
      showNotification("Failed to create new chat", "error");
    }
  }

  // Load chat when clicked in history
  async function loadChat(chatId) {
    currentChatId = chatId;

    // Save last active chat in session storage
    sessionStorage.setItem("last-active-chat", chatId);

    // Update URL with chat ID without refreshing the page
    const url = new URL(window.location);
    url.searchParams.set("chat", chatId);
    window.history.pushState({}, "", url);

    // Update active state in sidebar
    const chatItems = document.querySelectorAll(".chat-item");
    chatItems.forEach((item) => {
      item.classList.remove("active");
      if (item.dataset.id == chatId) {
        item.classList.add("active");
      }
    });

    // Display chat messages
    await displayChatMessages(chatId);

    // Hide empty state
    emptyState.style.display = "none";

    // Close sidebar on mobile after selection
    if (window.innerWidth <= 768) {
      sidebar.classList.remove("active");
    }
  }

  // Display messages for the selected chat
  async function displayChatMessages(chatId) {
    try {
      // Show loading state
      chatMessages.innerHTML =
        '<div class="loading-indicator"><span></span><span></span><span></span></div>';

      const response = await fetch(API.getMessages.replace(":id", chatId));
      if (!response.ok) throw new Error("Failed to fetch messages");

      const data = await response.json();
      const messages = data.messages || [];

      chatMessages.innerHTML = "";

      if (messages.length === 0) {
        // Add a welcome message if chat is empty
        const welcomeMessage = document.createElement("div");
        welcomeMessage.className = "message message-bot";
        welcomeMessage.textContent = "Hello! How can I assist you today?";
        chatMessages.appendChild(welcomeMessage);
      } else {
        // Display existing messages
        messages.forEach((msg) => {
          const messageDiv = document.createElement("div");
          messageDiv.className = `message message-${msg.sender}`;
          messageDiv.textContent = msg.text;
          chatMessages.appendChild(messageDiv);
        });
      }

      // Scroll to bottom
      chatMessages.scrollTop = chatMessages.scrollHeight;
    } catch (error) {
      console.error("Error loading messages:", error);
      chatMessages.innerHTML =
        '<div class="error-message">Failed to load messages. Please try again.</div>';
      showNotification("Failed to load messages", "error");
    }
  }

  // Update chat history in sidebar
  function updateChatHistory() {
    chatHistory.innerHTML = "";

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
        <button class="delete-chat-btn" title="Delete Chat">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
        </button>
      `;

      // Add click event for loading chat
      li.addEventListener("click", (e) => {
        // Don't load chat if delete button was clicked
        if (!e.target.closest(".delete-chat-btn")) {
          loadChat(chat.id);
        }
      });

      // Add delete button event
      const deleteBtn = li.querySelector(".delete-chat-btn");
      deleteBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteChat(chat.id);
      });

      chatHistory.appendChild(li);
    });

    // If no chats exist, show empty state
    if (chats.length === 0) {
      emptyState.style.display = "flex";
    }
  }

  // Delete a chat
  async function deleteChat(chatId) {
    if (confirm("Are you sure you want to delete this chat?")) {
      try {
        const response = await fetch(API.deleteChat.replace(":id", chatId), {
          method: "DELETE",
        });

        if (!response.ok) throw new Error("Failed to delete chat");

        // Remove chat from local array
        chats = chats.filter((chat) => chat.id !== chatId);
        updateChatHistory();

        // If current chat was deleted, load another one or show empty state
        if (currentChatId === chatId) {
          if (chats.length > 0) {
            loadChat(chats[0].id);
          } else {
            currentChatId = null;
            chatMessages.innerHTML = "";
            emptyState.style.display = "flex";
            // Clear URL parameter
            const url = new URL(window.location);
            url.searchParams.delete("chat");
            window.history.pushState({}, "", url);
          }
        }

        showNotification("Chat deleted successfully", "success");
      } catch (error) {
        console.error("Error deleting chat:", error);
        showNotification("Failed to delete chat", "error");
      }
    }
  }

  // Send a message
  async function sendMessage() {
    const userQuery = chatInput.value.trim();
    if (!userQuery) return;

    // Create new chat if none exists
    if (!currentChatId) {
      await createNewChat();
      if (!currentChatId) return; // If creation failed
    }

    // Check if file is uploaded
    if (!fileStatus) {
      NotificationSystem.warning("Please upload a PDF first", "Warning!", 2000);
      return;
    }

    // Add user message to UI immediately
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

    try {
      // Send message to server
      const response = await fetch(
        API.sendMessage.replace(":id", currentChatId),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            text: userQuery,
            sender: "user",
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to send message");
      }

      const data = await response.json();

      // Remove loading indicator
      if (chatMessages.contains(loadingIndicator)) {
        chatMessages.removeChild(loadingIndicator);
      }

      if (data.success && data.bot_message) {
        // Add bot message to UI
        const botDiv = document.createElement("div");
        botDiv.className = "message message-bot";
        botDiv.textContent = data.bot_message.text;
        chatMessages.appendChild(botDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      } else {
        // Show error message
        const errorDiv = document.createElement("div");
        errorDiv.className = "message message-error";
        errorDiv.textContent = data.message || "Failed to get bot response.";
        chatMessages.appendChild(errorDiv);
      }
    } catch (error) {
      console.error("Error sending message:", error);

      // Remove loading indicator
      if (chatMessages.contains(loadingIndicator)) {
        chatMessages.removeChild(loadingIndicator);
      }

      // Show error message
      const errorDiv = document.createElement("div");
      errorDiv.className = "message message-error";
      errorDiv.textContent = "Failed to send message. Please try again.";
      chatMessages.appendChild(errorDiv);

      showNotification("Failed to send message", "error");
    }
  }

  // Handle logout
  async function handleLogout() {
    if (confirm("Are you sure you want to logout?")) {
      try {
        const response = await fetch(API.logout);
        const data = await response.json();

        if (data.success) {
          // Redirect to login page
          window.location.href = data.redirect || "/login";
        } else {
          throw new Error(data.message || "Logout failed");
        }
      } catch (error) {
        console.error("Error during logout:", error);
        showNotification("Logout failed. Please try again.", "error");
      }
    }
  }

  // Mobile menu setup
  function setupMobileView() {
    if (window.innerWidth <= 768) {
      menuToggle.style.display = "block";
      sidebar.classList.remove("active");
    } else {
      menuToggle.style.display = "none";
      sidebar.classList.add("active"); // Desktop always shows sidebar
    }
  }

  // File upload functionality
  function setupFileUpload() {
    const fileUploadBtn = document.getElementById("fileUploadBtn");
    const fileInput = document.getElementById("fileInput");

    fileUploadBtn.addEventListener("click", () => {
      fileInput.click();
    });

    fileInput.addEventListener("change", async (e) => {
      if (e.target.files.length > 0) {
        const formData = new FormData();
        formData.append("file", e.target.files[0]);

        try {
          const response = await fetch(API.uploadFile, {
            method: "POST",
            body: formData,
          });

          if (!response.ok) throw new Error("File upload failed");

          const data = await response.json();
          fileStatus = true;
          showNotification("File uploaded successfully", "success");
        } catch (error) {
          console.error("Error uploading file:", error);
          showNotification("Failed to upload file", "error");
        }
      }
    });
  }

  // Show notification
  function showNotification(message, type = "info") {
    // Check if NotificationSystem exists
    if (typeof NotificationSystem !== "undefined") {
      NotificationSystem[type](
        message,
        type === "error" ? "Error!" : "Success!",
        3000
      );
    } else {
      // Simple fallback
      alert(message);
    }
  }

  // PDF Upload functionality
  function setupPdfUpload() {
    if (!pdfUpload) return;

    pdfUpload.addEventListener("change", async (e) => {
      const files = e.target.files;
      if (!files || files.length === 0) return;

      // Clear previous upload preview
      uploadPreview.innerHTML = "";

      // Check file type
      const invalidFiles = Array.from(files).filter(
        (file) => file.type !== "application/pdf"
      );
      if (invalidFiles.length > 0) {
        showNotification("Only PDF files are allowed", "error");
        pdfUpload.value = "";
        return;
      }

      // Create preview items for each file
      for (const file of files) {
        const previewItem = document.createElement("div");
        previewItem.className = "upload-preview-item";
        previewItem.innerHTML = `
          <div class="upload-preview-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
          <div class="upload-preview-info">
            <span class="upload-preview-name">${file.name}</span>
            <span class="upload-preview-size">${formatFileSize(
              file.size
            )}</span>
          </div>
          <button class="upload-preview-remove" title="Remove file">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        `;

        // Add remove button event
        const removeBtn = previewItem.querySelector(".upload-preview-remove");
        removeBtn.addEventListener("click", () => {
          previewItem.remove();
          // If all files are removed, reset the input
          if (uploadPreview.children.length === 0) {
            pdfUpload.value = "";
            fileStatus = false;
          }
        });

        uploadPreview.appendChild(previewItem);
      }

      // Show upload preview
      // uploadPreview.style.display = "flex";

      // Start uploading the files
      await uploadFiles(files);
    });
  }

  // Upload files to server with progress tracking
  async function uploadFiles(files) {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("file", files[i]);
    }

    try {
      // Show upload progress container with dynamic content
      uploadProgressContainer.style.display = "flex";
      uploadProgressContainer.innerHTML = `
        <div class="upload-progress-header">
          <div class="upload-progress-label">Uploading PDF...</div>
          <div class="upload-progress-text">0%</div>
        </div>
        <div class="upload-progress-bar-container">
          <div id="uploadProgressBar" class="upload-progress-bar" style="width: 0%"></div>
        </div>
      `;

      const progressBar = document.getElementById("uploadProgressBar");
      const progressText = uploadProgressContainer.querySelector(
        ".upload-progress-text"
      );

      // Use axios for upload with progress
      const response = await axios.post(API.uploadFile, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: function (progressEvent) {
          if (progressEvent.lengthComputable) {
            const percentComplete = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            progressBar.style.width = percentComplete + "%";
            progressText.textContent = percentComplete + "%";

            // Update label text based on progress
            const label = uploadProgressContainer.querySelector(
              ".upload-progress-label"
            );
            if (percentComplete < 100) {
              label.textContent = "Uploading PDF...";
            } else {
              label.textContent = "Processing PDF...";
            }
          }
        },
      });

      if (response.status >= 200 && response.status < 300) {
        progressBar.style.width = "100%";
        progressText.textContent = "100%";

        // Show success state
        const label = uploadProgressContainer.querySelector(
          ".upload-progress-label"
        );
        label.textContent = "✓ Upload Complete!";
        label.style.color = "#16a34a";

        // Add success animation
        uploadProgressContainer.style.background =
          "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)";
        uploadProgressContainer.style.borderColor = "#bbf7d0";

        setTimeout(() => {
          uploadProgressContainer.style.display = "none";
          showNotification("PDF uploaded successfully!", "success");
        }, 1500);

        fileStatus = true;
      } else {
        uploadProgressContainer.style.display = "none";
        showNotification("Failed to upload PDF", "error");
      }
    } catch (error) {
      console.error("Error uploading PDF:", error);
      uploadProgressContainer.style.display = "none";
      showNotification("Failed to upload PDF", "error");
    }
  }

  // Format file size in KB, MB, etc.
  function formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  // Show notification
  function showNotification(message, type = "info") {
    // Check if NotificationSystem exists
    if (typeof NotificationSystem !== "undefined") {
      NotificationSystem[type](
        message,
        type === "error" ? "Error!" : "Success!",
        3000
      );
    } else {
      // Simple fallback
      alert(message);
    }
  }
});
