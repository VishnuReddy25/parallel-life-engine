const timelineEl = document.getElementById("timeline");
const logEl = document.getElementById("status-log");
const navEl = document.getElementById("decade-nav");
const introEl = document.getElementById("artifact-intro");
const titleEl = document.getElementById("artifact-title");
const summaryEl = document.getElementById("artifact-summary");
const transcriptionEl = document.getElementById("transcription-note");
const traceEl = document.getElementById("trace-note");
const notesEl = document.getElementById("timeline-notes");
const errorListEl = document.getElementById("error-list");
const savedRunsEl = document.getElementById("saved-runs");
const scenarioListEl = document.getElementById("scenario-list");
const runtimeBadgesEl = document.getElementById("runtime-badges");
const runtimeValidationEl = document.getElementById("runtime-validation");
const photoInput = document.getElementById("photo-input");
const recordButton = document.getElementById("record-button");
const recordingStatusEl = document.getElementById("recording-status");
const audioPreviewEl = document.getElementById("audio-preview");
const forkInput = document.getElementById("fork-input");
const generateButton = document.getElementById("generate-button");
const exportButton = document.getElementById("export-button");

const renderedDecades = new Map();
let latestExportHtml = "";
let mediaRecorder = null;
let recordedChunks = [];
let recordedBlob = null;
let isRecording = false;

const starterScenarios = [
  {
    title: "Tokyo Photographer",
    fork: "What if I had moved to Tokyo at 22 and stayed long enough to become a photographer?",
    blurb: "A glamorous, lonely, city-lit life with visual texture and reinvention.",
  },
  {
    title: "Band in Sao Paulo",
    fork: "What if I had joined an indie band in Sao Paulo instead of taking the safe office job?",
    blurb: "A louder alternate life with touring, collapse, friendship, and regret.",
  },
  {
    title: "Marine Biologist",
    fork: "What if I had accepted the marine biology fellowship and spent my life near the sea?",
    blurb: "A slower, windswept memoir full of distance, discipline, and wonder.",
  },
];

function setLog(text) {
  logEl.textContent = text || "Listening for the next clue.";
}

function ensureNav(decades, readyDecades, readyPortraits) {
  navEl.innerHTML = "";
  decades.forEach((decade) => {
    const pill = document.createElement("span");
    const isReady = readyDecades.includes(decade) || readyPortraits.includes(decade);
    pill.className = `decade-pill${isReady ? " ready" : ""}`;
    pill.textContent = decade;
    navEl.appendChild(pill);
  });
}

function createCard(decade) {
  const card = document.createElement("article");
  card.className = "decade-card";
  card.dataset.decade = decade;
  card.innerHTML = `
    <div class="portrait-frame">
      <div class="portrait-placeholder">Portrait still developing in the darkroom.</div>
    </div>
    <div class="decade-copy">
      <h2>${decade}</h2>
      <div class="decade-meta"></div>
      <p></p>
      <div class="memory-strip"></div>
    </div>
  `;
  timelineEl.appendChild(card);
  renderedDecades.set(decade, card);
  return card;
}

function updateCard(decade, details) {
  const card = renderedDecades.get(decade) || createCard(decade);
  const meta = card.querySelector(".decade-meta");
  const paragraph = card.querySelector("p");
  const frame = card.querySelector(".portrait-frame");
  const strip = card.querySelector(".memory-strip");

  meta.innerHTML = "";
  [details.key_event, details.location, details.emotion]
    .filter(Boolean)
    .forEach((value) => {
      const span = document.createElement("span");
      span.textContent = value;
      meta.appendChild(span);
    });

  paragraph.textContent = details.narrative || "";

  strip.innerHTML = "";
  [
    ["Relationship", details.relationship],
    ["Body Memory", details.physical_memory],
    ["Aftertaste", details.aftertaste],
  ]
    .filter(([, value]) => Boolean(value))
    .forEach(([label, value]) => {
      const chip = document.createElement("div");
      chip.className = "memory-chip";
      chip.innerHTML = `<strong>${label}</strong><span>${value}</span>`;
      strip.appendChild(chip);
    });

  if (details.portrait_b64) {
    frame.innerHTML = "";
    const image = document.createElement("img");
    image.alt = `${decade} portrait`;
    image.src = `data:image/jpeg;base64,${details.portrait_b64}`;
    frame.appendChild(image);
  }
}

