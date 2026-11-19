/* =========================================================
   ReelMate – app logic
   Everything runs in the browser. The file is split into
   sections that match the 6 steps on the page.
   ========================================================= */

// ---------- Small helpers ----------
const $ = (sel) => document.querySelector(sel);
const clamp = (n, min, max) => Math.min(max, Math.max(min, n));

function formatTime(sec) {
  if (!isFinite(sec)) sec = 0;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

function toast(message, ms = 2800) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove('show'), ms);
}

// Wait for an event once (with a safety timeout so nothing hangs forever)
function once(target, event, timeoutMs = 4000) {
  return new Promise((resolve) => {
    const done = () => { clearTimeout(timer); target.removeEventListener(event, done); resolve(); };
    const timer = setTimeout(done, timeoutMs);
    target.addEventListener(event, done);
  });
}

// ---------- App state: everything the editor needs to remember ----------
const state = {
  url: null,          // temporary link to the uploaded file
  fileName: '',
  duration: 0,
  width: 0,
  height: 0,
  format: 'fill',     // 'fill' | 'blur' | 'bars'
  cropX: 0.5,         // 0 = left, 0.5 = center, 1 = right
  trimStart: 0,
  trimEnd: 0,
  captions: [],       // [{ start, end, text }]
  subStyle: 'outline',
  subSize: 'm',
  subPos: 'bottom',
  showSubs: true,
  exporting: false,
};

const video = $('#video');
const preview = $('#preview');
const pctx = preview.getContext('2d');

// =========================================================
//  STEP NAVIGATION (the pills at the top)
// =========================================================
const pills = [...document.querySelectorAll('.step-pill')];

pills.forEach((pill) => {
  pill.addEventListener('click', () => {
    document.getElementById(pill.dataset.target).scrollIntoView({ behavior: 'smooth' });
  });
});

function unlockSteps() {
  document.querySelectorAll('.card.locked').forEach((c) => c.classList.remove('locked'));
  pills.forEach((p) => (p.disabled = false));
}

function markDone(stepId) {
  const pill = pills.find((p) => p.dataset.target === stepId);
  if (pill) pill.classList.add('done');
}

// Highlight the step you're currently looking at
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      pills.forEach((p) => p.classList.toggle('active', p.dataset.target === entry.target.id));
    }
  });
}, { rootMargin: '-45% 0px -50% 0px' });
document.querySelectorAll('main .card').forEach((card) => observer.observe(card));

// =========================================================
//  STEP 1 – UPLOAD
// =========================================================
const fileInput = $('#fileInput');
const dropzone = $('#dropzone');

fileInput.addEventListener('change', () => loadFile(fileInput.files[0]));

['dragenter', 'dragover'].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add('drag'); }));
['dragleave', 'drop'].forEach((ev) =>
  dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove('drag'); }));
dropzone.addEventListener('drop', (e) => loadFile(e.dataTransfer.files[0]));

function loadFile(file) {
  if (!file) return;
  if (!file.type.startsWith('video/') && !/\.(mp4|mov|webm|m4v|mkv)$/i.test(file.name)) {
    toast('That is not a video file. Please choose an MP4 or MOV.');
    return;
  }
  if (state.url) URL.revokeObjectURL(state.url);
  state.url = URL.createObjectURL(file);
  state.fileName = file.name;
  state.fileSize = file.size;
  state.captions = [];
  renderCaptions();
  $('#suggestions').innerHTML = '';
  $('#result').classList.add('hidden');
  video.src = state.url;
  video.load();
}

