/* Essential preference is stored locally; no optional trackers are installed. */
(() => {
  const key = 'cc-cookie-preference-v1';
  const banner = document.getElementById('cookie-banner');
  const show = () => { if (banner) { banner.hidden = false; document.getElementById('cookie-reject').focus(); } };
  const save = value => { try { localStorage.setItem(key,value); } catch (_) {} if (banner) banner.hidden = true; };
  try { if (!localStorage.getItem(key)) { if (banner) banner.hidden = false; } } catch (_) { if (banner) banner.hidden = false; }
  document.getElementById('cookie-accept')?.addEventListener('click', () => save('accepted'));
  document.getElementById('cookie-reject')?.addEventListener('click', () => save('rejected'));
  document.getElementById('cookie-settings')?.addEventListener('click',show);
  document.getElementById('clear-local-data')?.addEventListener('click', () => {
    try { localStorage.removeItem(key); sessionStorage.clear(); document.getElementById('clear-result').textContent='Saved cookie preference removed. Other browser or server data, if any, must be handled separately.'; }
    catch (_) { document.getElementById('clear-result').textContent='Could not clear browser storage. Use your browser settings.'; }
  });
  document.addEventListener('keydown',e=>{ if(e.key==='Escape') {document.getElementById('chatPanel')?.classList.add('d-none');} });
})();