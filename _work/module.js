// =============================================================
//  Irish Grammar - module app logic (ABAIR TTS)
//  Expects LESSON (object) defined before this file:
//    LESSON.kind, LESSON.study (HTML), LESSON.drill[], LESSON.fill[], LESSON.quiz[]
// =============================================================
const ROUND_LEN = 10;
const KEY = 'ig-progress-' + LESSON.id;

// ---------- ABAIR TTS ----------
function say(text) {
  if (!text) return;
  const payload = {
    synthinput: { text: text, ssml: 'string' },
    voiceparams: { languageCode: 'ga-IE', name: 'ga_MU_cmg_piper', ssmlGender: 'UNSPECIFIED' },
    audioconfig: { audioEncoding: 'LINEAR16', speakingRate: 1, volumeGainDb: 1, htsParams: 'string', sampleRateHertz: 0, effectsProfileId: [] },
    outputType: 'JSON'
  };
  fetch('https://api.abair.ie/v3/synthesis', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
    .then(r => r.json())
    .then(d => {
      if (!d.audioContent) return;
      const bytes = atob(d.audioContent);
      const arr = new Uint8Array(bytes.length);
      for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
      const url = URL.createObjectURL(new Blob([arr], { type: 'audio/wav' }));
      new Audio(url).play();
    })
    .catch(() => {});
}
window.say = say;

function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function q(tag, attrs, html) {
  const el = document.createElement(tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  if (html != null) el.innerHTML = html;
  return el;
}
function shuffle(a) {
  const arr = a.slice();
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}
function bindSay(root) {
  root.querySelectorAll('[data-say]').forEach(el => {
    el.addEventListener('click', e => { e.stopPropagation(); say(el.dataset.say); });
  });
}
function boxdisabled(sel) {
  [...document.querySelectorAll(sel)].forEach(o => { o.disabled = true; });
}

// ---------- progress ----------
function setProg(p) {
  p = Math.max(0, Math.min(100, Math.round(p)));
  localStorage.setItem(KEY, p);
  const f = document.getElementById('progFill');
  const t = document.getElementById('progPct');
  if (f) f.style.width = p + '%';
  if (t) t.textContent = p + '%';
}
function getProg() { return parseInt(localStorage.getItem(KEY) || '0', 10); }
function resetProg() {
  if (confirm('Reset progress for this lesson?')) { localStorage.removeItem(KEY); setProg(0); }
}
setProg(getProg());

// ---------- tabs ----------
document.querySelectorAll('.tabbtn').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('.tabbtn').forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
  b.classList.add('active');
  document.getElementById('panel-' + b.dataset.tab).classList.add('active');
}));

// ---------- study (prebuilt HTML) ----------
(function () {
  const host = document.getElementById('studyList');
  host.innerHTML = LESSON.study;
  bindSay(host);
})();

// =============================================================
//  DRILL (flashcards)
// =============================================================
const DRILL = LESSON.drill;
let drillOrder = shuffle([...DRILL.keys()]);
let drillIdx = 0;
function setDrill() {
  const d = DRILL[drillOrder[drillIdx]];
  const card = document.getElementById('flipcard');
  card.classList.remove('flipped');
  const fv = document.getElementById('drillVerb');
  fv.textContent = d.front;
  document.getElementById('drillEn').textContent = d.frontSub || '';
  document.getElementById('drillPrompt').textContent = d.prompt || '';
  document.getElementById('drillBack').innerHTML = d.back;
  document.getElementById('drillPos').textContent = (drillIdx + 1) + ' / ' + DRILL.length;
  document.getElementById('drillFill').style.width = ((drillIdx + 1) / DRILL.length * 100) + '%';
  bindSay(document.getElementById('drillBack'));
}
function flip() { document.getElementById('flipcard').classList.toggle('flipped'); }
function drillNext() {
  if (drillIdx === DRILL.length - 1) { drillOrder = shuffle([...DRILL.keys()]); drillIdx = 0; }
  else drillIdx++;
  setDrill();
  setProg(getProg() + Math.max(1, Math.round(100 / DRILL.length)));
}
function drillPrev() { if (drillIdx > 0) { drillIdx--; setDrill(); } }
setDrill();

// =============================================================
//  FILL (choose the missing word)
// =============================================================
const FILL = LESSON.fill;
let fillItems = [], fillIdx = 0, fillScore = 0, fillAnswered = 0;

