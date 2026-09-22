const draftInput = document.getElementById("draftInput");
const correctBtn = document.getElementById("correctBtn");
const clearBtn = document.getElementById("clearBtn");
const statusEl = document.getElementById("status");
const resultSection = document.getElementById("resultSection");
const correctedText = document.getElementById("correctedText");
const explanationSection = document.getElementById("explanationSection");
const explanationText = document.getElementById("explanationText");
const dateLabel = document.getElementById("dateLabel");
const calendarBtn = document.getElementById("calendarBtn");
const calendarPopover = document.getElementById("calendarPopover");
const calPrevBtn = document.getElementById("calPrevBtn");
const calNextBtn = document.getElementById("calNextBtn");
const calMonthLabel = document.getElementById("calMonthLabel");
const calWeekdays = document.getElementById("calWeekdays");
const calGrid = document.getElementById("calGrid");

const today = window.APP_CONFIG.today; // "YYYY-MM-DD"
let selectedDate = today;
let savedDates = new Set();
let calendarView = { year: Number(today.slice(0, 4)), month: Number(today.slice(5, 7)) - 1 };

function pad(n) {
  return String(n).padStart(2, "0");
}

function isoDate(y, m, d) {
  return `${y}-${pad(m + 1)}-${pad(d)}`;
}

function hasText() {
  return draftInput.value.trim().length > 0;
}

function setBusy(busy, message = "") {
  correctBtn.disabled = busy || !hasText();
  clearBtn.disabled = busy || !hasText();
  statusEl.textContent = message;
}

draftInput.addEventListener("input", () => setBusy(false, ""));

function updateDateLabel() {
  dateLabel.innerHTML = "";
  if (selectedDate === today) {
    dateLabel.append(`Today — ${selectedDate}`);
    return;
  }
  dateLabel.append(`Viewing ${selectedDate}`);
  const backLink = document.createElement("a");
  backLink.href = "#";
  backLink.textContent = "Back to today";
  backLink.addEventListener("click", (e) => {
    e.preventDefault();
    selectDate(today);
  });
  dateLabel.append(backLink);
}

function renderWeekdays() {
  calWeekdays.innerHTML = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    .map((w) => `<span>${w}</span>`)
    .join("");
}

function renderCalendar() {
  const { year, month } = calendarView;
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  calMonthLabel.textContent = `${monthNames[month]} ${year}`;

  const firstOfMonth = new Date(year, month, 1);
  const startOffset = (firstOfMonth.getDay() + 6) % 7; // Monday-first grid
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  calGrid.innerHTML = "";
  for (let i = 0; i < startOffset; i++) {
    calGrid.appendChild(document.createElement("div"));
  }
  for (let day = 1; day <= daysInMonth; day++) {
    const dateStr = isoDate(year, month, day);
    const cell = document.createElement("button");
    cell.type = "button";
    cell.className = "calendar-cell";
    cell.textContent = String(day);
    if (dateStr === today) cell.classList.add("today");
    if (dateStr === selectedDate) cell.classList.add("selected");
    if (savedDates.has(dateStr)) cell.classList.add("has-entry");
    if (dateStr > today) cell.disabled = true;
    cell.addEventListener("click", () => selectDate(dateStr));
    calGrid.appendChild(cell);
  }
}

function openCalendar() {
  calendarPopover.hidden = false;
  calendarBtn.setAttribute("aria-expanded", "true");
}

function closeCalendar() {
  calendarPopover.hidden = true;
  calendarBtn.setAttribute("aria-expanded", "false");
}

calendarBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  if (calendarPopover.hidden) openCalendar();
  else closeCalendar();
});

document.addEventListener("click", (e) => {
  if (!calendarPopover.hidden && !calendarPopover.contains(e.target) && e.target !== calendarBtn) {
    closeCalendar();
  }
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !calendarPopover.hidden) closeCalendar();
});

calPrevBtn.addEventListener("click", () => {
  calendarView.month--;
  if (calendarView.month < 0) {
    calendarView.month = 11;
    calendarView.year--;
  }
  renderCalendar();
});

calNextBtn.addEventListener("click", () => {
  calendarView.month++;
  if (calendarView.month > 11) {
    calendarView.month = 0;
    calendarView.year++;
  }
  renderCalendar();
});

async function fetchDates() {
  try {
    const res = await fetch("/api/diary/dates");
    const data = await res.json();
    savedDates = new Set(data.dates || []);
    renderCalendar();
  } catch (err) {
    // Non-critical - the calendar just won't show entry dots.
  }
}

async function loadEntry(dateStr) {
  try {
    const res = await fetch(`/api/diary/entry?date=${encodeURIComponent(dateStr)}`);
    const data = await res.json();
    if (data.exists) {
      draftInput.value = data.draft;
      correctedText.textContent = data.corrected;
      resultSection.hidden = false;
      explanationText.textContent = data.explanation;
      explanationSection.hidden = !data.explanation;
    } else {
      draftInput.value = "";
      resultSection.hidden = true;
      explanationSection.hidden = true;
    }
    setBusy(false, "");
  } catch (err) {
    setBusy(false, `Error: ${err.message}`);
  }
}

function selectDate(dateStr) {
  selectedDate = dateStr;
  calendarView = { year: Number(dateStr.slice(0, 4)), month: Number(dateStr.slice(5, 7)) - 1 };
  closeCalendar();
  updateDateLabel();
  renderCalendar();
  loadEntry(dateStr);
}

async function correctEntry() {
  const text = draftInput.value.trim();
  if (!text) return;

  setBusy(true, "Correcting…");
  try {
    const res = await fetch("/api/diary/correct", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, date: selectedDate }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `Server error (${res.status})`);

    correctedText.textContent = data.corrected;
    resultSection.hidden = false;

    explanationText.textContent = data.explanation;
    explanationSection.hidden = !data.explanation;

    savedDates.add(selectedDate);
    renderCalendar();

    setBusy(false, "");
  } catch (err) {
    setBusy(false, `Error: ${err.message}`);
  }
}

function clearEntry() {
  draftInput.value = "";
  resultSection.hidden = true;
  explanationSection.hidden = true;
  setBusy(false, "");
  draftInput.focus();
}

correctBtn.addEventListener("click", correctEntry);
clearBtn.addEventListener("click", clearEntry);

renderWeekdays();
updateDateLabel();
renderCalendar();
fetchDates();
loadEntry(selectedDate);
