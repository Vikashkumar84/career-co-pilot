/* ==========================================================================
   Career Copilot — Career Analysis page behaviour
   This is API-ready: swap the setTimeout mock below for
   `await callCareerCopilotAPI('/api/analyze-career', payload)` once the
   Flask + Gemini endpoint is live. Do not hard-code final AI text in prod.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('#careerAnalysisForm');
  const resultsWrap = document.querySelector('#analysisResults');
  const loadingWrap = document.querySelector('#analysisLoading');
  const emptyState = document.querySelector('#analysisEmpty');

  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!validateForm(form)) {
      showToast('Please fill in the required fields.', 'error');
      return;
    }

    if (emptyState) emptyState.classList.add('d-none');
    if (resultsWrap) resultsWrap.classList.add('d-none');
    if (loadingWrap) loadingWrap.classList.remove('d-none');

    const payload = Object.fromEntries(new FormData(form).entries());

    // --- Placeholder for real API call ---
    // const data = await callCareerCopilotAPI('/api/analyze-career', payload);
    await new Promise((resolve) => setTimeout(resolve, 1100));
    const data = {
      recommended_career: payload.target_career || 'Web Developer',
      match_percentage: 82,
      current_skills: ['C', 'C++', 'HTML', 'CSS'],
      missing_skills: ['JavaScript', 'React', 'SQL'],
    };
    // --- end placeholder ---

    if (loadingWrap) loadingWrap.classList.add('d-none');
    if (resultsWrap) resultsWrap.classList.remove('d-none');

    document.querySelector('#matchCareerName').textContent = data.recommended_career;
    document.querySelector('#matchPercentText').textContent = data.match_percentage + '%';
    const bar = document.querySelector('#matchPercentBar');
    bar.style.width = data.match_percentage + '%';

    const haveWrap = document.querySelector('#currentSkillsWrap');
    haveWrap.innerHTML = data.current_skills.map((s) => `<span class="badge-skill badge-have">${s}</span>`).join('');

    const missingWrap = document.querySelector('#missingSkillsWrap');
    missingWrap.innerHTML = data.missing_skills.map((s) => `<span class="badge-skill badge-missing">${s}</span>`).join('');

    showToast('Sample career analysis displayed (not an AI prediction).', 'info');
    resultsWrap.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
