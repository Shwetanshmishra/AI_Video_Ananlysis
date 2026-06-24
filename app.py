import streamlit as st
import time
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500&display=swap');

:root {
    --bg:           #0a0a0f;
    --surface:      #111118;
    --surface-2:    #1a1a25;
    --border:       #2a2a3a;
    --accent:       #7c3aed;
    --accent-glow:  #9f67ff;
    --accent-2:     #06b6d4;
    --text:         #e8e8f0;
    --text-muted:   #7070a0;
    --success:      #10b981;
    --warning:      #f59e0b;
    --danger:       #ef4444;
}

/* ── Global ── */
html, body, [class*="css"], .stApp {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background: var(--bg) !important; }

/* grid overlay */
.stApp::before {
    content: '';
    position: fixed; top: 0; left: 0;
    width: 100%; height: 100%;
    background-image:
        linear-gradient(rgba(124,58,237,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(124,58,237,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}

/* ── Hide default chrome ── */
#MainMenu, footer { visibility: hidden !important; }
[data-testid="stDecoration"] { display: none !important; }

/* ── Main block container ── */
.main .block-container { background: transparent !important; }
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="column"] { background: transparent !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── Sidebar toggle button — always visible ── */
[data-testid="collapsedControl"],
button[data-testid="baseButton-headerNoPadding"] {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 6px !important;
}
[data-testid="collapsedControl"]:hover {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
}

/* ── Typography ── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Syne', sans-serif !important;
    color: var(--text) !important;
}

/* ── Hero ── */
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(135deg, #ffffff 0%, var(--accent-glow) 50%, var(--accent-2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: var(--text-muted);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 0.5rem;
}

/* ── Cards ── */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.card:hover { border-color: var(--accent); }
.card::before {
    content: '';
    position: absolute; top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, var(--accent), var(--accent-2));
}
.card-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
}
.card-content {
    font-size: 0.875rem;
    line-height: 1.7;
    color: var(--text);
}

/* ── Badges ── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}
.badge-purple { background: rgba(124,58,237,0.2); color: var(--accent-glow); border: 1px solid rgba(124,58,237,0.3); }
.badge-cyan   { background: rgba(6,182,212,0.15);  color: var(--accent-2);   border: 1px solid rgba(6,182,212,0.3); }
.badge-green  { background: rgba(16,185,129,0.15); color: var(--success);    border: 1px solid rgba(16,185,129,0.3); }

/* ── ALL text inputs — DARK, including chat ── */
input, textarea,
[data-testid="stTextInput"] input,
[data-testid="stTextInput"] textarea,
.stTextInput input,
.stTextInput textarea,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
    background: var(--surface-2) !important;
    background-color: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    caret-color: var(--accent-glow) !important;
}
input::placeholder, textarea::placeholder { color: var(--text-muted) !important; opacity: 1 !important; }
input:focus, textarea:focus,
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(124,58,237,0.2) !important;
    outline: none !important;
}

/* BaseUI input wrapper — prevent white background leaking in */
[data-baseweb="input"],
[data-baseweb="base-input"],
[class*="InputContainer"] {
    background: var(--surface-2) !important;
    background-color: var(--surface-2) !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
    background: #1a1a25 !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
}
[data-baseweb="option"], [role="option"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}
[data-baseweb="option"]:hover, [role="option"]:hover,
[data-baseweb="option"][aria-selected="true"], [role="option"][aria-selected="true"] {
    background: rgba(124,58,237,0.15) !important;
    color: var(--accent-glow) !important;
}

/* ── ALL Buttons — purple theme ── */
[data-testid="stButton"] > button,
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, var(--accent), #5b21b6) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s !important;
    text-transform: uppercase !important;
    width: 100% !important;
}
[data-testid="stButton"] > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 25px rgba(124,58,237,0.4) !important;
}

/* Download button — secondary style */
[data-testid="stDownloadButton"] > button {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-muted) !important;
    box-shadow: none !important;
    text-transform: none !important;
    font-size: 0.78rem !important;
    width: auto !important;
}

/* ── File uploader ── */
[data-testid="stFileUploaderDropzone"] {
    background: var(--surface-2) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--accent) !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-muted) !important;
    width: auto !important;
    text-transform: none !important;
    box-shadow: none !important;
}
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] small { color: var(--text-muted) !important; }

/* ── Status/spinner/info ── */
[data-testid="stStatus"],
[data-testid="stStatusWidget"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
}
[data-testid="stStatusWidget"] > div { background: transparent !important; }

