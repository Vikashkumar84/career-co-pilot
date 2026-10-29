/* ==========================================================================
   Career Copilot — Interview Preparation page behaviour
   Saves session results to /api/interview/save (POST, JSON).
   ========================================================================== */

const sampleQuestions = {
  technical: [
    { q: 'Explain the difference between stack and queue.', a: 'A stack follows LIFO (Last In, First Out) — the last element added is removed first. A queue follows FIFO (First In, First Out) — the first element added is the first removed. Stacks use push/pop; queues use enqueue/dequeue.' },
    { q: 'What is the time complexity of binary search?', a: 'Binary search runs in O(log n) time because it halves the search space on every comparison, provided the array is sorted.' },
    { q: 'What is the difference between == and === in JavaScript?', a: '== compares values after type coercion, while === compares both value and type without coercion.' },
    { q: 'What is a foreign key in SQL?', a: 'A foreign key is a column (or set of columns) in one table that references the primary key of another table, enforcing referential integrity.' },
    { q: 'What is the difference between GET and POST HTTP methods?', a: 'GET retrieves data and sends parameters in the URL; POST sends data in the request body, suitable for creating or modifying resources.' },
  ],
  hr: [
    { q: 'Tell me about yourself.', a: 'Give a concise summary of your background, key skills, and what you are looking for — tailored to the role you are applying for.' },
    { q: 'Why do you want to work here?', a: 'Connect your skills and career goals to the company\'s mission, products, and growth opportunities.' },
    { q: 'What is your greatest strength?', a: 'Choose a genuine strength backed by a specific example that is relevant to the role.' },
    { q: 'Where do you see yourself in 5 years?', a: 'Show ambition aligned with the company\'s growth and the natural progression of the role.' },
  ],
  coding: [
    { q: 'Reverse a linked list — describe your approach.', a: 'Iterate through the list, reversing the "next" pointer of each node as you go, tracking previous, current, and next nodes until you reach the end.' },
    { q: 'Find the two numbers in an array that sum to a target.', a: 'Use a hash map: for each number, check if (target - number) is already in the map. If yes, return the pair. This runs in O(n) time.' },
    { q: 'Implement a function to check if a string is a palindrome.', a: 'Compare characters from both ends moving towards the centre, or reverse the string and check equality. Ignore case and non-alphanumeric characters for robust solutions.' },
  ],
};

let currentType  = 'technical';
let currentIndex = 0;
let score        = { correct: 0, total: 0 };
const reviewSet  = new Set();

function renderQuestion() {
  const set  = sampleQuestions[currentType];
  const item = set[currentIndex % set.length];
  document.querySelector('#questionText').textContent = item.q;
  document.querySelector('#answerText').textContent   = item.a;
  document.querySelector('#answerBox').classList.add('d-none');
  document.querySelector('#questionCounter').textContent =
    `Question ${(currentIndex % set.length) + 1} of ${set.length}`;

  const markBtn = document.querySelector('#markReviewBtn');
  markBtn.classList.toggle('btn-primary-cc', reviewSet.has(currentIndex));
  markBtn.classList.toggle('btn-outline-cc',  !reviewSet.has(currentIndex));
}

async function saveSession() {
  const scorePct = score.total
    ? Math.round((score.correct / score.total) * 100)
    : 0;
  try {
    await fetch('/api/interview/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type:           currentType,
        questions_done: score.total,
        score_pct:      scorePct,
      }),
    });
  } catch (_) { /* silently ignore if offline */ }
}

document.addEventListener('DOMContentLoaded', () => {
  if (!document.querySelector('#questionText')) return;

  document.querySelectorAll('[data-interview-type]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (score.total > 0) await saveSession();

      currentType  = btn.dataset.interviewType;
      currentIndex = 0;
      score        = { correct: 0, total: 0 };
      document.querySelector('#scoreText').textContent = '0/0';
      document.querySelector('#scoreBar').style.width  = '0%';

      document.querySelectorAll('[data-interview-type]').forEach((b) => {
        b.classList.remove('active', 'btn-primary-cc');
        b.classList.add('btn-ghost-cc');
      });
      btn.classList.add('active', 'btn-primary-cc');
      btn.classList.remove('btn-ghost-cc');
      renderQuestion();
    });
  });

  document.querySelector('#showAnswerBtn').addEventListener('click', () => {
    document.querySelector('#answerBox').classList.remove('d-none');
    // Increment correct when they view the answer — simple proxy for "knew it"
    score.correct += 1;
    updateScoreUI();
  });

  document.querySelector('#nextQuestionBtn').addEventListener('click', () => {
    currentIndex  += 1;
    score.total   += 1;
    updateScoreUI();
    renderQuestion();
    // Auto-save every 5 questions
    if (score.total % 5 === 0) saveSession();
  });

  document.querySelector('#markReviewBtn').addEventListener('click', () => {
    if (reviewSet.has(currentIndex)) {
      reviewSet.delete(currentIndex);
    } else {
      reviewSet.add(currentIndex);
      showToast('Marked for review', 'info');
    }
    renderQuestion();
  });

  // Save session when user leaves the page
  window.addEventListener('beforeunload', () => {
    if (score.total > 0) saveSession();
  });

  renderQuestion();
});

function updateScoreUI() {
  document.querySelector('#scoreText').textContent = `${score.correct}/${score.total}`;
  const pct = score.total ? Math.round((score.correct / score.total) * 100) : 0;
  document.querySelector('#scoreBar').style.width = pct + '%';
}
