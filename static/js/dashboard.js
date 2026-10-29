/* ==========================================================================
   Career Copilot — Dashboard page behaviour
   ========================================================================== */

function renderProgressRing(canvasEl, percent, color = '#6C3FD1', track = '#EFE8FC') {
  const ctx = canvasEl.getContext('2d');
  const size = canvasEl.width;
  const cx = size / 2, cy = size / 2, r = size / 2 - 10;
  ctx.clearRect(0, 0, size, size);

  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = track;
  ctx.lineWidth = 14;
  ctx.stroke();

  if (percent > 0) {
    const endAngle = -Math.PI / 2 + (Math.PI * 2 * (percent / 100));
    ctx.beginPath();
    ctx.arc(cx, cy, r, -Math.PI / 2, endAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = 14;
    ctx.lineCap = 'round';
    ctx.stroke();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const ring = document.querySelector('#overallProgressRing');
  if (ring) {
    const percent = parseInt(ring.dataset.percent || '0', 10);
    renderProgressRing(ring, percent);
  }

  // Simulated "loading" skeleton -> real content swap (mirrors what a Flask
  // template + fetch() call would do once the Gemini-backed API responds)
  const skeletons = document.querySelectorAll('.dash-skeleton');
  if (skeletons.length) {
    setTimeout(() => {
      document.querySelectorAll('.dash-skeleton').forEach((el) => el.classList.add('d-none'));
      document.querySelectorAll('.dash-real').forEach((el) => el.classList.remove('d-none'));
    }, 700);
  }
});
