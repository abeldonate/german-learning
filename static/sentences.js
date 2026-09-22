const wordLimitInput = document.getElementById("wordLimit");
const wordLimitValue = document.getElementById("wordLimitValue");
const coveragePercent = document.getElementById("coveragePercent");
const storyEl = document.getElementById("story");
const translationSection = document.getElementById("translation");
const translationText = document.getElementById("translationText");
const generateBtn = document.getElementById("generateBtn");
const translateBtn = document.getElementById("translateBtn");
const resetBtn = document.getElementById("resetBtn");
const statusEl = document.getElementById("status");
const toneBtn = document.getElementById("toneBtn");
const toneLabel = document.getElementById("toneLabel");
const tonePopover = document.getElementById("tonePopover");
const toneGrid = document.getElementById("toneGrid");
const toneDesc = document.getElementById("toneDesc");

let currentSentence = "";
let currentTranslation = "";
let toneX = window.APP_CONFIG.toneDefault.x;
let toneY = window.APP_CONFIG.toneDefault.y;

wordLimitInput.addEventListener("input", () => {
  wordLimitValue.textContent = wordLimitInput.value;
  coveragePercent.textContent = window.APP_CONFIG.coverageByWordLimit[wordLimitInput.value];
});

function updateToneDisplay() {
  const styleLabel = window.APP_CONFIG.toneStyleLabels[toneX];
  const moodLabel = window.APP_CONFIG.toneSeriousnessLabels[toneY];
  toneLabel.textContent = `${styleLabel} / ${moodLabel}`;
  toneDesc.textContent = `${styleLabel} · ${moodLabel}`;
  toneGrid.querySelectorAll(".tone-cell").forEach((cell) => {
    cell.classList.toggle(
      "selected",
      Number(cell.dataset.x) === toneX && Number(cell.dataset.y) === toneY
    );
  });
}

function buildToneGrid() {
  const { toneStyleLabels, toneSeriousnessLabels } = window.APP_CONFIG;
  toneGrid.innerHTML = "";
  for (let y = 0; y < toneSeriousnessLabels.length; y++) {
    for (let x = 0; x < toneStyleLabels.length; x++) {
      const cell = document.createElement("button");
      cell.type = "button";
      cell.className = "tone-cell";
      cell.dataset.x = x;
      cell.dataset.y = y;
      cell.title = `${toneStyleLabels[x]} / ${toneSeriousnessLabels[y]}`;
      cell.addEventListener("click", () => {
        toneX = x;
        toneY = y;
        updateToneDisplay();
      });
      toneGrid.appendChild(cell);
    }
  }
  updateToneDisplay();
}

function openTonePopover() {
  tonePopover.hidden = false;
  toneBtn.setAttribute("aria-expanded", "true");
}

function closeTonePopover() {
  tonePopover.hidden = true;
  toneBtn.setAttribute("aria-expanded", "false");
}

toneBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  if (tonePopover.hidden) openTonePopover();
  else closeTonePopover();
});

document.addEventListener("click", (e) => {
  if (!tonePopover.hidden && !tonePopover.contains(e.target) && e.target !== toneBtn) {
    closeTonePopover();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !tonePopover.hidden) closeTonePopover();
});

buildToneGrid();

function setBusy(busy, message = "") {
  generateBtn.disabled = busy;
  translateBtn.disabled = busy || !currentSentence;
  resetBtn.disabled = busy || !currentSentence;
  statusEl.textContent = message;
}

function renderSentence() {
  if (!currentSentence) {
    storyEl.innerHTML = '<p class="placeholder">Click "Generate" to start using only your selected vocabulary.</p>';
    return;
  }
  storyEl.innerHTML = `<p><span class="sentence">${escapeHtml(currentSentence)}</span></p>`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function generateNext() {
  setBusy(true, "");
  translationSection.hidden = true;
  try {
    const res = await fetch("/api/sentences/next", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wordLimit: Number(wordLimitInput.value), toneX, toneY }),
    });
    if (!res.ok) throw new Error(`Server error (${res.status})`);
    const data = await res.json();
    if (data.sentence) {
      currentSentence = data.sentence;
      currentTranslation = data.translation || "";
      renderSentence();
    }
    setBusy(false, "");
  } catch (err) {
    setBusy(false, `Error: ${err.message}`);
  }
}

function translateSentence() {
  // Pre-fetched alongside the sentence, so this is instant.
  translationText.textContent = currentTranslation;
  translationSection.hidden = false;
}

async function resetStory() {
  setBusy(true, "Restarting…");
  try {
    await fetch("/api/sentences/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ wordLimit: Number(wordLimitInput.value), toneX, toneY }),
    });
  } catch (err) {
    // Local state still resets below even if the request fails.
  }
  currentSentence = "";
  currentTranslation = "";
  renderSentence();
  translationSection.hidden = true;
  setBusy(false, "");
}

generateBtn.addEventListener("click", generateNext);
translateBtn.addEventListener("click", translateSentence);
resetBtn.addEventListener("click", resetStory);

document.addEventListener("keydown", (e) => {
  if (e.repeat) return;

  if (e.code === window.APP_CONFIG.generateKeyCode) {
    e.preventDefault();
    if (!generateBtn.disabled) generateNext();
  } else if (e.code === window.APP_CONFIG.translateKeyCode) {
    e.preventDefault();
    if (!translateBtn.disabled) translateSentence();
  }
});
