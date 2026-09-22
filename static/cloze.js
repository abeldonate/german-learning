const wordLimitInput = document.getElementById("wordLimit");
const wordLimitValue = document.getElementById("wordLimitValue");
const coveragePercent = document.getElementById("coveragePercent");
const sentenceBox = document.getElementById("sentenceBox");
const feedbackEl = document.getElementById("feedback");
const translationSection = document.getElementById("translation");
const translationText = document.getElementById("translationText");
const generateBtn = document.getElementById("generateBtn");
const translateBtn = document.getElementById("translateBtn");
const resetBtn = document.getElementById("resetBtn");
const statusEl = document.getElementById("status");

let currentItem = null; // { sentenceWithBlank, answer, translation }
let answered = false;

wordLimitInput.addEventListener("input", () => {
  wordLimitValue.textContent = wordLimitInput.value;
  coveragePercent.textContent = window.APP_CONFIG.coverageByWordLimit[wordLimitInput.value];
});

function setBusy(busy, message = "") {
  generateBtn.disabled = busy;
  translateBtn.disabled = busy || !currentItem;
  resetBtn.disabled = busy || !currentItem;
  statusEl.textContent = message;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderItem() {
  feedbackEl.textContent = "";
  feedbackEl.className = "feedback";

  if (!currentItem) {
    sentenceBox.innerHTML = '<p class="placeholder">Click "Generate" to get a sentence.</p>';
    return;
  }

  const [before, after] = currentItem.sentenceWithBlank.split("_____");
  sentenceBox.innerHTML =
    `<p>${escapeHtml(before)}` +
    `<input type="text" id="answerInput" class="cloze-input" autocomplete="off" spellcheck="false">` +
    `${escapeHtml(after)}</p>`;

  const answerInput = document.getElementById("answerInput");
  answerInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      checkAnswer();
    }
  });
  answerInput.focus();
}

function normalize(str) {
  return str.trim().toLowerCase();
}

function checkAnswer() {
  if (!currentItem || answered) return;
  const answerInput = document.getElementById("answerInput");
  const correct = normalize(answerInput.value) === normalize(currentItem.answer);

  answered = true;
  answerInput.disabled = true;

  if (correct) {
    feedbackEl.textContent = "✓ Correct!";
    feedbackEl.className = "feedback correct";
  } else {
    feedbackEl.textContent = `✗ Not quite. The answer was "${currentItem.answer}".`;
    feedbackEl.className = "feedback incorrect";
  }
}

async function generateNext() {
  setBusy(true, "");
  translationSection.hidden = true;
  answered = false;
  try {
    const res = await fetch("/api/cloze/next", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wordLimit: Number(wordLimitInput.value) }),
    });
    if (!res.ok) throw new Error(`Server error (${res.status})`);
    const data = await res.json();
    currentItem = data;
    renderItem();
    setBusy(false, "");
  } catch (err) {
    setBusy(false, `Error: ${err.message}`);
  }
}

function translateSentence() {
  if (!currentItem) return;
  translationText.textContent = currentItem.translation;
  translationSection.hidden = false;
}

async function resetExercise() {
  setBusy(true, "Restarting…");
  try {
    await fetch("/api/cloze/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wordLimit: Number(wordLimitInput.value) }),
    });
  } catch (err) {
    // Local state still resets below even if the request fails.
  }
  currentItem = null;
  answered = false;
  renderItem();
  translationSection.hidden = true;
  setBusy(false, "");
}

generateBtn.addEventListener("click", generateNext);
translateBtn.addEventListener("click", translateSentence);
resetBtn.addEventListener("click", resetExercise);

document.addEventListener("keydown", (e) => {
  if (e.repeat) return;

  const typingInAnswer = document.activeElement && document.activeElement.id === "answerInput";

  if (e.code === window.APP_CONFIG.generateKeyCode) {
    if (typingInAnswer) return; // let Space be typed into the answer normally
    e.preventDefault();
    if (!generateBtn.disabled) generateNext();
  } else if (e.code === window.APP_CONFIG.translateKeyCode) {
    e.preventDefault();
    if (!translateBtn.disabled) translateSentence();
  }
});