[data-testid="stSpinner"] > div,
.stSpinner > div { color: var(--accent-glow) !important; }
.stSpinner svg circle { stroke: var(--accent-glow) !important; }

[data-testid="stInfo"] {
    background: rgba(124,58,237,0.08) !important;
    border: 1px solid rgba(124,58,237,0.25) !important;
    border-radius: 8px !important;
    color: var(--accent-glow) !important;
}
[data-testid="stAlert"] {
    background: rgba(239,68,68,0.08) !important;
    border: 1px solid rgba(239,68,68,0.25) !important;
    border-radius: 8px !important;
    color: #fca5a5 !important;
}
.stSuccess, [data-testid="stSuccess"] {
    background: rgba(16,185,129,0.08) !important;
    border: 1px solid rgba(16,185,129,0.25) !important;
    border-radius: 8px !important;
    color: var(--success) !important;
}

/* ── Forms (prevent white bg) ── */
[data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
[data-testid="stExpander"] summary {
    color: var(--text) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}
[data-testid="stExpander"] > div { background: transparent !important; }

/* ── Pipeline status bars ── */
.status-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0.9rem;
    background: var(--surface-2);
    border-radius: 8px;
    margin: 0.3rem 0;
    border: 1px solid var(--border);
    font-size: 0.78rem;
    color: var(--text);
}
.status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dot-active  { background: var(--accent-glow); box-shadow: 0 0 8px var(--accent-glow); animation: pulse 1.5s infinite; }
.dot-done    { background: var(--success); }
.dot-pending { background: var(--border); }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }

/* ── Chat ── */
.chat-container {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    max-height: 420px;
    overflow-y: auto;
    margin-bottom: 1rem;
}
.chat-msg { margin-bottom: 1rem; display: flex; flex-direction: column; gap: 0.2rem; }
.chat-label { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; }
.chat-bubble { display: inline-block; padding: 0.6rem 1rem; border-radius: 10px; font-size: 0.85rem; line-height: 1.6; max-width: 90%; }
.user-label  { color: var(--accent-glow); }
.bot-label   { color: var(--accent-2); }
.user-bubble { background: rgba(124,58,237,0.15); border: 1px solid rgba(124,58,237,0.25); align-self: flex-end; }
.bot-bubble  { background: rgba(6,182,212,0.1);  border: 1px solid rgba(6,182,212,0.2);   align-self: flex-start; }

/* ── Transcript ── */
.transcript-box {
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    font-size: 0.82rem;
    line-height: 1.8;
    max-height: 300px;
    overflow-y: auto;
    color: var(--text-muted);
    white-space: pre-wrap;
    word-break: break-word;
}
.highlight { background: rgba(124,58,237,0.3); color: var(--accent-glow); border-radius: 2px; padding: 0 2px; }