function updateIntro(title, summary) {
  if (!title && !summary) {
    introEl.hidden = true;
    transcriptionEl.textContent = "";
    traceEl.textContent = "";
    return;
  }
  introEl.hidden = false;
  titleEl.textContent = title || "The Life Where I Turned";
  summaryEl.textContent = summary || "";
}

function updateTranscriptionNote(transcription, language) {
  if (!transcription) {
    transcriptionEl.textContent = "";
    return;
  }
  const langText = language ? ` (${language})` : "";
  transcriptionEl.textContent = `Recovered fork${langText}: ${transcription}`;
}

function updateTraceNote(traceId, tracePath) {
  if (!traceId) {
    traceEl.textContent = "";
    return;
  }
  traceEl.textContent = `Trace ${traceId} saved to ${tracePath || "local artifacts"}.`;
}

function updateTimelineNotes(items) {
  notesEl.innerHTML = "";
  items.slice(0, 5).forEach((item) => {
    const note = document.createElement("div");
    note.className = "timeline-note";
    note.innerHTML = `<strong>${item.decade || "Memory"}</strong><span>${item.event || item.location || ""}</span>`;
    notesEl.appendChild(note);
  });
}

function updateErrors(errors, portraitFailures) {
  errorListEl.innerHTML = "";
  const combined = [...(errors || []), ...(portraitFailures || [])];
  if (combined.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No visible fractures yet.";
    errorListEl.appendChild(li);
    return;
  }

  combined.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    errorListEl.appendChild(li);
  });
}

function renderSavedRuns(runs) {
  savedRunsEl.innerHTML = "";
  if (!Array.isArray(runs) || runs.length === 0) {
    const empty = document.createElement("p");
    empty.className = "artifact-summary";
    empty.textContent = "No recovered lives on the shelf yet. Generate the first one.";
    savedRunsEl.appendChild(empty);
    return;
  }

  runs.forEach((run) => {
    const card = document.createElement("a");
    card.className = "saved-run-card";
    card.href = run.replay_path;
    card.innerHTML = `
      <h3>${run.life_title}</h3>
      <p>${run.life_summary}</p>
      <div class="saved-run-meta">
        <span>${run.decade_count || 0} decades</span>
        <span>${run.timeline_count || 0} timeline notes</span>
      </div>
    `;
    savedRunsEl.appendChild(card);
  });
}

function renderStarterScenarios() {
  scenarioListEl.innerHTML = "";
  starterScenarios.forEach((scenario) => {
    const card = document.createElement("article");
    card.className = "scenario-card";
    card.innerHTML = `
      <h3>${scenario.title}</h3>
      <p>${scenario.blurb}</p>
      <button type="button">Use This Fork</button>
    `;
    card.querySelector("button").addEventListener("click", () => {
      forkInput.value = scenario.fork;
      setLog(`Loaded starter fork: ${scenario.title}.`);
      forkInput.focus();
    });
    scenarioListEl.appendChild(card);
  });
}

function renderRuntimeInfo(runtime) {
  runtimeBadgesEl.innerHTML = "";
  const entries = [
    ["Models", runtime?.model_provider ?? "unknown"],
    ["Demo Mode", runtime?.demo_mode ? "on" : "off"],
    ["Traces", runtime?.traces_provider ?? "unknown"],
  ];
  entries.forEach(([label, value]) => {
    const badge = document.createElement("div");
    badge.className = "runtime-badge";
    badge.innerHTML = `<strong>${label}</strong>${value}`;
    runtimeBadgesEl.appendChild(badge);
  });
}

function renderRuntimeValidation(validation) {
  runtimeValidationEl.classList.remove("ok", "issue");
  if (!validation || validation.ok) {
    runtimeValidationEl.classList.add("ok");
    runtimeValidationEl.textContent = "Runtime validation passed for the currently selected providers.";
    return;
  }

  runtimeValidationEl.classList.add("issue");
  runtimeValidationEl.textContent = validation.issues.join(" ");
}

function renderSnapshot(payload) {
  const decades = payload.decades || ["20s", "30s", "40s", "50s", "60s"];
  setLog(payload.log);
  updateIntro(payload.life_title, payload.life_summary);
  updateTranscriptionNote(payload.transcription, payload.language_detected);
  updateTraceNote(payload.trace_id, payload.trace_path);
  ensureNav(decades, payload.narrative_ready || [], payload.portraits_ready || []);
  updateTimelineNotes(payload.timeline || []);
  updateErrors(payload.errors, payload.portrait_failures);

  Object.entries(payload.life_arc || {}).forEach(([decade, details]) => {
    updateCard(decade, {
      ...details,
      portrait_b64: (payload.portraits || {})[decade] || "",
    });
  });

  if (payload.export_ready && payload.scrapbook_html) {
    latestExportHtml = payload.scrapbook_html;
    exportButton.hidden = false;
  }
}

