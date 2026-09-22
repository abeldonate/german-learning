const wordLimitInput = document.getElementById("wordLimit");
const wordLimitValue = document.getElementById("wordLimitValue");
const coveragePercent = document.getElementById("coveragePercent");
const board = document.getElementById("board");
const feedbackEl = document.getElementById("feedback");
const generateBtn = document.getElementById("generateBtn");
const translateBtn = document.getElementById("translateBtn");
const resetBtn = document.getElementById("resetBtn");
const statusEl = document.getElementById("status");

let currentItem = null; // { options: [{word, gloss}, ...], answer }
let answered = false;
let glossesRevealed = false;

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

function renderBoard() {
  feedbackEl.textContent = "";
  feedbackEl.className = "feedback";
  glossesRevealed = false;

  if (!currentItem) {
    board.innerHTML = '<p class="placeholder">Click "Generate" to get 4 words.</p>';
    return;
  }

  board.innerHTML =
    '<div class="oddoneout-grid">' +
    currentItem.options
      .map(
        (opt) =>
          `<button type="button" class="oddoneout-tile" data-word="${escapeHtml(opt.word)}">` +
          `<span class="oddoneout-word">${escapeHtml(opt.word)}</span>` +
          `<span class="oddoneout-gloss" hidden>${escapeHtml(opt.gloss)}</span>` +
          `</button>`
      )
      .join("") +
    "</div>";

  board.querySelectorAll(".oddoneout-tile").forEach((tile) => {
    tile.addEventListener("click", () => selectTile(tile));
  });
}

function selectTile(tile) {
  if (!currentItem || answered) return;
  answered = true;

  const chosenWord = tile.dataset.word;
  const correct = chosenWord === currentItem.answer;

  board.querySelectorAll(".oddoneout-tile").forEach((t) => {
    t.disabled = true;
    if (t.dataset.word === currentItem.answer) t.classList.add("correct");
    else if (t === tile) t.classList.add("incorrect");
  });

  feedbackEl.textContent = correct
    ? "✓ Correct!"
    : `✗ Not quite. The odd one out was "${currentItem.answer}".`;
  feedbackEl.className = correct ? "feedback correct" : "feedback incorrect";
}

async function generateNext() {
  setBusy(true, "");
  answered = false;
  try {
    const res = await fetch("/api/odd-one-out/next", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wordLimit: Number(wordLimitInput.value) }),
    });
    if (!res.ok) throw new Error(`Server error (${res.status})`);
    const data = await res.json();
    currentItem = data;
    renderBoard();
    setBusy(false, "");
  } catch (err) {
    setBusy(false, `Error: ${err.message}`);
  }
}

function revealGlosses() {
  if (!currentItem || glossesRevealed) return;
  glossesRevealed = true;
  board.querySelectorAll(".oddoneout-gloss").forEach((el) => {
    el.hidden = false;
  });
}

async function resetExercise() {
  setBusy(true, "Restarting…");
  try {
    await fetch("/api/odd-one-out/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wordLimit: Number(wordLimitInput.value) }),
    });
  } catch (err) {
    // Local state still resets below even if the request fails.
  }
  currentItem = null;
  answered = false;
  renderBoard();
  setBusy(false, "");
}

generateBtn.addEventListener("click", generateNext);
translateBtn.addEventListener("click", revealGlosses);
resetBtn.addEventListener("click", resetExercise);

document.addEventListener("keydown", (e) => {
  if (e.repeat) return;

  if (e.code === window.APP_CONFIG.generateKeyCode) {
    e.preventDefault();
    if (!generateBtn.disabled) generateNext();
  } else if (e.code === window.APP_CONFIG.translateKeyCode) {
    e.preventDefault();
    if (!translateBtn.disabled) revealGlosses();
  }
});