video.addEventListener('loadedmetadata', async () => {
  // Some recorded videos report "Infinity" as duration – this trick fixes it.
  if (!isFinite(video.duration)) {
    video.currentTime = 1e9;
    await once(video, 'durationchange', 3000);
    video.currentTime = 0;
  }
  state.duration = video.duration || 0;
  state.width = video.videoWidth;
  state.height = video.videoHeight;
  state.trimStart = 0;
  state.trimEnd = +state.duration.toFixed(2);

  // Pick a sensible default format: vertical videos fill, horizontal ones get blur.
  const ratio = state.width / state.height;
  setFormat(ratio > 0.8 ? 'blur' : 'fill');

  $('#trimStart').value = 0;
  $('#trimEnd').value = state.trimEnd;
  $('#seek').max = state.duration;
  updateTrimInfo();
  showFileInfo();
  unlockSteps();
  markDone('step-upload');
  toast('Video loaded! Scroll down to preview it 👇');
  setTimeout(() => $('#step-preview').scrollIntoView({ behavior: 'smooth' }), 400);
});

video.addEventListener('error', () => {
  toast('Your browser cannot play this video format. Try an MP4 (H.264) file.', 5000);
});

function showFileInfo() {
  const mb = (state.fileSize / 1024 / 1024).toFixed(1);
  const ratio = state.width / state.height;
  const shape = ratio < 0.7 ? 'Vertical ✓' : ratio > 1.3 ? 'Horizontal' : 'Square-ish';
  const info = $('#fileInfo');
  info.innerHTML = `
    <div class="wide"><small>File</small><b></b></div>
    <div><small>Length</small><b>${formatTime(state.duration)}</b></div>
    <div><small>Size</small><b>${mb} MB</b></div>
    <div><small>Resolution</small><b>${state.width} × ${state.height}</b></div>
    <div><small>Shape</small><b>${shape}</b></div>`;
  info.querySelector('.wide b').textContent = state.fileName; // safe: file names are shown as plain text
  info.classList.remove('hidden');
}

// =========================================================
//  DRAWING – turns one video frame into a 9:16 Reel frame.
//  Used by both the preview (step 2) and the export (step 6).
// =========================================================
const blurCanvas = document.createElement('canvas');
blurCanvas.width = 27;   // tiny canvas: scaling it up creates a soft blur
blurCanvas.height = 48;
const bctx = blurCanvas.getContext('2d');
const canFilter = typeof pctx.filter === 'string';

function drawFrame(ctx, W, H, t) {
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, W, H);
  if (!state.width || video.readyState < 2) return;

  const vw = state.width;
  const vh = state.height;

  if (state.format === 'fill') {
    // Scale until the frame is covered, then slide left/right using cropX.
    const scale = Math.max(W / vw, H / vh);
    const dw = vw * scale, dh = vh * scale;
    ctx.drawImage(video, (W - dw) * state.cropX, (H - dh) / 2, dw, dh);
  } else {
    if (state.format === 'blur') {
      const s = Math.max(blurCanvas.width / vw, blurCanvas.height / vh);
      bctx.drawImage(video, (blurCanvas.width - vw * s) / 2, (blurCanvas.height - vh * s) / 2, vw * s, vh * s);
      ctx.save();
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';
      if (canFilter) ctx.filter = `blur(${Math.round(W / 40)}px)`;
      ctx.drawImage(blurCanvas, -W * 0.05, -H * 0.05, W * 1.1, H * 1.1);
      ctx.restore();
      ctx.fillStyle = 'rgba(0,0,0,0.3)';
      ctx.fillRect(0, 0, W, H);
    }
    // Scale until the whole video fits inside, then center it.
    const scale = Math.min(W / vw, H / vh);
    const dw = vw * scale, dh = vh * scale;
    ctx.drawImage(video, (W - dw) / 2, (H - dh) / 2, dw, dh);
  }

  if (state.showSubs || state.exporting) drawCaption(ctx, W, H, t);
}

