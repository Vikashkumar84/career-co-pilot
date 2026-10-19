/* ==========================================================================
   Career Copilot — Shared utilities
   Used across every page. Flask can inject data via Jinja and call
   these same helpers (e.g. showToast, animateProgressBars).
   ========================================================================== */

/* ---------- Toast notifications ---------- */
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

/* ---------- Animate .cc-progress-bar elements from data-value ---------- */
function animateProgressBars(root = document) {
  root.querySelectorAll('.cc-progress-bar[data-value]').forEach((bar) => {
    const val = bar.getAttribute('data-value');
    requestAnimationFrame(() => { bar.style.width = val + '%'; });
  });
}

/* ---------- Simple client-side form validation ---------- */
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
      err.textContent = 'Enter a valid email address.';
      group.appendChild(err);
    }
  });
  return valid;
}

/* ---------- Mobile hamburger for public navbar ---------- */
document.addEventListener('DOMContentLoaded', () => {
  animateProgressBars();

  const navToggle = document.querySelector('.navbar-toggler-cc');
  const navMenu = document.querySelector('#ccNavMenu');
  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => navMenu.classList.toggle('show'));
  }

  // Generic sidebar toggle (dashboard shell) reused on every internal page
  const hamburger = document.querySelector('.hamburger-btn');
  const sidebar = document.querySelector('.cc-sidebar');
  const backdrop = document.querySelector('.sidebar-backdrop');
  if (hamburger && sidebar && backdrop) {
    hamburger.addEventListener('click', () => {
      sidebar.classList.add('open');
      backdrop.classList.add('show');
    });
    backdrop.addEventListener('click', () => {
      sidebar.classList.remove('open');
      backdrop.classList.remove('show');
    });
  }

  // ---------- Ask Career Copilot chat widget ----------
  const chatFab = document.querySelector('#chatFab');
  const chatPanel = document.querySelector('#chatPanel');
  const chatClose = document.querySelector('#chatClose');
  const chatBody = document.querySelector('#chatBody');
  const chatInput = document.querySelector('#chatInput');
  const chatSend = document.querySelector('#chatSend');

  if (chatFab && chatPanel) {
    chatFab.addEventListener('click', () => chatPanel.classList.toggle('d-none'));
    chatClose.addEventListener('click', () => chatPanel.classList.add('d-none'));

    const sendMessage = async () => {
      const text = chatInput.value.trim();
      if (!text) return;
      const userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user';
      userBubble.textContent = text;
      chatBody.appendChild(userBubble);
      chatInput.value = '';
      chatBody.scrollTop = chatBody.scrollHeight;

      const typing = document.createElement('div');
      typing.className = 'chat-bubble ai typing-dots';
      typing.innerHTML = '<span></span><span></span><span></span>';
      chatBody.appendChild(typing);
      chatBody.scrollTop = chatBody.scrollHeight;

      // Placeholder reply — replace with:
      // const data = await callCareerCopilotAPI('/api/chat', { message: text });
      await new Promise((resolve) => setTimeout(resolve, 1000));
      typing.remove();
      const aiBubble = document.createElement('div');
      aiBubble.className = 'chat-bubble ai';
      aiBubble.textContent = 'Here is your personalized roadmap: start with core programming fundamentals, then move to your target stack, build 2–3 projects, and practice interview questions weekly.';
      chatBody.appendChild(aiBubble);
      chatBody.scrollTop = chatBody.scrollHeight;
    };

    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });
  }

  // Fetch-ready pattern for Flask backend (placeholder, no hard-coded AI logic)
  window.callCareerCopilotAPI = async function (endpoint, payload) {
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('Request failed');
      return await res.json();
    } catch (err) {
      showToast('Something went wrong. Please try again.', 'error');
      throw err;
    }
  };
});
