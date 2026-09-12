/**
 * NUTRIBOT CHILE - FRONTEND LOGIC & RAG CLIENT
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatMessages = document.getElementById("chat-messages");
  const welcomeCard = document.getElementById("welcome-card");
  const chatForm = document.getElementById("chat-form");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const voiceBtn = document.getElementById("voice-input-btn");
  const clearChatBtn = document.getElementById("clear-chat-btn");
  const toggleTtsBtn = document.getElementById("toggle-tts-btn");
  const toggleInventoryBtn = document.getElementById("toggle-inventory-btn");
  const inventorySidebar = document.getElementById("inventory-sidebar");
  const inventoryList = document.getElementById("inventory-list");
  const refreshInventoryBtn = document.getElementById("refresh-inventory-btn");
  const inventorySearch = document.getElementById("inventory-search");

  // KPI elements
  const kpiProducts = document.getElementById("kpi-products");
  const kpiStock = document.getElementById("kpi-stock");
  const kpiValuation = document.getElementById("kpi-valuation");

  // State
  let inventoryData = [];
  let isTtsEnabled = localStorage.getItem("nutribot_tts") === "true";
  let isRecognitionActive = false;
  let recognition = null;
  let isSending = false;

  // Initialize TTS UI state
  updateTtsButtonState();

  // Setup Speech Recognition if available
  setupSpeechRecognition();

  // Load Inventory Data
  fetchInventory();

  // Setup Event Listeners
  setupEventListeners();

  /* ==========================================================================
     EVENT LISTENERS & BINDINGS
     ========================================================================== */
  function setupEventListeners() {
    // Form Submit
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      handleSendMessage();
    });

    // Enter to submit, Shift+Enter for newline
    userInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    });

    // Auto-grow textarea
    userInput.addEventListener("input", () => {
      userInput.style.height = "auto";
      userInput.style.height = Math.min(userInput.scrollHeight, 120) + "px";
    });

    // Quick suggestion pills delegation
    document.addEventListener("click", (e) => {
      const pill = e.target.closest(".suggestion-pill") || e.target.closest(".mini-chip");
      if (pill && pill.dataset.prompt) {
        const prompt = pill.dataset.prompt;
        userInput.value = prompt;
        handleSendMessage();
      }
    });

    // Toggle Inventory Sidebar (Mobile / Desktop)
    if (toggleInventoryBtn) {
      toggleInventoryBtn.addEventListener("click", () => {
        inventorySidebar.classList.toggle("open");
        toggleInventoryBtn.classList.toggle("active");
      });
    }

    // Refresh Inventory Button
    if (refreshInventoryBtn) {
      refreshInventoryBtn.addEventListener("click", () => {
        refreshInventoryBtn.style.transform = "rotate(360deg)";
        fetchInventory().then(() => {
          setTimeout(() => { refreshInventoryBtn.style.transform = ""; }, 500);
        });
      });
    }

    // Filter Inventory Search
    if (inventorySearch) {
      inventorySearch.addEventListener("input", (e) => {
        filterInventoryDisplay(e.target.value.trim().toLowerCase());
      });
    }

    // Toggle TTS
    if (toggleTtsBtn) {
      toggleTtsBtn.addEventListener("click", () => {
        isTtsEnabled = !isTtsEnabled;
        localStorage.setItem("nutribot_tts", isTtsEnabled);
        updateTtsButtonState();
      });
    }

    // Clear Chat
    if (clearChatBtn) {
      clearChatBtn.addEventListener("click", () => {
        if (confirm("¿Deseas reiniciar la conversación con NutriBot?")) {
          clearChat();
        }
      });
    }

    // Voice Input Button
    if (voiceBtn) {
      voiceBtn.addEventListener("click", toggleVoiceRecognition);
    }
  }

  /* ==========================================================================
     INVENTORY API & RENDERING
     ========================================================================== */
  async function fetchInventory() {
    try {
      const response = await fetch("/api/inventory");
      if (!response.ok) throw new Error("Error fetching inventory");
      const data = await response.json();
      
      inventoryData = data.items || [];
      
      // Update KPIs
      if (kpiProducts) kpiProducts.textContent = data.total_products || 0;
      if (kpiStock) kpiStock.textContent = `${data.total_stock || 0} un.`;
      if (kpiValuation) kpiValuation.textContent = `${data.total_valuation_formatted || '$0'} CLP`;

      renderInventoryList(inventoryData);
    } catch (err) {
      console.error("Error al cargar inventario:", err);
      if (inventoryList) {
        inventoryList.innerHTML = `
          <div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
            No se pudo cargar el inventario local. Revisa que el backend esté activo.
          </div>
        `;
      }
    }
  }

  function renderInventoryList(items) {
    if (!inventoryList) return;
    
    if (items.length === 0) {
      inventoryList.innerHTML = `
        <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
          No se encontraron productos coincidentes.
        </div>
      `;
      return;
    }

    inventoryList.innerHTML = items.map(item => {
      const stockClass = item.stock >= 15 ? "stock-high" : item.stock >= 5 ? "stock-med" : "stock-low";
      const stockLabel = item.stock >= 15 ? "Disponible" : item.stock >= 5 ? "Medio" : "Bajo";

      return `
        <div class="inventory-item-card" data-product-name="${escapeHtml(item.producto)}" title="Haz clic para consultar sobre este producto">
          <div class="item-header">
            <span class="item-title">${escapeHtml(item.producto)}</span>
            <span class="item-id-badge">#${item.id}</span>
          </div>
          <div class="item-body-row">
            <span class="item-price">${item.precio_formateado} CLP</span>
            <span class="card-prod-stock ${stockClass}">
              ${item.stock} un. (${stockLabel})
            </span>
          </div>
          <div class="item-ask-hint">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
            Preguntar al bot
          </div>
        </div>
      `;
    }).join("");

    // Add click event on each inventory card to ask about it
    inventoryList.querySelectorAll(".inventory-item-card").forEach(card => {
      card.addEventListener("click", () => {
        const prodName = card.dataset.productName;
        userInput.value = `¿Qué stock y precio tiene el producto ${prodName}?`;
        handleSendMessage();
      });
    });
  }

  function filterInventoryDisplay(term) {
    if (!term) {
      renderInventoryList(inventoryData);
      return;
    }
    const filtered = inventoryData.filter(item => 
      item.producto.toLowerCase().includes(term) ||
      String(item.id) === term ||
      String(item.precio).includes(term)
    );
    renderInventoryList(filtered);
  }

  /* ==========================================================================
     CHAT HANDLING & MESSAGE RENDERING
     ========================================================================== */
  async function handleSendMessage() {
    const text = userInput.value.trim();
    if (!text || isSending) return;

    isSending = true;
    sendBtn.disabled = true;
    userInput.value = "";
    userInput.style.height = "auto";

    // Hide welcome card if present
    if (welcomeCard && welcomeCard.style.display !== "none") {
      welcomeCard.style.display = "none";
    }

    // Append User Message
    appendMessage({
      sender: "user",
      text: text,
      timestamp: getCurrentTime()
    });

    // Show Typing Indicator
    const typingElement = showTypingIndicator();
    scrollToBottom();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });

      if (!response.ok) {
        throw new Error("Error en la respuesta del servidor");
      }

      const data = await response.json();
      
      // Remove typing indicator
      typingElement.remove();

      // Append Bot Message
      appendMessage({
        sender: "bot",
        text: data.response,
        matches: data.matches || [],
        timestamp: getCurrentTime()
      });

      // Text-To-Speech if enabled
      if (isTtsEnabled) {
        speakText(data.response);
      }

    } catch (error) {
      console.error("Error sending message:", error);
      typingElement.remove();
      appendMessage({
        sender: "bot",
        text: "⚠️ Ocurrió un error al consultar el servidor local. Por favor verifica que el backend de NutriBot esté en ejecución.",
        matches: [],
        timestamp: getCurrentTime()
      });
    } finally {
      isSending = false;
      sendBtn.disabled = false;
      userInput.focus();
      scrollToBottom();
    }
  }

  function appendMessage({ sender, text, matches = [], timestamp }) {
    const row = document.createElement("div");
    row.className = `message-row ${sender}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.innerHTML = sender === "bot" ? "⚡" : "👤";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";

    const textContent = document.createElement("div");
    textContent.className = "bot-content-text";
    textContent.innerHTML = formatMarkdown(text);
    bubble.appendChild(textContent);

    // If bot returned structured product matches, render cards
    if (sender === "bot" && matches && matches.length > 0) {
      const cardsContainer = document.createElement("div");
      cardsContainer.className = "chat-product-cards-container";
      
      matches.forEach(item => {
        const stockClass = item.stock >= 15 ? "stock-high" : item.stock >= 5 ? "stock-med" : "stock-low";
        const stockText = item.stock >= 15 ? "En Stock" : item.stock >= 5 ? "Stock Moderado" : "Últimas unidades";

        const card = document.createElement("div");
        card.className = "chat-product-card";
        card.innerHTML = `
          <div class="card-top-row">
            <span class="card-prod-name">${escapeHtml(item.producto)}</span>
            <span class="item-id-badge">#${item.id}</span>
          </div>
          <div class="card-prod-price">${item.precio_formateado} CLP</div>
          <div class="card-prod-stock ${stockClass}">
            ${item.stock} unidades (${stockText})
          </div>
        `;
        cardsContainer.appendChild(card);
      });
      bubble.appendChild(cardsContainer);
    }

    // Message Footer Actions (Copy & Read Aloud)
    const footer = document.createElement("div");
    footer.className = "message-footer-actions";
    
    footer.innerHTML = `
      <span class="message-time">${timestamp}</span>
      <button class="msg-action-btn copy-btn" title="Copiar texto">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
        </svg>
        Copiar
      </button>
      ${sender === "bot" ? `
        <button class="msg-action-btn speak-btn" title="Leer en voz alta">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          </svg>
          Escuchar
        </button>
      ` : ""}
    `;

    // Copy event listener
    const copyBtn = footer.querySelector(".copy-btn");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(text).then(() => {
          copyBtn.innerHTML = "✓ ¡Copiado!";
          setTimeout(() => {
            copyBtn.innerHTML = `
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              Copiar
            `;
          }, 2000);
        });
      });
    }

    // Speak event listener
    const speakBtn = footer.querySelector(".speak-btn");
    if (speakBtn) {
      speakBtn.addEventListener("click", () => {
        speakText(text);
      });
    }

    bubble.appendChild(footer);
    row.appendChild(avatar);
    row.appendChild(bubble);
    chatMessages.appendChild(row);
  }

  function showTypingIndicator() {
    const row = document.createElement("div");
    row.className = "message-row bot typing-indicator-row";
    row.id = "typing-indicator";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.innerHTML = "⚡";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble typing-bubble";
    bubble.innerHTML = `
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    `;

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatMessages.appendChild(row);
    return row;
  }

  function clearChat() {
    chatMessages.innerHTML = "";
    if (welcomeCard) {
      welcomeCard.style.display = "block";
      chatMessages.appendChild(welcomeCard);
    }
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  /* ==========================================================================
     SPEECH SYNTHESIS & RECOGNITION (VOICE)
     ========================================================================== */
  function speakText(text) {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel(); // Stop any ongoing speech

    // Clean text from markdown symbols for clear pronunciation
    const cleanText = text
      .replace(/[*_#`]/g, "")
      .replace(/CLP/g, "pesos chilenos")
      .replace(/un\./g, "unidades");

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = "es-ES";
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    
    // Choose Spanish voice if available
    const voices = window.speechSynthesis.getVoices();
    const spanishVoice = voices.find(v => v.lang.startsWith("es"));
    if (spanishVoice) utterance.voice = spanishVoice;

    window.speechSynthesis.speak(utterance);
  }

  function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (voiceBtn) voiceBtn.style.display = "none";
      return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "es-CL";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      isRecognitionActive = true;
      voiceBtn.classList.add("recording");
      voiceBtn.title = "Escuchando... habla ahora";
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      userInput.value = transcript;
      handleSendMessage();
    };

    recognition.onerror = (event) => {
      console.warn("Speech recognition error:", event.error);
      stopVoiceRecognition();
    };

    recognition.onend = () => {
      stopVoiceRecognition();
    };
  }

  function toggleVoiceRecognition() {
    if (!recognition) return;
    if (isRecognitionActive) {
      recognition.stop();
    } else {
      try {
        recognition.start();
      } catch (err) {
        console.error("Speech recognition start failed:", err);
      }
    }
  }

  function stopVoiceRecognition() {
    isRecognitionActive = false;
    if (voiceBtn) {
      voiceBtn.classList.remove("recording");
      voiceBtn.title = "Dictado por voz";
    }
  }

  function updateTtsButtonState() {
    if (!toggleTtsBtn) return;
    if (isTtsEnabled) {
      toggleTtsBtn.classList.add("secondary-btn", "active");
      toggleTtsBtn.title = "Voz automática ACTIVADA";
    } else {
      toggleTtsBtn.classList.remove("secondary-btn", "active");
      toggleTtsBtn.title = "Voz automática DESACTIVADA";
    }
  }

  /* ==========================================================================
     UTILITY HELPERS
     ========================================================================== */
  function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);

    // Bold **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Inline code `code`
    formatted = formatted.replace(/`(.*?)`/g, "<code>$1</code>");

    // Bullet points (• or -)
    formatted = formatted.replace(/^[•\-]\s+(.*)$/gm, "• $1");

    return formatted;
  }
});