function wrapText(ctx, text, maxWidth) {
  const words = text.split(/\s+/);
  const lines = [];
  let line = '';
  for (const word of words) {
    const test = line ? `${line} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function drawCaption(ctx, W, H, t) {
  const cap = state.captions.find((c) => t >= c.start && t < c.end);
  if (!cap || !cap.text.trim()) return;

  const size = H * { s: 0.034, m: 0.045, l: 0.058 }[state.subSize];
  ctx.save();
  ctx.font = `800 ${size}px system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const lines = wrapText(ctx, cap.text.trim(), W * 0.8);
  const lineH = size * 1.25;
  // "bottom" sits at 72% height so Instagram's buttons don't cover it.
  const centerY = H * { top: 0.2, middle: 0.5, bottom: 0.72 }[state.subPos];
  let y = centerY - ((lines.length - 1) * lineH) / 2;

  if (state.subStyle === 'box') {
    const maxW = Math.max(...lines.map((l) => ctx.measureText(l).width));
    const padX = size * 0.5, padY = size * 0.3;
    const boxH = lines.length * lineH + padY * 2;
    ctx.fillStyle = 'rgba(0,0,0,0.72)';
    roundRect(ctx, W / 2 - maxW / 2 - padX, y - lineH / 2 - padY, maxW + padX * 2, boxH, size * 0.35);
    ctx.fill();
  }

  for (const line of lines) {
    if (state.subStyle !== 'box') {
      ctx.lineWidth = size * 0.2;
      ctx.lineJoin = 'round';
      ctx.strokeStyle = '#000';
      ctx.strokeText(line, W / 2, y);
    }
    ctx.fillStyle = state.subStyle === 'yellow' ? '#ffd60a' : '#fff';
    ctx.fillText(line, W / 2, y);
    y += lineH;
  }
  ctx.restore();
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

// =========================================================
//  STEP 2 – PREVIEW (player controls + live drawing loop)
// =========================================================
const playBtn = $('#playBtn');
const seek = $('#seek');

// Audio routing: lets us hear the video AND record its sound during export.
let audioCtx = null, speakerGain = null, recordDest = null;
function setupAudio() {
  if (audioCtx) { audioCtx.resume(); return; }
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioCtx.createMediaElementSource(video);
    speakerGain = audioCtx.createGain();
    recordDest = audioCtx.createMediaStreamDestination();
    source.connect(speakerGain).connect(audioCtx.destination); // → your speakers
    source.connect(recordDest);                                // → the exporter
  } catch (err) {
    console.warn('Audio setup failed, export will be silent', err);
    audioCtx = null;
  }
}

playBtn.addEventListener('click', () => {
  setupAudio();
  if (video.paused) {
    if (video.currentTime < state.trimStart || video.currentTime >= state.trimEnd - 0.05) {
      video.currentTime = state.trimStart;
    }
    video.play();
    markDone('step-preview');
  } else {
    video.pause();
  }
});
video.addEventListener('play', () => { playBtn.textContent = '❚❚'; playBtn.setAttribute('aria-label', 'Pause'); });
video.addEventListener('pause', () => { playBtn.textContent = '▶'; playBtn.setAttribute('aria-label', 'Play'); });

seek.addEventListener('input', () => { video.currentTime = +seek.value; });

$('#showSubs').addEventListener('change', (e) => { state.showSubs = e.target.checked; });
$('#showSafe').addEventListener('change', (e) => { $('#safeZone').hidden = !e.target.checked; });

let lastHighlighted = -1;
function renderLoop() {
  if (!state.exporting) {
    // Stop at the trim end while previewing
    if (!video.paused && video.currentTime >= state.trimEnd) {
      video.pause();
      video.currentTime = state.trimStart;
    }
    drawFrame(pctx, preview.width, preview.height, video.currentTime);
    if (document.activeElement !== seek) seek.value = video.currentTime;
    $('#timeLabel').textContent = `${formatTime(video.currentTime)} / ${formatTime(state.duration)}`;

    // Highlight the caption that is on screen right now
    const idx = state.captions.findIndex((c) => video.currentTime >= c.start && video.currentTime < c.end);
    if (idx !== lastHighlighted) {
      lastHighlighted = idx;
      document.querySelectorAll('.caption').forEach((el, i) => el.classList.toggle('current', i === idx));
    }
  }
  requestAnimationFrame(renderLoop);
}
requestAnimationFrame(renderLoop);

// =========================================================
//  STEP 3 – EDITING SUGGESTIONS
//  Samples frames from the video and measures brightness,
//  contrast and how much the picture changes (pacing).
// =========================================================
$('#analyzeBtn').addEventListener('click', analyzeVideo);

async function analyzeVideo() {
  const btn = $('#analyzeBtn');
  const bar = $('#analyzeProgress');
  btn.disabled = true;
  btn.textContent = '🔍 Analyzing…';
  bar.classList.remove('hidden');
  $('#suggestions').innerHTML = '';

  // Use a second, silent copy of the video so the preview isn't disturbed
  const probe = document.createElement('video');
  probe.muted = true;
  probe.playsInline = true;
  probe.preload = 'auto';
  probe.src = state.url;
  await once(probe, 'loadeddata', 6000);

  const cw = 64, ch = Math.max(1, Math.round((64 * state.height) / state.width));
  const c = document.createElement('canvas');
  c.width = cw; c.height = ch;
  const cx = c.getContext('2d', { willReadFrequently: true });

  const samples = clamp(Math.round(state.duration * 2), 8, 40);
  const frames = [];
  let prevLuma = null;

  for (let i = 0; i < samples; i++) {
    const t = ((i + 0.5) * state.duration) / samples;
    probe.currentTime = t;
    await once(probe, 'seeked', 3000);
    cx.drawImage(probe, 0, 0, cw, ch);
    const px = cx.getImageData(0, 0, cw, ch).data;

    const luma = new Float32Array(cw * ch);
    let sum = 0;
    for (let p = 0, j = 0; p < px.length; p += 4, j++) {
      luma[j] = 0.299 * px[p] + 0.587 * px[p + 1] + 0.114 * px[p + 2];
      sum += luma[j];
    }
    const mean = sum / luma.length;
    let varSum = 0, diff = 0;
    for (let j = 0; j < luma.length; j++) {
      varSum += (luma[j] - mean) ** 2;
      if (prevLuma) diff += Math.abs(luma[j] - prevLuma[j]);
    }
    frames.push({ t, brightness: mean, contrast: Math.sqrt(varSum / luma.length), change: prevLuma ? diff / luma.length : 0 });
    prevLuma = luma;
    bar.firstElementChild.style.width = `${((i + 1) / samples) * 100}%`;
  }
  probe.removeAttribute('src');
  probe.load();

  renderSuggestions(buildSuggestions(frames));
  btn.disabled = false;
  btn.textContent = '🔄 Analyze again';
  setTimeout(() => bar.classList.add('hidden'), 600);
  markDone('step-suggest');
}

function buildSuggestions(frames) {
  const list = [];
  const d = state.duration;
  const avg = (key) => frames.reduce((s, f) => s + f[key], 0) / frames.length;
  const brightness = avg('brightness');
  const contrast = avg('contrast');
  const ratio = state.width / state.height;

  // 1. Length
  if (d > 90) {
    list.push({ level: 'warn', icon: '⏱', title: 'Too long for a Reel',
      text: `Your video is ${formatTime(d)}. Short Reels (15–30 s) keep people watching to the end. Keep only the best part.`,
      action: { label: 'Trim to 30 s', run: () => setTrim(state.trimStart, state.trimStart + 30) } });
  } else if (d > 35) {
    list.push({ level: 'tip', icon: '⏱', title: 'Consider making it shorter',
      text: `${formatTime(d)} is fine, but Reels under 30 seconds usually get watched to the end more often.`,
      action: { label: 'Trim to 30 s', run: () => setTrim(state.trimStart, state.trimStart + 30) } });
  } else if (d < 5) {
    list.push({ level: 'tip', icon: '⏱', title: 'Very short clip',
      text: 'Clips under 5 seconds play on loop. That can work, but add text so people know what they are looking at.' });
  } else {
    list.push({ level: 'good', icon: '✅', title: 'Great length', text: `${formatTime(d)} is a good length for a Reel.` });
  }

  // 2. Shape / framing
  if (ratio > 1.3) {
    list.push({ level: 'warn', icon: '📐', title: 'Horizontal video',
      text: 'Reels are vertical. "Fit + blur" shows your whole shot. "Fill & crop" fills the screen but cuts off the sides.',
      action: { label: 'Use Fit + blur', run: () => setFormat('blur') } });
  } else if (ratio > 0.7) {
    list.push({ level: 'tip', icon: '📐', title: 'Square-ish video',
      text: 'Fill the 9:16 frame by cropping, or keep everything visible with a blurred background.',
      action: { label: 'Use Fill & crop', run: () => setFormat('fill') } });
  } else {
    list.push({ level: 'good', icon: '✅', title: 'Already vertical', text: 'Your video is vertical, so it will fill the screen perfectly.' });
  }

  // 3. Resolution
  if (Math.min(state.width, state.height) < 720) {
    list.push({ level: 'warn', icon: '🔎', title: 'Low resolution',
      text: `${state.width}×${state.height} may look soft. Record in 1080p or 4K if you can, or export at 720p.`,
      action: { label: 'Export at 720p', run: () => { $('#quality').value = '720'; toast('Quality set to 720p'); } } });
  }

  // 4. Lighting
  if (brightness < 60) {
    list.push({ level: 'warn', icon: '💡', title: 'Video looks dark',
      text: 'Film facing a window or a lamp. Bright videos get more attention in the feed.' });
  } else if (brightness > 200) {
    list.push({ level: 'warn', icon: '💡', title: 'Video looks overexposed',
      text: 'Some parts may be too bright. Lower exposure on your camera by tapping and dragging down on the screen.' });
  } else {
    list.push({ level: 'good', icon: '✅', title: 'Good lighting', text: 'The brightness looks balanced.' });
  }
  if (contrast < 28) {
    list.push({ level: 'tip', icon: '🎨', title: 'Looks a bit flat',
      text: 'Low contrast. A filter in Instagram (like "Clarendon") or more light from the side adds depth.' });
  }

  // 5. Pacing – how often the picture changes a lot
  const bigChanges = frames.filter((f) => f.change > 28).length;
  const changesPer10s = (bigChanges / d) * 10;
  if (d > 8 && changesPer10s < 1) {
    list.push({ level: 'tip', icon: '✂️', title: 'Slow pacing',
      text: 'The picture barely changes. Add a cut every 2–3 seconds, change the angle, or move the camera to keep viewers watching.' });
  } else if (changesPer10s > 6) {
    list.push({ level: 'good', icon: '⚡', title: 'Fast, energetic pacing', text: 'Lots of movement and cuts. Perfect for Reels.' });
  } else {
    list.push({ level: 'good', icon: '✅', title: 'Good pacing', text: 'Your video has a healthy amount of movement.' });
  }

  // 6. Hook – is the start slow compared to the rest?
  const avgChange = avg('change');
  const intro = frames.filter((f) => f.t < 3 && f.change > 0);
  const introChange = intro.length ? intro.reduce((s, f) => s + f.change, 0) / intro.length : avgChange;
  const firstAction = frames.find((f) => f.t > 1 && f.change > avgChange * 1.2);
  if (d > 8 && introChange < avgChange * 0.5 && firstAction && firstAction.t < d * 0.5) {
    const newStart = +Math.max(0, firstAction.t - 0.5).toFixed(1);
    list.push({ level: 'warn', icon: '🪝', title: 'Slow start: hook viewers faster',
      text: `The first seconds are calm. The action starts around ${newStart}s. Starting there can stop people from scrolling away.`,
      action: { label: `Start at ${newStart}s`, run: () => setTrim(newStart, state.trimEnd) } });
  } else {
    list.push({ level: 'tip', icon: '🪝', title: 'Hook in the first 2 seconds',
      text: 'Show the most exciting moment or put a bold question on screen right away.' });
  }

  // 7. Subtitles
  if (!state.captions.length) {
    list.push({ level: 'tip', icon: '💬', title: 'Add subtitles',
      text: 'Many people watch Reels with the sound off. Subtitles keep them watching.',
      action: { label: 'Go to subtitles', run: () => $('#step-subs').scrollIntoView({ behavior: 'smooth' }) } });
  }

  // 8. Safe zone reminder
  list.push({ level: 'tip', icon: '📱', title: 'Mind the safe zone',
    text: 'Instagram puts the caption, likes and buttons at the bottom and right. Keep faces and text away from those areas.',
    action: { label: 'Show safe zone', run: () => { $('#showSafe').checked = true; $('#safeZone').hidden = false; $('#step-preview').scrollIntoView({ behavior: 'smooth' }); } } });

  return list;
}

function renderSuggestions(list) {
  const ul = $('#suggestions');
  ul.innerHTML = '';
  list.forEach((s, i) => {
    const li = document.createElement('li');
    li.className = `suggestion ${s.level}`;
    li.style.animationDelay = `${i * 60}ms`;
    li.innerHTML = `<div class="icon"></div><div><h3></h3><p></p></div>`;
    li.querySelector('.icon').textContent = s.icon;
    li.querySelector('h3').textContent = s.title;
    li.querySelector('p').textContent = s.text;
    if (s.action) {
      const b = document.createElement('button');
      b.className = 'btn ghost';
      b.textContent = s.action.label;
      b.addEventListener('click', () => { s.action.run(); b.textContent = '✓ Applied'; b.disabled = true; });
      li.querySelector('div:last-child').appendChild(b);
    }
    ul.appendChild(li);
  });
}

// =========================================================
//  STEP 4 – SUBTITLES
// =========================================================
$('#genSubsBtn').addEventListener('click', () => {
  const text = $('#scriptInput').value.trim();
  if (!text) { toast('Type or paste what is said in the video first ✍️'); return; }
  state.captions = makeCaptions(text, state.trimStart, state.trimEnd, +$('#wordsPer').value);
  renderCaptions();
  markDone('step-subs');
  toast(`Created ${state.captions.length} captions. Press play to check the timing.`);
});

// Split the text into short chunks and spread them over the clip,
// giving longer chunks a bit more screen time.
function makeCaptions(text, start, end, wordsPer) {
  const words = text.replace(/\s+/g, ' ').split(' ');
  const chunks = [];
  let current = [];
  for (const w of words) {
    current.push(w);
    if (current.length >= wordsPer || /[.!?,;:]$/.test(w)) {
      chunks.push(current.join(' '));
      current = [];
    }
  }
  if (current.length) chunks.push(current.join(' '));

  const total = Math.max(0.5, end - start);
  const weights = chunks.map((c) => c.length + 4);
  const weightSum = weights.reduce((a, b) => a + b, 0);
  let t = start;
  return chunks.map((chunk, i) => {
    const len = (weights[i] / weightSum) * total;
    const cap = { start: +t.toFixed(2), end: +(t + len).toFixed(2), text: chunk };
    t += len;
    return cap;
  });
}

function renderCaptions() {
  const list = $('#captionList');
  list.innerHTML = '';
  lastHighlighted = -1;
  state.captions.forEach((cap, i) => {
    const row = document.createElement('div');
    row.className = 'caption';
    row.innerHTML = `
      <input type="number" step="0.1" min="0" aria-label="Start time" />
      <input type="number" step="0.1" min="0" aria-label="End time" />
      <button class="mini" title="Play from here" aria-label="Play from here">▶</button>
      <button class="mini" title="Delete" aria-label="Delete caption">✕</button>
      <textarea rows="1" aria-label="Caption text"></textarea>`;
    const [startIn, endIn] = row.querySelectorAll('input');
    const [playB, delB] = row.querySelectorAll('button');
    const textIn = row.querySelector('textarea');
    startIn.value = cap.start;
    endIn.value = cap.end;
    textIn.value = cap.text;
    startIn.addEventListener('change', () => { cap.start = +startIn.value || 0; });
    endIn.addEventListener('change', () => { cap.end = +endIn.value || 0; });
    textIn.addEventListener('input', () => { cap.text = textIn.value; });
    playB.addEventListener('click', () => { setupAudio(); video.currentTime = cap.start; video.play(); });
    delB.addEventListener('click', () => { state.captions.splice(i, 1); renderCaptions(); });
    list.appendChild(row);
  });
  $('#srtBtn').disabled = state.captions.length === 0;
}

$('#addCaptionBtn').addEventListener('click', () => {
  const t = +video.currentTime.toFixed(2);
  state.captions.push({ start: t, end: +Math.min(state.duration, t + 2).toFixed(2), text: 'New caption' });
  state.captions.sort((a, b) => a.start - b.start);
  renderCaptions();
  markDone('step-subs');
});

$('#subStyle').addEventListener('change', (e) => { state.subStyle = e.target.value; });
$('#subSize').addEventListener('change', (e) => { state.subSize = e.target.value; });
$('#subPos').addEventListener('change', (e) => { state.subPos = e.target.value; });

// .srt is the standard subtitle file format (useful for YouTube, CapCut, etc.)
$('#srtBtn').addEventListener('click', () => {
  const stamp = (s) => {
    const ms = Math.round(Math.max(0, s) * 1000);
    const h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60;
    const sec = Math.floor(ms / 1000) % 60, rest = ms % 1000;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')},${String(rest).padStart(3, '0')}`;
  };
  // Times are shifted so they match the trimmed video
  const srt = state.captions
    .filter((c) => c.end > state.trimStart && c.start < state.trimEnd)
    .map((c, i) => `${i + 1}\n${stamp(c.start - state.trimStart)} --> ${stamp(Math.min(c.end, state.trimEnd) - state.trimStart)}\n${c.text}\n`)
    .join('\n');
  downloadBlob(new Blob([srt], { type: 'text/plain' }), baseName() + '.srt');
});

// =========================================================
//  STEP 5 – 9:16 FORMAT & TRIM
// =========================================================
function setFormat(fmt) {
  state.format = fmt;
  document.querySelector(`input[name="format"][value="${fmt}"]`).checked = true;
  $('#cropField').classList.toggle('hidden', fmt !== 'fill');
}

document.querySelectorAll('input[name="format"]').forEach((r) =>
  r.addEventListener('change', () => { setFormat(r.value); markDone('step-format'); }));

$('#cropX').addEventListener('input', (e) => {
  state.cropX = +e.target.value;
  $('#cropLabel').textContent = state.cropX < 0.4 ? 'left' : state.cropX > 0.6 ? 'right' : 'center';
});

function setTrim(start, end) {
  start = clamp(+start || 0, 0, state.duration);
  end = clamp(+end || state.duration, 0, state.duration);
  if (end - start < 0.5) { toast('The clip must be at least 0.5 seconds long'); end = Math.min(state.duration, start + 0.5); }
  state.trimStart = +start.toFixed(2);
  state.trimEnd = +end.toFixed(2);
  $('#trimStart').value = state.trimStart;
  $('#trimEnd').value = state.trimEnd;
  video.currentTime = state.trimStart;
  updateTrimInfo();
  markDone('step-format');
}

function updateTrimInfo() {
  $('#trimInfo').textContent = `Your Reel will be ${(state.trimEnd - state.trimStart).toFixed(1)} seconds long.`;
}

$('#trimStart').addEventListener('change', (e) => setTrim(e.target.value, state.trimEnd));
$('#trimEnd').addEventListener('change', (e) => setTrim(state.trimStart, e.target.value));
$('#setStartBtn').addEventListener('click', () => setTrim(video.currentTime, state.trimEnd));
$('#setEndBtn').addEventListener('click', () => setTrim(state.trimStart, video.currentTime));

// =========================================================
//  STEP 6 – EXPORT
//  Plays the trimmed clip, draws every frame onto a 9:16 canvas
//  and records it (with sound) using the browser's MediaRecorder.
// =========================================================
let recorder = null;
let cancelled = false;

function pickMimeType() {
  const options = [
    'video/mp4;codecs=avc1.42E01E,mp4a.40.2', // MP4 – Instagram's favorite
    'video/mp4;codecs=avc1,mp4a.40.2',
    'video/mp4',
    'video/webm;codecs=vp9,opus',
    'video/webm;codecs=vp8,opus',
    'video/webm',
  ];
  return options.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || '';
}

$('#exportBtn').addEventListener('click', exportVideo);
$('#cancelExportBtn').addEventListener('click', () => { cancelled = true; finishExport(); });

async function exportVideo() {
  if (!window.MediaRecorder || !HTMLCanvasElement.prototype.captureStream) {
    toast('Sorry, this browser cannot export video. Try Chrome or update your phone.', 5000);
    return;
  }
  const [W, H] = $('#quality').value === '1080' ? [1080, 1920] : [720, 1280];
  const canvas = document.createElement('canvas');
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');

  setupAudio();
  const stream = canvas.captureStream(30);
  if (recordDest) recordDest.stream.getAudioTracks().forEach((track) => stream.addTrack(track));

  const mimeType = pickMimeType();
  const chunks = [];
  recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: H >= 1920 ? 8_000_000 : 5_000_000 });
  recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  recorder.onstop = () => {
    if (cancelled) return;
    const type = recorder.mimeType || mimeType || 'video/webm';
    showResult(new Blob(chunks, { type }), type);
  };

  // Get ready: jump to the trim start, mute speakers
  cancelled = false;
  state.exporting = true;
  video.pause();
  video.currentTime = state.trimStart;
  await once(video, 'seeked', 3000);
  if (speakerGain) speakerGain.gain.value = 0;

  $('#exportBtn').disabled = true;
  $('#exportStatus').classList.remove('hidden');
  $('#result').classList.add('hidden');
  $('#exportText').textContent = 'Exporting… keep this screen open.';

  recorder.start(500);
  try {
    await video.play();
  } catch (err) {
    toast('Could not start playback for export. Tap Export again.');
    cancelled = true;
    finishExport();
    return;
  }

  const length = state.trimEnd - state.trimStart;
  const step = () => {
    if (!state.exporting) return;
    const t = video.currentTime;
    drawFrame(ctx, W, H, t);
    drawFrame(pctx, preview.width, preview.height, t); // keep preview alive too
    const pct = clamp(((t - state.trimStart) / length) * 100, 0, 100);
    $('#exportBar').style.width = `${pct}%`;
    $('#exportText').textContent = `Exporting… ${Math.round(pct)}% (keep this screen open)`;
    if (t >= state.trimEnd || video.ended) finishExport();
    else requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function finishExport() {
  if (!state.exporting) return;
  state.exporting = false;
  video.pause();
  if (speakerGain) speakerGain.gain.value = 1;
  if (recorder && recorder.state !== 'inactive') recorder.stop();
  $('#exportBtn').disabled = false;
  $('#exportStatus').classList.add('hidden');
  $('#exportBar').style.width = '0';
  if (cancelled) toast('Export cancelled');
}

function showResult(blob, type) {
  const url = URL.createObjectURL(blob);
  const ext = type.includes('mp4') ? 'mp4' : 'webm';
  $('#resultVideo').src = url;
  const link = $('#downloadLink');
  if (link.dataset.url) URL.revokeObjectURL(link.dataset.url);
  link.href = url;
  link.dataset.url = url;
  link.download = `${baseName()}-reel.${ext}`;
  const mb = (blob.size / 1024 / 1024).toFixed(1);
  const isH264 = /avc1|h264/i.test(type) || /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
  const convertTip = 'If Instagram refuses the file, convert it to MP4 (H.264) with a free tool like CloudConvert, or export from a recent Chrome or Safari.';
  $('#resultNote').textContent = ext === 'mp4' && isH264
    ? `Done! ${mb} MB MP4, ready to upload to Instagram.`
    : ext === 'mp4'
      ? `Done! ${mb} MB MP4. ${convertTip}`
      : `Done! Saved as WebM (${mb} MB) because this browser can't make MP4. ${convertTip}`;
  $('#result').classList.remove('hidden');
  markDone('step-export');
  toast('🎉 Your Reel is ready!');
  $('#result').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// ---------- Shared utilities ----------
function baseName() {
  return (state.fileName || 'video').replace(/\.[^.]+$/, '');
}

function downloadBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
