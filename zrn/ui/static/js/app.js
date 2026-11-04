/**
 * Project ZRN — Kiosk Frontend
 * ByteBell Software
 */

// ── Icons (SVG instead of emoji — no emoji font on the kiosk Pi) ───────────
const ICON_CARD = `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="9" x2="22" y2="9"/><line x1="5" y1="14" x2="10" y2="14"/></svg>`;
const ICON_CHECK = `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="10"/><path d="M7.5 12.5l3 3 6-6"/></svg>`;
const ICON_WARN = `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M12 3 2 20h20L12 3z"/><line x1="12" y1="9" x2="12" y2="14"/><circle cx="12" cy="17" r="0.5" fill="currentColor"/></svg>`;

// ── State ──────────────────────────────────────────────────────────────────
let numpadInput = '';
let nfcPollInterval = null;
const AUTO_RESET_MS = 30_000; // Back to the home screen after 30s
let resetTimer = null;

// ── Screen switching ─────────────────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function showHome() {
  clearReset();
  stopNfcPoll();
  numpadInput = '';
  document.getElementById('numpad-display').textContent = '_';
  document.getElementById('lesson-list').innerHTML = `
    <div class="placeholder-msg">
      <span class="placeholder-icon">${ICON_CARD}</span>
      <p>Leg je druppel op de scanner</p>
      <p class="keyboard-hint">of typ je leerlingnummer op het toetsenbord</p>
    </div>`;
  document.getElementById('home-name').textContent = 'Scan je druppel';
  document.getElementById('home-sub').textContent = 'of typ je leerlingnummer';
  showScreen('screen-home');
  startNfcScan();
}

function showNumpad() {
  clearReset();
  stopNfcPoll();
  numpadInput = '';
  document.getElementById('numpad-display').textContent = '_';
  showScreen('screen-numpad');
}

// ── NumPad ───────────────────────────────────────────────────────────────────
function npPress(digit) {
  if (numpadInput.length >= 12) return;
  numpadInput += digit;
  document.getElementById('numpad-display').textContent = numpadInput || '_';
}

function npBack() {
  numpadInput = numpadInput.slice(0, -1);
  document.getElementById('numpad-display').textContent = numpadInput || '_';
}

function npConfirm() {
  if (numpadInput.length < 4) return;
  loadRooster(numpadInput);
}

// ── Loading the schedule ─────────────────────────────────────────────────────
async function loadRooster(leerlingnummer) {
  showScreen('screen-rooster');
  document.getElementById('r-naam-klas').textContent = 'Laden…';
  document.getElementById('r-lnr').textContent = leerlingnummer;
  document.getElementById('r-lessons').innerHTML = '<div class="spinner"></div>';

  try {
    const resp = await fetch(`/api/rooster/${leerlingnummer}`);
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);

    document.getElementById('r-naam-klas').textContent =
      [data.naam, data.klas].filter(Boolean).join(' ') || leerlingnummer;
    document.getElementById('r-lnr').textContent = data.leerlingnummer;

    const list = document.getElementById('r-lessons');
    if (!data.lessen || data.lessen.length === 0) {
      list.innerHTML = `
        <div class="placeholder-msg">
          <span class="placeholder-icon">${ICON_CHECK}</span>
          <p>Geen lessen vandaag</p>
        </div>`;
    } else {
      list.innerHTML = data.lessen.map(les => `
        <div class="lesson-btn ${les.geannuleerd ? 'geannuleerd' : ''}">
          <div>
            <div class="lesson-label">${les.vak}</div>
            <div class="lesson-vak">${les.lokaal} · ${les.docent}</div>
          </div>
          <div class="lesson-time">${les.start}<br>${les.einde}</div>
        </div>
      `).join('');
    }

    scheduleReset();

  } catch (err) {
    document.getElementById('r-naam-klas').textContent = 'Fout';
    document.getElementById('r-lessons').innerHTML = `
      <div class="placeholder-msg">
        <span class="placeholder-icon">${ICON_WARN}</span>
        <p>${err.message}</p>
      </div>`;
    setTimeout(showHome, 4000);
  }
}

// ── NFC polling ────────────────────────────────────────────────────────────
async function startNfcScan() {
  try { await fetch('/api/nfc/scan', { method: 'POST' }); } catch {}
  nfcPollInterval = setInterval(async () => {
    try {
      const resp = await fetch('/api/nfc/status');
      const data = await resp.json();
      if (data.leerlingnummer) {
        stopNfcPoll();
        loadRooster(data.leerlingnummer);
      } else if (data.uid && !data.leerlingnummer) {
        // UID found but not registered -> enrollment flow
        stopNfcPoll();
        showEnrollmentPrompt(data.uid);
      }
    } catch {}
  }, 800);
}

function stopNfcPoll() {
  if (nfcPollInterval) { clearInterval(nfcPollInterval); nfcPollInterval = null; }
}

// ── Enrollment (new card) ─────────────────────────────────────────────────────
let enrollUid = null;
let enrollInput = '';

function showEnrollmentPrompt(uid) {
  enrollUid = uid;
  enrollInput = '';
  document.getElementById('enroll-uid').textContent = uid;
  document.getElementById('enroll-display').textContent = '_';
  document.getElementById('enrollment-modal').hidden = false;
}

function enrollPress(digit) {
  if (enrollInput.length >= 12) return;
  enrollInput += digit;
  document.getElementById('enroll-display').textContent = enrollInput || '_';
}

function enrollBack() {
  enrollInput = enrollInput.slice(0, -1);
  document.getElementById('enroll-display').textContent = enrollInput || '_';
}

function enrollConfirm() {
  if (enrollInput.length < 4) return;
  const uid = enrollUid;
  const lnr = enrollInput;
  document.getElementById('enrollment-modal').hidden = true;
  fetch('/api/enrollment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ uid, leerlingnummer: lnr }),
  }).then(() => loadRooster(lnr));
}

function cancelEnrollment() {
  document.getElementById('enrollment-modal').hidden = true;
  showHome();
}

// ── Auto-reset ───────────────────────────────────────────────────────────────
function scheduleReset() {
  clearReset();
  resetTimer = setTimeout(showHome, AUTO_RESET_MS);
}

function clearReset() {
  if (resetTimer) { clearTimeout(resetTimer); resetTimer = null; }
}

// ── Keyboard support ─────────────────────────────────────────────────────────
// The final product has no mouse and no touchscreen — the kiosk is operated
// entirely with a physical keyboard/NumPad (digits, Backspace, Enter, Esc).
document.addEventListener('keydown', e => {
  const enrolling = !document.getElementById('enrollment-modal').hidden;

  if (enrolling) {
    if (e.key >= '0' && e.key <= '9') enrollPress(e.key);
    else if (e.key === 'Backspace') enrollBack();
    else if (e.key === 'Enter') enrollConfirm();
    else if (e.key === 'Escape') cancelEnrollment();
    return;
  }

  const screen = document.querySelector('.screen.active').id;

  if (screen === 'screen-home') {
    if (e.key >= '0' && e.key <= '9') {
      // Typing a digit directly on the home screen immediately opens the numpad
      showNumpad();
      npPress(e.key);
    }
  } else if (screen === 'screen-numpad') {
    if (e.key >= '0' && e.key <= '9') npPress(e.key);
    else if (e.key === 'Backspace') npBack();
    else if (e.key === 'Enter') npConfirm();
    else if (e.key === 'Escape') showHome();
  } else if (screen === 'screen-rooster') {
    if (e.key === 'Escape') showHome();
  }
});

// ── Startup ──────────────────────────────────────────────────────────────────
window.addEventListener('load', showHome);