function genFill() {
  fillItems = shuffle(FILL.slice()).slice(0, Math.min(ROUND_LEN, FILL.length));
  fillIdx = 0; fillScore = 0; fillAnswered = 0;
  fillShow();
}
function fillProgress() {
  document.getElementById('fillPos').textContent = (fillIdx + 1) + ' / ' + fillItems.length;
  document.getElementById('fillFill').style.width = ((fillIdx + 1) / fillItems.length * 100) + '%';
  document.getElementById('fillScore').textContent = fillScore + ' / ' + fillAnswered + ' correct';
}
function fillShow() {
  fillProgress();
  const it = fillItems[fillIdx];
  const box = q('div', { className: 'qcard' }, `
    <p class="qtype">${it.qtype}</p>
    <div class="q"><em>${it.sentence}</em>
      <span class="speak inline" data-say="${escHtml(it.say)}">🔊 listen</span></div>
    <div class="opts">${it.options.map(o => `<button class="opt" data-ok="${o === it.answer ? '1' : '0'}">${escHtml(o)}</button>`).join('')}</div>
    <div id="fillFb"></div>`);
  box.querySelectorAll('.opt').forEach(b => b.addEventListener('click', () => fillPick(b, it)));
  bindSay(box);
  const host = document.getElementById('fillQ');
  host.innerHTML = '';
  host.appendChild(box);
}
function fillPick(btn, it) {
  if (btn.disabled) return;
  boxdisabled('#fillQ .opt');
  const ok = btn.dataset.ok === '1';
  btn.classList.add(ok ? 'correct' : 'wrong');
  fillAnswered++;
  if (ok) fillScore++;
  const fb = document.getElementById('fillFb');
  fb.innerHTML = (ok ? '<div class="feedback ok">Correct! 🎉</div>'
    : `<div class="feedback no">Not quite — the answer is <b>${escHtml(it.answer)}</b>.</div>`)
    + `<div class="feedback sol">${it.english ? escHtml(it.english) + ' ' : ''}
       <span class="speak" data-say="${escHtml(it.say)}">🔊</span></div>`;
  bindSay(fb);
  fillProgress();
  setProg(getProg() + 1);
  const wrap = q('div', { className: 'navbtns' },
    fillIdx < fillItems.length - 1 ? '<button class="btn">Next →</button>' : '<button class="btn">See result 🏁</button>');
  wrap.querySelector('button').addEventListener('click', () => {
    if (fillIdx < fillItems.length - 1) { fillIdx++; fillShow(); } else fillResult();
  });
  fb.appendChild(wrap);
}
function fillResult() {
  const host = document.getElementById('fillQ');
  host.innerHTML = '';
  const card = q('div', { className: 'qcard results' }, `
    <h3>🏁 Round complete</h3>
    <p class="bigscore">You got <b>${fillScore}</b> of <b>${fillItems.length}</b> right.</p>
    <div class="navbtns">
      <button class="btn" id="fillAgain">Play again</button>
      <button class="btn ghost" onclick="document.querySelector('[data-tab=drill]').click()">Go to flashcards</button>
    </div>`);
  card.querySelector('#fillAgain').addEventListener('click', genFill);
  host.appendChild(card);
}
function fillReset() { genFill(); }
genFill();

// =============================================================
//  QUIZ
// =============================================================
const QUIZ = LESSON.quiz;
let quizItems = [], quizIdx = 0, quizScore = 0, quizAnswered = 0;

function genQuiz() {
  quizItems = shuffle(QUIZ.slice()).slice(0, Math.min(ROUND_LEN, QUIZ.length));
  quizIdx = 0; quizScore = 0; quizAnswered = 0;
  quizShow();
}
function quizProgress() {
  document.getElementById('quizPos').textContent = (quizIdx + 1) + ' / ' + quizItems.length;
  document.getElementById('quizFill').style.width = ((quizIdx + 1) / quizItems.length * 100) + '%';
  document.getElementById('quizScore').textContent = quizScore + ' / ' + quizAnswered + ' correct';
}
function quizShow() {
  quizProgress();
  const it = quizItems[quizIdx];
  const box = q('div', { className: 'qcard' }, `
    <p class="qtype"><span class="qtype-tag">${escHtml(it.badge)}</span></p>
    <div class="q">${it.q}${it.say ? ` <span class="speak inline" data-say="${escHtml(it.say)}">🔊 listen</span>` : ''}</div>
    <div class="opts">${it.options.map(o => `<button class="opt" data-ok="${o === it.correct ? '1' : '0'}">${escHtml(o)}</button>`).join('')}</div>
    <div id="quizFb"></div>`);
  box.querySelectorAll('.opt').forEach(b => b.addEventListener('click', () => quizPick(b, it)));
  bindSay(box);
  const host = document.getElementById('quizQ');
  host.innerHTML = '';
  host.appendChild(box);
}
function quizPick(btn, it) {
  if (btn.disabled) return;
  boxdisabled('#quizQ .opt');
  const ok = btn.dataset.ok === '1';
  btn.classList.add(ok ? 'correct' : 'wrong');
  quizAnswered++;
  if (ok) quizScore++;
  const fb = document.getElementById('quizFb');
  fb.innerHTML = (ok ? '<div class="feedback ok">Correct! 🎉</div>' : '<div class="feedback no">Not quite.</div>')
    + `<div class="feedback sol">Answer: <b>${escHtml(it.correct)}</b></div>`;
  quizProgress();
  setProg(getProg() + 1);
  const wrap = q('div', { className: 'navbtns' },
    quizIdx < quizItems.length - 1 ? '<button class="btn">Next →</button>' : '<button class="btn">See result 🏁</button>');
  wrap.querySelector('button').addEventListener('click', () => {
    if (quizIdx < quizItems.length - 1) { quizIdx++; quizShow(); } else quizResult();
  });
  fb.appendChild(wrap);
}
function quizResult() {
  const host = document.getElementById('quizQ');
  host.innerHTML = '';
  const card = q('div', { className: 'qcard results' }, `
    <h3>🏁 Quiz complete</h3>
    <p class="bigscore">You scored <b>${quizScore}</b> of <b>${quizItems.length}</b>.</p>
    <div class="navbtns">
      <button class="btn" id="quizAgain">Play again</button>
      <button class="btn ghost" onclick="document.querySelector('[data-tab=drill]').click()">Go to flashcards</button>
    </div>`);
  card.querySelector('#quizAgain').addEventListener('click', genQuiz);
  host.appendChild(card);
}
function quizReset() { genQuiz(); }
genQuiz();
