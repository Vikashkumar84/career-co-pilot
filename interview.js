/* ==========================================================================
   Career Copilot — Interview Preparation page behaviour
   Sample question bank shown below is placeholder data; in production this
   is fetched from Flask (e.g. GET /api/interview-questions?type=technical).
   ========================================================================== */

const sampleQuestions = {
  technical: [
    { q: 'Explain the difference between stack and queue.', a: 'A stack follows LIFO (Last In, First Out) — the last element added is removed first. A queue follows FIFO (First In, First Out) — the first element added is the first removed. Stacks use push/pop; queues use enqueue/dequeue.' },
    { q: 'What is the time complexity of binary search?', a: 'Binary search runs in O(log n) time because it halves the search space on every comparison, provided the array is sorted.' },
    { q: 'What is the difference between == and === in JavaScript?', a: '== compares values after type coercion, while === compares both value and type without coercion.' },
  ],
  hr: [
    { q: 'Tell me about yourself.', a: 'Give a concise summary of your background, key skills, and what you are looking for — tailored to the role you are applying for.' },
    { q: 'Why do you want to work here?', a: 'Connect your skills and career goals to the company\'s mission, products, and growth opportunities.' },
  ],
  coding: [
    { q: 'Reverse a linked list — describe your approach.', a: 'Iterate through the list, reversing the "next" pointer of each node as you go, tracking previous, current, and next nodes until you reach the end.' },
  ],
};

let currentType = 'technical';
let currentIndex = 0;
let score = { correct: 0, total: 0 };
const reviewSet = new Set();

function renderQuestion() {
  const set = sampleQuestions[currentType];
  const item = set[currentIndex % set.length];
  document.querySelector('#questionText').textContent = item.q;
  document.querySelector('#answerText').textContent = item.a;
  document.querySelector('#answerBox').classList.add('d-none');
  document.querySelector('#questionCounter').textContent = `Question ${(currentIndex % set.length) + 1} of ${set.length}`;
  const markBtn = document.querySelector('#markReviewBtn');
  markBtn.classList.toggle('btn-primary-cc', reviewSet.has(currentIndex));
  markBtn.classList.toggle('btn-outline-cc', !reviewSet.has(currentIndex));
}

document.addEventListener('DOMContentLoaded', () => {
  if (!document.querySelector('#questionText')) return;

  document.querySelectorAll('[data-interview-type]').forEach((btn) => {
    btn.addEventListener('click', () => {
      currentType = btn.dataset.interviewType;
      currentIndex = 0;
      document.querySelectorAll('[data-interview-type]').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      renderQuestion();
    });
  });

  document.querySelector('#showAnswerBtn').addEventListener('click', () => {
    document.querySelector('#answerBox').classList.remove('d-none');
  });

  document.querySelector('#nextQuestionBtn').addEventListener('click', () => {
    currentIndex += 1;
    score.total += 1;
    document.querySelector('#scoreText').textContent = `${score.correct}/${score.total}`;
    const pct = score.total ? Math.round((score.correct / score.total) * 100) : 0;
    document.querySelector('#scoreBar').style.width = pct + '%';
    renderQuestion();
  });

  document.querySelector('#markReviewBtn').addEventListener('click', () => {
    if (reviewSet.has(currentIndex)) { reviewSet.delete(currentIndex); }
    else { reviewSet.add(currentIndex); showToast('Marked for review', 'info'); }
    renderQuestion();
  });

  renderQuestion();
});
