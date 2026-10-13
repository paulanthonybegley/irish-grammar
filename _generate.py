#!/usr/bin/env python3
"""
Generate the "Irish Grammar" interactive course from data/grammar.json.

Produces:
  - index.html                     (landing page, 6 lesson cards)
  - <slug>/index.html              (6 self-contained module apps)

Based on the YouTube playlist "Irish Grammar" by "Stories in Irish".
Each module is fully self-contained and provides Study / Flashcards /
Fill-in-the-blank / Quiz with ABAIR (ga-IE) text-to-speech and
localStorage progress.
"""
import json
import os
import random

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "data", "grammar.json"), encoding="utf-8") as f:
    DATA = json.load(f)

PRON = DATA["pronouns"]
VNS = DATA["verbalNouns"]
LESSONS = DATA["lessons"]
SRC = DATA["source"]

INDEX_CSS = open(os.path.join(HERE, "_work", "index.css"), encoding="utf-8").read()
MODULE_CSS = open(os.path.join(HERE, "_work", "module.css"), encoding="utf-8").read()
MODULE_JS = open(os.path.join(HERE, "_work", "module.js"), encoding="utf-8").read()

TENSE_EN = {"present": "present habitual", "future": "future", "past": "past"}
AUX_EN = {"present": "I am", "past": "I was", "future": "I will be"}


# ------------------------------------------------------------------ helpers
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def say_span(text, label=None):
    return f'<span class="irish" data-say="{esc(text)}">{esc(label if label is not None else text)}</span>'


LEN = {"b": "bh", "c": "ch", "d": "dh", "f": "fh", "g": "gh", "m": "mh", "p": "ph", "s": "sh", "t": "th"}
ECL = {"b": "mb", "c": "gc", "d": "nd", "f": "bhf", "g": "ng", "p": "bp", "t": "dt"}
VOWELS = "aeiouáéíóú"


def slender(root):
    for ch in reversed(root.lower()):
        if ch in VOWELS:
            return ch in "eiéí"
    return False


def lenite(w):
    if not w:
        return w
    c = w[0].lower()
    return LEN[c] + w[1:] if c in LEN else w


def eclipse(w):
    if not w:
        return w
    c = w[0].lower()
    if c in ECL:
        return ECL[c] + w[1:]
    if c in VOWELS:
        return "n-" + w
    return w