async function generate() {
  if (!forkInput.value.trim() && !recordedBlob) {
    setLog("Write or record a life fork first so the machine has somewhere to go.");
    return;
  }

  timelineEl.innerHTML = "";
  navEl.innerHTML = "";
  renderedDecades.clear();
  exportButton.hidden = true;
  latestExportHtml = "";
  setLog("Opening the first impossible door...");
  updateIntro("", "");
  notesEl.innerHTML = "";
  errorListEl.innerHTML = "";
  transcriptionEl.textContent = "";
  traceEl.textContent = "";

  const formData = new FormData();
  if (photoInput.files[0]) {
    formData.append("photo", photoInput.files[0]);
  }
  if (forkInput.value.trim()) {
    formData.append("fork_text", forkInput.value.trim());
  }
  if (recordedBlob) {
    formData.append("audio", recordedBlob, "fork.webm");
  }

  const response = await fetch("/run", { method: "POST", body: formData });
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n");
    buffer = chunks.pop() || "";

    chunks.filter(Boolean).forEach((line) => {
      renderSnapshot(JSON.parse(line));
    });
  }
}

async function toggleRecording() {
  if (isRecording && mediaRecorder) {
    mediaRecorder.stop();
    return;
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  recordedChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      recordedChunks.push(event.data);
    }
  };
  mediaRecorder.onstop = () => {
    recordedBlob = new Blob(recordedChunks, { type: "audio/webm" });
    audioPreviewEl.src = URL.createObjectURL(recordedBlob);
    audioPreviewEl.hidden = false;
    recordingStatusEl.textContent = "Voice fork captured and ready to send.";
    recordingStatusEl.classList.remove("recording");
    recordButton.textContent = "Record Again";
    isRecording = false;
    stream.getTracks().forEach((track) => track.stop());
  };

  mediaRecorder.start();
  isRecording = true;
  recordingStatusEl.textContent = "Recording... click again to stop.";
  recordingStatusEl.classList.add("recording");
  recordButton.textContent = "Stop Recording";
}

generateButton.addEventListener("click", () => {
  generate().catch((error) => {
    console.error(error);
    setLog("The scrapbook jammed. Try another fork in the road.");
  });
});

recordButton.addEventListener("click", () => {
  toggleRecording().catch((error) => {
    console.error(error);
    recordingStatusEl.textContent = "Microphone access failed in this browser.";
    recordingStatusEl.classList.remove("recording");
  });
});

exportButton.addEventListener("click", () => {
  if (!latestExportHtml) {
    return;
  }

  const blob = new Blob([latestExportHtml], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "parallel-life-keepsake.html";
  link.click();
  URL.revokeObjectURL(url);
});

const savedScrapbook = window.__SCRAPBOOK_TEMPLATE__;
renderRuntimeInfo(window.__RUNTIME_INFO__);
renderRuntimeValidation(window.__APP_META__?.runtime_validation);
renderStarterScenarios();
renderSavedRuns(window.__SAVED_RUNS__);
if (savedScrapbook && Array.isArray(savedScrapbook.pages) && savedScrapbook.pages.length > 0) {
  renderSnapshot({
    log: "A saved scrapbook is ready to browse.",
    life_title: savedScrapbook.title,
    life_summary: savedScrapbook.summary,
    transcription: savedScrapbook.transcription,
    language_detected: savedScrapbook.language_detected,
    trace_id: savedScrapbook.trace_id,
    trace_path: savedScrapbook.trace_path,
    decades: savedScrapbook.pages.map((page) => page.decade),
    life_arc: Object.fromEntries(
      savedScrapbook.pages.map((page) => [page.decade, page]),
    ),
    portraits: Object.fromEntries(
      savedScrapbook.pages.map((page) => [page.decade, page.portrait_b64 || ""]),
    ),
    timeline: savedScrapbook.timeline || [],
    portrait_failures: savedScrapbook.portrait_failures || [],
    narrative_ready: savedScrapbook.pages.map((page) => page.decade),
    portraits_ready: savedScrapbook.pages
      .filter((page) => page.portrait_b64)
      .map((page) => page.decade),
  });
}