/* ── Code blocks ── */
[data-testid="stCode"], [data-testid="stCode"] pre, [data-testid="stCode"] code {
    background: var(--surface-2) !important;
    color: var(--text-muted) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Labels ── */
label, [data-testid="stWidgetLabel"] {
    color: var(--text-muted) !important;
    font-size: 0.78rem !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Misc ── */
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1.5rem 0 !important; }
[data-testid="stMarkdownContainer"] p { color: var(--text) !important; }
.stProgress > div > div > div { background: var(--accent) !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────────────────────
for key, default in {
    "result": None,
    "chat_history": [],
    "processing": False,
    "pipeline_done": False,
    "pipeline_steps": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helpers ───────────────────────────────────────────
PIPELINE_STEPS = [
    ("audio",      "🔊", "Audio Processing"),
    ("transcript", "📝", "Transcription"),
    ("title",      "🏷️",  "Title Generation"),
    ("summary",    "📋", "Summarisation"),
    ("extract",    "🔍", "Extraction"),
    ("rag",        "🧠", "RAG Engine"),
]
_STEP_META = {k: (icon, label) for k, icon, label in PIPELINE_STEPS}

def _step_html(key, state):
    icon, label = _STEP_META[key]
    dot = {"active": "dot-active", "done": "dot-done"}.get(state, "dot-pending")
    return (
        f'<div class="status-bar">'
        f'<div class="status-dot {dot}"></div>'
        f'<span>{icon} {label}</span>'
        f'</div>'
    )

step_slots: dict = {}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="hero-title" style="font-size:1.6rem">🎬 AI<br>Video</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Meeting Intelligence</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<span class="badge badge-purple">Source</span>', unsafe_allow_html=True)

    input_mode = st.radio("Input mode", ["YouTube URL", "Upload file"], label_visibility="hidden")

    source = None
    if input_mode == "YouTube URL":
        url_val = st.text_input("YouTube URL", placeholder="https://youtube.com/watch?v=...", label_visibility="hidden")
        source = url_val.strip() if url_val else None
    else:
        uploaded = st.file_uploader("Upload video or audio", type=["mp4","mov","avi","mkv","webm","mp3","wav"], label_visibility="hidden")
        if uploaded:
            suffix = os.path.splitext(uploaded.name)[1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(uploaded.read())
            tmp.flush()
            source = tmp.name

    st.markdown("---")
    st.markdown('<span class="badge badge-cyan">Language</span>', unsafe_allow_html=True)
    language = st.selectbox("Language", ["english", "hinglish"], label_visibility="hidden")

    st.markdown("---")
    run_btn = st.button("⚡  Analyse", use_container_width=True)

    # ── Pipeline status ─ always visible, updates live via placeholders ──
    st.markdown("---")
    st.markdown('<span class="badge badge-green">Pipeline Status</span>', unsafe_allow_html=True)
    for _key, _icon, _label in PIPELINE_STEPS:
        step_slots[_key] = st.empty()
        _state = st.session_state.pipeline_steps.get(_key, "pending")
        step_slots[_key].markdown(_step_html(_key, _state), unsafe_allow_html=True)

# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">AI Video Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Transcribe · Summarise · Chat with your meetings</div>', unsafe_allow_html=True)
st.markdown("---")

# ── Run Pipeline ──────────────────────────────────────────────────────────────
if run_btn:
    if not source:
        st.error("Please enter a YouTube URL or upload a file.")
    else:
        from utils.audio_processor import process_input
        from core.transcriber import transcribe_all
        from core.summarizer import summarize, generate_title
        from core.extractor import extract_action_items, extract_key_decisions, extract_questions
        from core.rag_engine import build_rag_chain

        st.session_state.pipeline_done = False
        st.session_state.result = None
        st.session_state.chat_history = []
        st.session_state.pipeline_steps = {k: "pending" for k, _, _ in PIPELINE_STEPS}
        for _k, _icon2, _lbl2 in PIPELINE_STEPS:
            step_slots[_k].markdown(_step_html(_k, "pending"), unsafe_allow_html=True)

        progress_ph = st.empty()

        try:
            progress_ph.info("⚙️ Pipeline running — see sidebar for live status…")

            st.session_state.pipeline_steps["audio"] = "active"
            if "audio" in step_slots:
                step_slots["audio"].markdown(_step_html("audio", "active"), unsafe_allow_html=True)
            chunks = process_input(source)
            st.session_state.pipeline_steps["audio"] = "done"
            if "audio" in step_slots:
                step_slots["audio"].markdown(_step_html("audio", "done"), unsafe_allow_html=True)

            st.session_state.pipeline_steps["transcript"] = "active"
            if "transcript" in step_slots:
                step_slots["transcript"].markdown(_step_html("transcript", "active"), unsafe_allow_html=True)
            transcript = transcribe_all(chunks, language)
            st.session_state.pipeline_steps["transcript"] = "done"
            if "transcript" in step_slots:
                step_slots["transcript"].markdown(_step_html("transcript", "done"), unsafe_allow_html=True)

            st.session_state.pipeline_steps["title"] = "active"
            if "title" in step_slots:
                step_slots["title"].markdown(_step_html("title", "active"), unsafe_allow_html=True)
            title = generate_title(transcript)
            st.session_state.pipeline_steps["title"] = "done"
            if "title" in step_slots:
                step_slots["title"].markdown(_step_html("title", "done"), unsafe_allow_html=True)

            st.session_state.pipeline_steps["summary"] = "active"
            if "summary" in step_slots:
                step_slots["summary"].markdown(_step_html("summary", "active"), unsafe_allow_html=True)
            summary = summarize(transcript)
            st.session_state.pipeline_steps["summary"] = "done"
            if "summary" in step_slots:
                step_slots["summary"].markdown(_step_html("summary", "done"), unsafe_allow_html=True)

            st.session_state.pipeline_steps["extract"] = "active"
            if "extract" in step_slots:
                step_slots["extract"].markdown(_step_html("extract", "active"), unsafe_allow_html=True)
            action_items = extract_action_items(transcript)
            decisions    = extract_key_decisions(transcript)
            questions    = extract_questions(transcript)
            st.session_state.pipeline_steps["extract"] = "done"
            if "extract" in step_slots:
                step_slots["extract"].markdown(_step_html("extract", "done"), unsafe_allow_html=True)

            st.session_state.pipeline_steps["rag"] = "active"
            if "rag" in step_slots:
                step_slots["rag"].markdown(_step_html("rag", "active"), unsafe_allow_html=True)
            rag_chain = build_rag_chain(transcript)
            st.session_state.pipeline_steps["rag"] = "done"
            if "rag" in step_slots:
                step_slots["rag"].markdown(_step_html("rag", "done"), unsafe_allow_html=True)

            st.session_state.result = {
                "title":        title,
                "transcript":   transcript,
                "summary":      summary,
                "action_items": action_items,
                "key_decisions":decisions,
                "open_questions":questions,
                "rag_chain":    rag_chain,
            }
            st.session_state.pipeline_done = True
            progress_ph.success("✅ Analysis complete!")
            time.sleep(0.8)
            progress_ph.empty()
            st.rerun()

        except Exception as e:
            for k in ["audio","transcript","title","summary","extract","rag"]:
                if st.session_state.pipeline_steps.get(k) == "active":
                    st.session_state.pipeline_steps[k] = "pending"
                    if k in step_slots:
                        step_slots[k].markdown(_step_html(k, "pending"), unsafe_allow_html=True)
            progress_ph.error(f"❌ Error: {e}")

# ── Results ───────────────────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result

    st.markdown(f"""
    <div class="card">
        <div class="card-title">📌 Session Title</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:700;color:var(--text)">
            {r['title']}
        </div>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2], gap="medium")
    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📋 Summary</div>
            <div class="card-content">{r['summary']}</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        with st.expander("📝 Full Transcript", expanded=False):
            st.markdown(f'<div class="transcript-box">{r["transcript"]}</div>', unsafe_allow_html=True)
            st.download_button("⬇ Download transcript", data=r["transcript"],
                file_name=f"{r['title'].replace(' ','_')}.txt", mime="text/plain")

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">✅ Action Items</div>
            <div class="card-content">{r['action_items']}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">🔑 Key Decisions</div>
            <div class="card-content">{r['key_decisions']}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">❓ Open Questions</div>
            <div class="card-content">{r['open_questions']}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── RAG Chat ──────────────────────────────────────────────────────────────
    st.markdown('<div style="font-family:\'Syne\',sans-serif;font-size:1.2rem;font-weight:700;margin-bottom:1rem;color:var(--text)">💬 Chat with your Meeting</div>', unsafe_allow_html=True)

    if st.session_state.chat_history:
        chat_html = '<div class="chat-container">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                content = msg["content"].replace("<","&lt;").replace(">","&gt;")
                chat_html += f'<div class="chat-msg" style="align-items:flex-end"><span class="chat-label user-label">You</span><div class="chat-bubble user-bubble">{content}</div></div>'
            else:
                content = msg["content"].replace("<","&lt;").replace(">","&gt;")
                chat_html += f'<div class="chat-msg" style="align-items:flex-start"><span class="chat-label bot-label">🤖 Assistant</span><div class="chat-bubble bot-bubble">{content}</div></div>'
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">💬</div>
            <div style="color:var(--text-muted);font-size:0.85rem">Ask anything about your meeting transcript</div>
        </div>""", unsafe_allow_html=True)

    # Chat input row
    chat_col, send_col = st.columns([5, 1], gap="small")
    with chat_col:
        user_input = st.text_input("Ask a question", placeholder="What were the main decisions made?", label_visibility="hidden")
    with send_col:
        send_btn = st.button("Send →", use_container_width=True)

    if send_btn and user_input and user_input.strip():
        from core.rag_engine import ask_question
        with st.spinner("Thinking…"):
            answer = ask_question(r["rag_chain"], user_input.strip())
        st.session_state.chat_history.append({"role": "user",      "content": user_input.strip()})
        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat"):
            st.session_state.chat_history = []
            st.rerun()

else:
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5rem 2rem;text-align:center">
        <div style="font-size:4rem;margin-bottom:1rem">🎬</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:700;color:var(--text);margin-bottom:0.5rem">
            Ready to Analyse
        </div>
        <div style="color:var(--text-muted);font-size:0.85rem;max-width:380px;line-height:1.7">
            Paste a YouTube URL or upload a file in the sidebar, choose your language, and hit <strong style="color:var(--accent-glow)">Analyse</strong>.
        </div>
        <div style="margin-top:2rem;display:flex;gap:1rem;flex-wrap:wrap;justify-content:center">
            <span class="badge badge-purple">Transcription</span>
            <span class="badge badge-cyan">Summarisation</span>
            <span class="badge badge-green">RAG Chat</span>
        </div>
    </div>""", unsafe_allow_html=True)