def split_form(f):
    parts = f.split(" ", 1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def join_form(w, rest):
    return w + (" " + rest if rest else "")


def derive_pf(pos):
    neg, q, negq = [], [], []
    for f in pos:
        w, rest = split_form(f)
        neg.append("Ní " + join_form(lenite(w), rest))
        q.append("An " + join_form(eclipse(w), rest) + "?")
        negq.append("Nach " + join_form(eclipse(w), rest) + "?")
    return neg, q, negq


def derive_past(pos):
    neg, q, negq = [], [], []
    for f in pos:
        w, rest = split_form(f)
        if w.startswith("d'"):
            w = w[2:]
        neg.append("Níor " + join_form(w, rest))
        q.append("Ar " + join_form(w, rest) + "?")
        negq.append("Nár " + join_form(w, rest) + "?")
    return neg, q, negq


def past_stem(root):
    c = root[0].lower()
    if c in VOWELS:
        return "d'" + root
    if c == "f":
        return "d'fh" + root[1:]
    return lenite(root)


def c1_present(root):
    s = slender(root)
    base = root + ("eann" if s else "ann")
    return [root + ("im" if s else "aim"), base + " tú", base + " sé", base + " sí",
            root + ("imid" if s else "aimid"), base + " sibh", base + " siad",
            root + ("tear" if s else "tar")]


def c1_future(root):
    s = slender(root)
    base = root + ("fidh" if s else "faidh")
    return [base + " mé", base + " tú", base + " sé", base + " sí",
            root + ("fimid" if s else "faimid"), base + " sibh", base + " siad",
            root + ("fear" if s else "far")]


def c1_past(root):
    s = slender(root)
    stem = past_stem(root)
    return [stem + " mé", stem + " tú", stem + " sé", stem + " sí",
            past_stem(root + ("eamar" if s else "amar")), stem + " sibh", stem + " siad",
            root + ("eadh" if s else "adh")]


def c2_present(stem):
    return [stem + "m", stem + "onn tú", stem + "onn sé", stem + "onn sí",
            stem + "mid", stem + "onn sibh", stem + "onn siad", stem + "tear"]


def c2_future(fut, fut1p):
    return [fut + " mé", fut + " tú", fut + " sé", fut + " sí",
            fut1p, fut + " sibh", fut + " siad", fut[:-3] + "far"]


def c2_past(root, stem):
    s3 = past_stem(root)
    return [s3 + " mé", s3 + " tú", s3 + " sé", s3 + " sí",
            past_stem(stem + "omar"), s3 + " sibh", s3 + " siad", stem + "odh"]


def opts4(correct, pool, suffix=""):
    seen = {correct}
    out = [correct]
    for x in pool:
        x = x + suffix
        if x and x not in seen:
            seen.add(x)
            out.append(x)
        if len(out) == 4:
            break
    while len(out) < 4:
        out.append("—")
    random.shuffle(out)
    return out


def find_form(sentence, forms):
    low = sentence.lower()
    for f in sorted(forms, key=len, reverse=True):
        i = low.find(f.lower())
        if i != -1:
            return sentence[:i], sentence[i + len(f):], f
    return None, None, None


# ------------------------------------------------------ build verb paradigms
def build_regular(v, tense):
    if v["conj"] == 1:
        pos = {"present": c1_present, "future": c1_future, "past": c1_past}[tense](v["root"])
    else:
        if tense == "present":
            pos = c2_present(v["stem"])
        elif tense == "future":
            pos = c2_future(v["fut"], v["fut1p"])
        else:
            pos = c2_past(v["root"], v["stem"])
    if tense == "past":
        neg, q, negq = derive_past(pos)
    else:
        neg, q, negq = derive_pf(pos)
    return {"root": v["root"], "meaning": v["meaning"], "example": v["example"],
            "en_example": v["en_example"], "pos": pos, "neg": neg, "q": q, "negq": negq,
            "irregular": False}


def build_irregular(v):
    return {"root": v["root"], "meaning": v["meaning"], "example": v["example"],
            "en_example": v["en_example"], "pos": v["pos"], "neg": v["neg"],
            "q": v["q"], "negq": v["negq"], "irregular": True}


def verbs_of(lesson):
    return [build_regular(v, lesson["tense"]) for v in lesson["verbs"]] + \
           [build_irregular(v) for v in lesson["irregulars"]]


# ------------------------------------------------------------------- study
def study_continuous(lesson):
    aux = lesson["aux"]
    rows = ""
    for i, p in enumerate(PRON):
        rows += ("<tr>"
                 f'<td class="pron">{p}</td>'
                 f'<td>{say_span(aux["pos"][i])}</td>'
                 f'<td>{say_span(aux["neg"][i])}</td>'
                 f'<td>{say_span(aux["q"][i])}</td>'
                 f'<td>{say_span(aux["negq"][i])}</td>'
                 "</tr>")
    uses = "".join(
        f'<li>{say_span(u["irish"])} — <em>{esc(u["english"])}</em></li>' for u in lesson["uses"])
    signals = "".join(
        f'<span class="chip" data-say="{esc(s["irish"])}">{esc(s["irish"])} · {esc(s["english"])}</span>'
        for s in lesson["signalWords"])
    base1 = aux["pos"][0].split(" / ")[0]
    vn_rows = ""
    for vn in VNS:
        ex = f"{base1} ag {vn['vn']}."
        vn_rows += ("<tr>"
                    f'<td>{say_span(vn["vn"])}</td>'
                    f'<td>{esc(vn["meaning"])}</td>'
                    f'<td>{esc(vn["english"])}</td>'
                    f'<td>{say_span(ex)}</td>'
                    "</tr>")
    notes = "".join(f'<div class="note"><h4>{esc(n["title"])}</h4>{n["html"]}</div>'
                    for n in lesson["notes"])
    return f"""
    <div class="patternbox"><b>{esc(lesson['pattern'])}</b>
      <span class="en">{esc(lesson['patternEnglish'])} — {esc(lesson['summary'])}</span></div>
    <h3 class="section-h">When we use it</h3>
    <ul class="uses">{uses}</ul>
    <h3 class="section-h">Signal words</h3>
    <div class="signal">{signals}</div>
    <h3 class="section-h">The verb bí — {esc(aux['english'])}</h3>
    <table class="conj">
      <tr><th>Pronoun</th><th>Positive</th><th>Negative</th><th>Question</th><th>Neg. question</th></tr>
      {rows}
    </table>
    <h3 class="section-h">The verbal noun (an t-ainm briathartha)</h3>
    <p class="empty-note">After <b>ag</b> we use the verbal noun. It never changes for person.</p>
    <table class="conj">
      <tr><th>Verbal noun</th><th>Meaning</th><th>Verb</th><th>Example</th></tr>
      {vn_rows}
    </table>
    <h3 class="section-h">Notes</h3>
    {notes}
    """


def verb_table(v):
    rows = ""
    for i, p in enumerate(PRON):
        rows += ("<tr>"
                 f'<td class="pron">{p}</td>'
                 f'<td>{say_span(v["pos"][i])}</td>'
                 f'<td>{say_span(v["neg"][i])}</td>'
                 f'<td>{say_span(v["q"][i])}</td>'
                 f'<td>{say_span(v["negq"][i])}</td>'
                 "</tr>")
    return f"""
    <p><b>Example:</b> <span class="irish" data-say="{esc(v['example'])}">{esc(v['example'])}</span>
       — <em>{esc(v['en_example'])}</em></p>
    <table class="conj">
      <tr><th>Pronoun</th><th>Positive</th><th>Negative</th><th>Question</th><th>Neg. question</th></tr>
      {rows}
    </table>"""


def study_simple(lesson):
    verbs = verbs_of(lesson)
    regs = [v for v in verbs if not v["irregular"]]
    irrs = [v for v in verbs if v["irregular"]]
    signals = "".join(
        f'<span class="chip" data-say="{esc(s["irish"])}">{esc(s["irish"])} · {esc(s["english"])}</span>'
        for s in lesson["signalWords"])
    notes = "".join(f'<div class="note"><h4>{esc(n["title"])}</h4>{n["html"]}</div>'
                    for n in lesson["notes"])

    def block(items):
        out = ""
        for v in items:
            flag = " ⭐" if v["irregular"] else ""
            out += (f'<details class="verb"><summary>{esc(v["root"])}{flag} '
                    f'<span class="m">— {esc(v["meaning"])}</span></summary>{verb_table(v)}</details>')
        return out

    return f"""
    <div class="patternbox"><b>{esc(lesson['titleIrish'])}</b>
      <span class="en">{esc(lesson['summary'])}</span></div>
    <h3 class="section-h">Signal words</h3>
    <div class="signal">{signals}</div>
    {notes}
    <h3 class="section-h">Regular verbs</h3>
    {block(regs)}
    <h3 class="section-h">Irregular verbs ⭐</h3>
    {block(irrs)}
    """


# ------------------------------------------------------------------- pools
def continuous_pools(lesson):
    aux = lesson["aux"]
    base1 = aux["pos"][0].split(" / ")[0]
    neg1 = aux["neg"][0].split(" / ")[0]
    q1 = aux["q"][0]
    negq1 = aux["negq"][0]
    en_aux = AUX_EN[lesson["auxTense"]]

    drill = []
    fill = []
    quiz = []
    vn_choices = [v["vn"] for v in VNS]
    meaning_choices = [v["meaning"] for v in VNS]

    for vn in VNS:
        ex = f"{base1} ag {vn['vn']}."
        drill.append({
            "front": vn["meaning"], "frontSub": vn["english"],
            "prompt": "Give the verbal noun with ag",
            "back": f'<div class="prep">ag {esc(vn["vn"])}</div>'
                    f'<span data-say="{esc(ex)}">{esc(ex)}</span>',
            "say": ex,
        })
        fill.append({
            "qtype": "Which verbal noun completes the sentence?",
            "sentence": f"{esc(base1)} ag ______.",
            "answer": vn["vn"], "english": f"{en_aux} {vn['meaning']}.",
            "say": ex, "options": opts4(vn["vn"], [x for x in vn_choices if x != vn["vn"]]),
        })
        quiz.append({
            "badge": "Verbal noun",
            "q": f"Which verbal noun means '<b>{esc(vn['meaning'])}</b>'?",
            "options": opts4(vn["vn"], [x for x in vn_choices if x != vn["vn"]]),
            "correct": vn["vn"],
        })

    for i, p in enumerate(PRON):
        quiz.append({
            "badge": "bí — positive",
            "q": f"Which is the <b>positive</b> form of <b>bí</b> for '<b>{p}</b>'?",
            "options": opts4(aux["pos"][i], [aux["pos"][j] for j in range(len(PRON)) if j != i]),
            "correct": aux["pos"][i],
        })
        quiz.append({
            "badge": "bí — negative",
            "q": f"Which is the <b>negative</b> form of <b>bí</b> for '<b>{p}</b>'?",
            "options": opts4(aux["neg"][i], [aux["neg"][j] for j in range(len(PRON)) if j != i]),
            "correct": aux["neg"][i],
        })

    for vn in random.sample(VNS, 8):
        correct = f"{base1} ag {vn['vn']}"
        quiz.append({
            "badge": "Build the sentence",
            "q": f"How do you say '<b>{en_aux} {esc(vn['meaning'])}</b>'?",
            "options": opts4(correct, [f"{base1} ag {x['vn']}" for x in VNS if x["vn"] != vn["vn"]]),
            "correct": correct, "say": correct + ".",
        })
        quiz.append({
            "badge": "Make it negative",
            "q": f"Make it negative: '<b>{esc(correct)}</b>'",
            "options": opts4(
                f"{neg1} ag {vn['vn']}",
                [f"{q1} ag {vn['vn']}", f"{negq1} ag {vn['vn']}"] +
                [f"{base1} ag {x['vn']}" for x in VNS if x["vn"] != vn["vn"]]),
            "correct": f"{neg1} ag {vn['vn']}",
        })
    return drill, fill, quiz


def simple_pools(lesson):
    verbs = verbs_of(lesson)
    tense = lesson["tense"]
    drill = []
    fill = []
    quiz = []

    for vi, v in enumerate(verbs):
        forms_show = " · ".join(f"{PRON[i]}: {v['pos'][i]}" for i in (0, 2, 4, 7))
        drill.append({
            "front": v["root"], "frontSub": f"({v['meaning']})",
            "prompt": f"{TENSE_EN[tense]} — tap to flip",
            "back": f'<div class="prep">{esc(v["root"])} — {esc(v["meaning"])}</div>'
                    f'<div style="font-size:.9rem;opacity:.95">{esc(forms_show)}</div>'
                    f'<span data-say="{esc(v["example"])}">{esc(v["example"])}</span>',
            "say": v["example"],
        })

        pre, post, answer = find_form(v["example"], v["pos"])
        if answer is None:
            answer = v["pos"][2]
            fill.append({
                "qtype": f"Complete with the correct form of '<b>{esc(v['root'])}</b>'.",
                "sentence": f"{esc(v['example'])} (answer: ______)",
                "answer": answer, "english": v["en_example"], "say": v["example"],
                "options": opts4(answer, [v["pos"][j] for j in range(8) if j != 2]),
            })
        else:
            fill.append({
                "qtype": f"Complete with the correct form of '<b>{esc(v['root'])}</b>'.",
                "sentence": f"{esc(pre)}<b>______</b>{esc(post)}",
                "answer": answer, "english": v["en_example"], "say": v["example"],
                "options": opts4(answer, [f for f in v["pos"] if f != answer]),
            })

        pron_i = vi % 8
        quiz.append({
            "badge": "Conjugate",
            "q": f"Which is the correct form of '<b>{esc(v['root'])}</b>' ({esc(v['meaning'])}) "
                 f"for '<b>{PRON[pron_i]}</b>' in the {TENSE_EN[tense]}?",
            "options": opts4(v["pos"][pron_i], [v["pos"][j] for j in range(8) if j != pron_i]),
            "correct": v["pos"][pron_i], "say": v["pos"][pron_i],
        })
        quiz.append({
            "badge": "Negative",
            "q": f"What is the <b>negative</b> of '<b>{esc(v['pos'][2])}</b>'?",
            "options": opts4(v["neg"][2], [v["neg"][j] for j in range(8) if j != 2]),
            "correct": v["neg"][2], "say": v["neg"][2],
        })
        quiz.append({
            "badge": "Meaning",
            "q": f"What does '<b>{esc(v['pos'][2])}</b>' mean?",
            "options": opts4(v["meaning"], [x["meaning"] for x in verbs if x["meaning"] != v["meaning"]]),
            "correct": v["meaning"],
        })
    return drill, fill, quiz


# ------------------------------------------------------------------- render
def render_index():
    cards = ""
    for lesson in LESSONS:
        if lesson["kind"] == "continuous":
            meta = f"{len(VNS)} verbal nouns"
        else:
            meta = f"{len(lesson['verbs']) + len(lesson['irregulars'])} verbs"
        cards += f"""
<div class="card">
  <div class="card-body">
    <div class="num">Lesson {lesson['id']} · {meta}</div>
    <h3>{lesson['emoji']} {esc(lesson['titleIrish'])}</h3>
    <div class="sub">{esc(lesson['titleEnglish'])}</div>
    <p>{esc(lesson['summary'])}</p>
    <div class="meta"><span>🔊 Audio</span><span>🃏 Cards</span><span>🎯 Quiz</span>
      <div class="bar"><div class="fill" id="bar{lesson['id']}" style="width:0%"></div></div>
      <span id="pct{lesson['id']}">0%</span>
    </div>
    <a class="btn" href="{lesson['slug']}/index.html">Start lesson →</a>
  </div>
</div>"""

    ids_js = json.dumps([l["id"] for l in LESSONS])
    total_v = sum(len(l.get("verbs", [])) + len(l.get("irregulars", [])) for l in LESSONS)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Irish Grammar — Interactive Course</title>
<style>{INDEX_CSS}</style>
</head>
<body>
<header>
  <h1>🍀 Irish Grammar</h1>
  <p>Six interactive lessons on the tenses of Irish — continuous and simple — with conjugation tables, drills and ABAIR pronunciation.</p>
</header>
<div class="container">
  <div class="intro">
    <h2>Fáilte! · About this course</h2>
    <p>An interactive companion to the YouTube playlist
    <a href="{SRC['playlistUrl']}" target="_blank" rel="noopener"><strong>“{esc(SRC['playlistTitle'])}”</strong></a>
    by <strong>{esc(SRC['channel'])}</strong>. The playlist covers the three continuous tenses
    (present, past, future) and the three simple tenses (habitual present, future, past).
    Each lesson turns the video into an active practice programme: rules and conjugation tables,
    flashcards, fill-in-the-blanks and a quiz — with Irish audio from <strong>ABAIR</strong>.</p>
    <p style="margin-top:.5rem">Click any green Irish word to hear it spoken. Your progress is saved automatically.</p>
  </div>
  <div class="course-grid">{cards}</div>
  <div class="stats">
    <div class="stat"><b>6</b> lessons</div>
    <div class="stat"><b>{total_v}</b> verb paradigms</div>
    <div class="stat"><b>{len(VNS)}</b> verbal nouns</div>
    <div class="stat"><b>🔊</b> Irish audio (ABAIR)</div>
  </div>
  <div class="intro" style="margin-top:1.4rem">
    <h2>🎥 About the channel</h2>
    <p>Watch the videos first, then work through the lessons actively. Channel:
    <a href="{SRC['channelUrl']}" target="_blank" rel="noopener">{esc(SRC['channel'])}</a>.
    Audio is synthesised by <a href="https://abair.ie" target="_blank" rel="noopener">ABAIR</a> (Trinity College Dublin).</p>
  </div>
</div>
<footer>
  <p>Based on the <a href="{SRC['playlistUrl']}" target="_blank">“{esc(SRC['playlistTitle'])}”</a> playlist by {esc(SRC['channel'])}</p>
  <p>Irish audio by <a href="https://abair.ie" target="_blank">ABAIR</a> (Trinity College Dublin)</p>
</footer>
<script>
const IDS = {ids_js};
function fmt(){{
  IDS.forEach(id=>{{
    const p = parseInt(localStorage.getItem('ig-progress-'+id)||'0',10);
    const b = document.getElementById('bar'+id), t = document.getElementById('pct'+id);
    if (b) b.style.width = Math.round(p)+'%';
    if (t) t.textContent = Math.round(p)+'%';
  }});
}}
fmt();
window.addEventListener('storage', fmt);
</script>
</body>
</html>
"""
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote index.html")


def render_module(lesson):
    if lesson["kind"] == "continuous":
        study = study_continuous(lesson)
        drill, fill, quiz = continuous_pools(lesson)
    else:
        study = study_simple(lesson)
        drill, fill, quiz = simple_pools(lesson)

    payload = {
        "id": lesson["id"], "kind": lesson["kind"],
        "study": study, "drill": drill, "fill": fill, "quiz": quiz,
    }
    lesson_js = json.dumps(payload, ensure_ascii=False)
    count = len(VNS) if lesson["kind"] == "continuous" else len(lesson["verbs"]) + len(lesson["irregulars"])
    unit = "ag + verbal noun" if lesson["kind"] == "continuous" else "verb forms"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lesson {lesson['id']}: {esc(lesson['titleIrish'])} — Irish Grammar</title>
<style>{MODULE_CSS}</style>
</head>
<body>
<div class="topbar">
  <a href="../index.html">← Course overview</a>
  <span class="title">{lesson['emoji']} Lesson {lesson['id']}: {esc(lesson['titleIrish'])}</span>
  <span>🔊 ga-IE</span>
</div>
<header class="hdr">
  <h1>{lesson['emoji']} {esc(lesson['titleIrish'])}</h1>
  <p>{esc(lesson['titleEnglish'])} · {count} {unit}</p>
  <a class="yt" href="{lesson['videoUrl']}" target="_blank" rel="noopener">▶ Watch the video</a>
</header>
<div class="container">
  <div class="progressbox">
    <span>Progress</span>
    <div class="bar"><div class="fill" id="progFill" style="width:0%"></div></div>
    <span id="progPct">0%</span>
    <button class="btn ghost" onclick="resetProg()">Reset</button>
  </div>

  <div class="tabs">
    <button class="tabbtn active" data-tab="study">📚 Study</button>
    <button class="tabbtn" data-tab="drill">🃏 Flashcards</button>
    <button class="tabbtn" data-tab="fill">✍️ Fill in</button>
    <button class="tabbtn" data-tab="quiz">🎯 Quiz</button>
  </div>

  <section class="panel active" id="panel-study">
    <h2>Study</h2>
    <p class="lede">{esc(lesson['summary'])} Click any green Irish word to hear it.</p>
    <div id="studyList"></div>
  </section>

  <section class="panel" id="panel-drill">
    <h2>Flashcards</h2>
    <p class="lede">Think of the answer, then flip the card to check.</p>
    <div class="progressbox"><span>Card</span><span id="drillPos">1 / 1</span>
      <div class="bar"><div class="fill" id="drillFill" style="width:0%"></div></div></div>
    <div class="flipcard" id="flipcard" onclick="flip()">
      <div class="inner">
        <div class="face front">
          <div class="prompt" id="drillPrompt"></div>
          <div class="verb" id="drillVerb"></div>
          <div class="en" id="drillEn"></div>
          <div class="hint">Click for the answer</div>
        </div>
        <div class="face back" id="drillBack"></div>
      </div>
    </div>
    <div class="navbtns">
      <button class="btn ghost" onclick="drillPrev()">← Back</button>
      <button class="btn" onclick="drillNext()">Next →</button>
    </div>
    <p class="empty-note">Cards appear in a random order.</p>
  </section>

  <section class="panel" id="panel-fill">
    <h2>Fill in the blank</h2>
    <p class="lede">Choose the correct word to complete each sentence.</p>
    <div class="progressbox"><span>Question</span><span id="fillPos">1 / {min(10, len(fill))}</span>
      <div class="bar"><div class="fill" id="fillFill" style="width:0%"></div></div>
      <span>Score</span><span id="fillScore">0 / 0</span></div>
    <div id="fillQ"></div>
    <div class="navbtns"><button class="btn ghost" onclick="fillReset()">Reshuffle</button></div>
    <p class="empty-note">{min(10, len(fill))} random sentences each round.</p>
  </section>

  <section class="panel" id="panel-quiz">
    <h2>Quiz</h2>
    <p class="lede">Mixed questions on forms, negatives, questions and meaning.</p>
    <div class="progressbox"><span>Question</span><span id="quizPos">1 / {min(10, len(quiz))}</span>
      <div class="bar"><div class="fill" id="quizFill" style="width:0%"></div></div>
      <span>Score</span><span id="quizScore">0 / 0</span></div>
    <div id="quizQ"></div>
    <div class="navbtns"><button class="btn ghost" onclick="quizReset()">Reshuffle</button></div>
    <p class="empty-note">10 questions drawn from the full pool.</p>
  </section>
</div>
<footer style="text-align:center;padding:1.6rem;color:var(--grey);font-size:.88rem">
  <p>Lesson {lesson['id']} of 6 · Based on “{esc(SRC['playlistTitle'])}” by {esc(SRC['channel'])} ·
  <a href="../index.html" style="color:var(--green)">Course overview</a></p>
</footer>
<script>
const LESSON = {lesson_js};
{MODULE_JS}
</script>
</body>
</html>
"""
    outdir = os.path.join(HERE, lesson["slug"])
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {lesson['slug']}/index.html")


if __name__ == "__main__":
    render_index()
    for lesson in LESSONS:
        render_module(lesson)
    print("Done.")
