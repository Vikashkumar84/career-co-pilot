/* ==========================================================================
   Career Copilot — Dynamic Career Analysis Handler + Resume Scanner
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#careerAnalysisForm');
  const resultsWrap = document.querySelector('#analysisResultsWrap');
  const loadingWrap = document.querySelector('#analysisLoading');
  const emptyState = document.querySelector('#analysisEmpty');
  const submitBtn = document.querySelector('#submitAnalysisBtn');

  // -------------------------------------------------------------------------
  // Resume Upload & AI Auto-Fill
  // -------------------------------------------------------------------------
  const resumeInput = document.querySelector('#resumeFileInput');
  const resumeDropZone = document.querySelector('#resumeDropZone');
  const resumeStatus = document.querySelector('#resumeStatus');
  const scanResumeBtn = document.querySelector('#scanResumeBtn');
  let _parsedResumeText = '';

  // Drag-and-drop support
  if (resumeDropZone && resumeInput) {
    resumeDropZone.addEventListener('click', () => resumeInput.click());

    resumeDropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      resumeDropZone.classList.add('drop-active');
    });

    resumeDropZone.addEventListener('dragleave', () => {
      resumeDropZone.classList.remove('drop-active');
    });

    resumeDropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      resumeDropZone.classList.remove('drop-active');
      const files = e.dataTransfer.files;
      if (files.length) {
        resumeInput.files = files;
        triggerResumeLabel(files[0].name);
      }
    });

    resumeInput.addEventListener('change', () => {
      if (resumeInput.files.length) {
        triggerResumeLabel(resumeInput.files[0].name);
      }
    });
  }

  function triggerResumeLabel(filename) {
    if (resumeStatus) {
      resumeStatus.textContent = `📄 ${filename} — ready to scan`;
      resumeStatus.className = 'small text-muted-soft mt-1';
    }
  }

  async function scanResume() {
    if (!resumeInput || !resumeInput.files.length) {
      showToast('Please select a resume file first.', 'error');
      return;
    }

    const file = resumeInput.files[0];
    const formData = new FormData();
    formData.append('resume', file);

    if (scanResumeBtn) {
      scanResumeBtn.disabled = true;
      scanResumeBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Scanning with AI...';
    }
    if (resumeStatus) {
      resumeStatus.textContent = '🔍 Gemini AI is reading your resume...';
      resumeStatus.className = 'small text-purple mt-1';
    }

    try {
      // Note: Do NOT set Content-Type manually — browser sets multipart boundary automatically
      const response = await fetch('/api/parse-resume', {
        method: 'POST',
        body: formData,
        // CSRF token is injected automatically by the global fetch wrapper in main.js
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || `Server error ${response.status}`);
      }

      const data = await response.json();
      _parsedResumeText = data.resume_text || '';

      // Auto-fill form fields with AI-extracted data
      autoFill('name', data.name);
      autoFill('education', data.education);
      autoFill('branch', data.branch);
      autoFill('current_skills', data.current_skills);
      autoFill('interests', data.interests);
      autoFill('target_career', data.target_career);

      // Set experience level if value matches an option
      if (data.experience_level) {
        const expSelect = form.querySelector('[name="experience_level"]');
        if (expSelect) {
          const options = Array.from(expSelect.options);
          const match = options.find(o => o.value.toLowerCase() === data.experience_level.toLowerCase());
          if (match) expSelect.value = match.value;
        }
      }

      if (resumeStatus) {
        resumeStatus.textContent = '✅ Resume scanned! Form auto-filled. Review and submit.';
        resumeStatus.className = 'small text-success mt-1';
      }
      showToast('Resume scanned! Form auto-filled by Gemini AI.', 'success');

    } catch (err) {
      if (resumeStatus) {
        resumeStatus.textContent = '⚠️ Scan failed. Fill the form manually.';
        resumeStatus.className = 'small text-danger mt-1';
      }
      showToast('Resume scan error: ' + err.message, 'error');
    } finally {
      if (scanResumeBtn) {
        scanResumeBtn.disabled = false;
        scanResumeBtn.innerHTML = '<i class="fa-solid fa-file-magnifying-glass me-2"></i>Scan & Auto-Fill Resume';
      }
    }
  }

  function autoFill(fieldName, value) {
    if (!value || !form) return;
    const el = form.querySelector(`[name="${fieldName}"]`);
    if (el && (!el.value || el.value.trim() === '')) {
      el.value = value;
    }
  }

  if (scanResumeBtn) {
    scanResumeBtn.addEventListener('click', (e) => {
      e.preventDefault();
      scanResume();
    });
  }

  // -------------------------------------------------------------------------
  // Career Analysis Form Submission
  // -------------------------------------------------------------------------
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!validateForm(form)) {
      showToast('Please fill in all required fields.', 'error');
      return;
    }

    // Toggle loading UI
    if (emptyState) emptyState.classList.add('d-none');
    if (resultsWrap) resultsWrap.classList.add('d-none');
    if (loadingWrap) loadingWrap.classList.remove('d-none');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Analyzing with Gemini AI...';
    }

    const payload = Object.fromEntries(new FormData(form).entries());
    // Attach resume text for enhanced analysis accuracy
    if (_parsedResumeText) {
      payload.resume_text = _parsedResumeText;
    }

    try {
      const response = await fetch('/api/analyze-career', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error ${response.status}`);
      }

      const data = await response.json();

      // Populate UI with AI results
      const careerNameEl = document.querySelector('#matchCareerName');
      if (careerNameEl) careerNameEl.textContent = data.recommended_career || payload.target_career;

      const pctText = document.querySelector('#matchPercentText');
      if (pctText) pctText.textContent = (data.match_percentage || 0) + '%';

      const bar = document.querySelector('#matchPercentBar');
      if (bar) {
        bar.style.width = '0%';
        setTimeout(() => { bar.style.width = (data.match_percentage || 0) + '%'; }, 50);
      }

      const summaryEl = document.querySelector('#analysisSummaryText');
      if (summaryEl && data.ai_summary) summaryEl.textContent = data.ai_summary;

      const haveWrap = document.querySelector('#currentSkillsWrap');
      if (haveWrap) {
        haveWrap.innerHTML = (data.current_skills || [])
          .map((s) => `<span class="badge-skill bg-emerald-soft text-emerald">${s}</span>`)
          .join('');
      }

      const missingWrap = document.querySelector('#missingSkillsWrap');
      if (missingWrap) {
        missingWrap.innerHTML = (data.missing_skills || [])
          .map((s) => `<span class="badge-skill badge-missing">${s}</span>`)
          .join('');
      }

      if (loadingWrap) loadingWrap.classList.add('d-none');
      if (resultsWrap) resultsWrap.classList.remove('d-none');

      showToast('AI analysis completed and saved to your profile!', 'success');
      resultsWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      if (loadingWrap) loadingWrap.classList.add('d-none');
      if (emptyState) emptyState.classList.remove('d-none');
      showToast('Analysis error: ' + err.message, 'error');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles me-2"></i>Generate AI Career Analysis';
      }
    }
  });
});
