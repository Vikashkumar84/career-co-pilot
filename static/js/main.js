/* ==========================================================================
   Career Copilot — Core SaaS Frontend Logic & Gemini Pro Chat Client
   ========================================================================== */

// Automatic CSRF protection for all state-modifying fetch requests
(() => {
  const originalFetch = window.fetch;
  window.fetch = function(url, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
      if (csrfToken) {
        // Always inject CSRF token header
        if (options.headers instanceof Headers) {
          if (!options.headers.has('X-CSRFToken')) options.headers.set('X-CSRFToken', csrfToken);
        } else {
          options.headers = options.headers || {};
          if (!options.headers['X-CSRFToken']) options.headers['X-CSRFToken'] = csrfToken;
        }
        // IMPORTANT: Do NOT set Content-Type when body is FormData —
        // the browser must set it automatically with the correct multipart boundary.
        const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData;
        if (!isFormData && !options.headers['Content-Type'] && !(options.headers instanceof Headers && options.headers.has('Content-Type'))) {
          // Only set application/json if no content type and not FormData
          // (caller must set it explicitly for JSON payloads)
        }
      }
    }
    return originalFetch.call(this, url, options);
  };
})();

/* ---------- Toast Notifications ---------- */
function ensureToastContainer() {
  let el = document.querySelector('.cc-toast-container');
  if (!el) {
    el = document.createElement('div');
    el.className = 'cc-toast-container';
    document.body.appendChild(el);
  }
  return el;
}

function showToast(message, type = 'info') {
  const container = ensureToastContainer();
  const icon = type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-circle-exclamation' : 'fa-circle-info';
  const toast = document.createElement('div');
  toast.className = `cc-toast ${type}`;
  toast.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(30px)';
    toast.style.transition = 'all .25s ease';
    setTimeout(() => toast.remove(), 260);
  }, 3200);
}

/* ---------- Client-side Form Validation ---------- */
function validateForm(form) {
  let valid = true;
  form.querySelectorAll('[required]').forEach((field) => {
    const group = field.closest('.form-group-cc') || field.parentElement;
    const existingError = group.querySelector('.field-error');
    if (existingError) existingError.remove();
    field.classList.remove('is-invalid');

    if ((field.type === 'checkbox' && !field.checked) || (field.type !== 'checkbox' && (!field.value || !field.value.trim()))) {
      valid = false;
      field.classList.add('is-invalid');
      const err = document.createElement('div');
      err.className = 'field-error text-danger small mt-1';
      err.textContent = 'This field is required.';
      group.appendChild(err);
    } else if (field.type === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(field.value)) {
      valid = false;
      field.classList.add('is-invalid');
      const err = document.createElement('div');
      err.className = 'field-error text-danger small mt-1';
      err.textContent = 'Please enter a valid email address.';
      group.appendChild(err);
    }
  });
  return valid;
}

/* ---------- Global Initializations ---------- */
document.addEventListener('DOMContentLoaded', () => {
  // Mobile sidebar toggle for dashboard app shell
  const hamburger = document.querySelector('#hamburgerBtn') || document.querySelector('.hamburger-btn');
  const sidebar = document.querySelector('#ccSidebar') || document.querySelector('.cc-sidebar');
  const backdrop = document.querySelector('#sidebarBackdrop') || document.querySelector('.sidebar-backdrop');

  if (hamburger && sidebar) {
    hamburger.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      if (backdrop) backdrop.classList.toggle('show');
    });
  }

  if (backdrop && sidebar) {
    backdrop.addEventListener('click', () => {
      sidebar.classList.remove('open');
      backdrop.classList.remove('show');
    });
  }

  // ---------- Live Gemini Pro Chat Assistant Widget ----------
  const chatFab = document.querySelector('#chatFab');
  const chatPanel = document.querySelector('#chatPanel');
  const chatClose = document.querySelector('#chatClose');
  const chatBody = document.querySelector('#chatBody');
  const chatInput = document.querySelector('#chatInput');
  const chatSend = document.querySelector('#chatSend');

  if (chatFab && chatPanel) {
    chatFab.addEventListener('click', () => {
      chatPanel.classList.toggle('d-none');
      if (!chatPanel.classList.contains('d-none') && chatInput) {
        chatInput.focus();
      }
    });

    if (chatClose) {
      chatClose.addEventListener('click', () => chatPanel.classList.add('d-none'));
    }

    const sendChatMessage = async () => {
      const text = chatInput.value.trim();
      if (!text) return;

      // Append User message
      const userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user';
      userBubble.textContent = text;
      chatBody.appendChild(userBubble);
      chatInput.value = '';
      chatBody.scrollTop = chatBody.scrollHeight;

      // Show typing indicator
      const typing = document.createElement('div');
      typing.className = 'chat-bubble ai typing-dots';
      typing.innerHTML = '<span></span><span></span><span></span>';
      chatBody.appendChild(typing);
      chatBody.scrollTop = chatBody.scrollHeight;

      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text }),
        });

        const data = await response.json();
        typing.remove();

        const aiBubble = document.createElement('div');
        aiBubble.className = 'chat-bubble ai';
        aiBubble.textContent = data.reply || "I'm ready to help with your tech career journey.";
        chatBody.appendChild(aiBubble);
        chatBody.scrollTop = chatBody.scrollHeight;

      } catch (err) {
        typing.remove();
        const errBubble = document.createElement('div');
        errBubble.className = 'chat-bubble ai text-danger';
        errBubble.textContent = "Unable to connect to Gemini Pro advisor right now. Please try again.";
        chatBody.appendChild(errBubble);
        chatBody.scrollTop = chatBody.scrollHeight;
      }
    };

    if (chatSend) {
      chatSend.addEventListener('click', sendChatMessage);
    }
    if (chatInput) {
      chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          sendChatMessage();
        }
      });
    }
  }
});
