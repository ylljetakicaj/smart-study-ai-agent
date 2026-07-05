"""
main.py — Smart Study AI Agent Streamlit frontend.

Run:
    streamlit run app/main.py
"""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.adk")

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from app.agents import StudySession
from app.retriever import extract_text
from app.quiz_generator import QuizGenerator
from app.planner import StudyPlanner


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Smart Study AI",
    page_icon="assets/icon.png" if False else "📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global styles
# ---------------------------------------------------------------------------
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
    /* ── Base ── */
    [data-testid="stAppViewContainer"] {
        background: #f8f9fb;
    }
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e8eaed;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-size: 0.85rem;
        color: #5f6368;
    }

    /* ── Header ── */
    .app-header {
        padding: 1.5rem 0 1rem 0;
        border-bottom: 1px solid #e8eaed;
        margin-bottom: 1.5rem;
    }
    .app-header h1 {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .app-header p {
        color: #5f6368;
        margin: 0.25rem 0 0 0;
        font-size: 0.9rem;
    }

    /* ── Tabs ── */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 2px solid #e8eaed;
        background: transparent;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        font-size: 0.875rem;
        font-weight: 500;
        color: #5f6368;
        padding: 0.6rem 1.2rem;
        border-radius: 0;
        background: transparent;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
    }
    [data-testid="stTabs"] [aria-selected="true"] {
        color: #1a73e8 !important;
        border-bottom: 2px solid #1a73e8 !important;
        background: transparent !important;
    }

    /* ── Cards ── */
    .card {
        background: #ffffff;
        border: 1px solid #e8eaed;
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }
    .card-question {
        background: #ffffff;
        border: 1px solid #e8eaed;
        border-radius: 10px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }

    /* ── Section headings ── */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-title i {
        color: #1a73e8;
        font-size: 1rem;
    }

    /* ── Upload area ── */
    .upload-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #5f6368;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    .doc-badge {
        background: #e8f0fe;
        color: #1a73e8;
        border-radius: 6px;
        padding: 0.35rem 0.75rem;
        font-size: 0.8rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        margin-top: 0.5rem;
    }

    /* ── Chat bubbles ── */
    [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
    }

    /* ── Progress bars ── */
    .stProgress > div > div {
        background: #1a73e8;
    }

    /* ── Buttons ── */
    [data-testid="stButton"] button[kind="primary"] {
        background: #1a73e8;
        border: none;
        border-radius: 6px;
        font-weight: 500;
        letter-spacing: 0.2px;
    }
    [data-testid="stButton"] button[kind="primary"]:hover {
        background: #1557b0;
    }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        border: 1px solid #e8eaed !important;
        border-radius: 8px !important;
        margin-bottom: 0.5rem;
    }

    /* hide Streamlit branding */
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="app-header">
    <h1><i class="fa-solid fa-brain" style="color:#1a73e8;margin-right:0.5rem;"></i>Smart Study AI</h1>
    <p>Upload your lecture notes — summarize, quiz, plan, and track your progress.</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session bootstrap
# ---------------------------------------------------------------------------
if "session" not in st.session_state:
    try:
        st.session_state.session = StudySession()
        st.session_state.init_error = None
    except RuntimeError as exc:
        st.session_state.session = None
        st.session_state.init_error = str(exc)

if st.session_state.init_error:
    st.error(st.session_state.init_error)
    st.info("Add your Gemini API key to the `.env` file and restart the app.")
    st.stop()

session: StudySession = st.session_state.session

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<p class="upload-label">Document</p>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Upload notes",
        type=["pdf", "pptx", "txt"],
        key="uploaded_file",
        label_visibility="collapsed",
    )
    if uploaded:
        with st.spinner("Reading..."):
            text = extract_text(uploaded)
        if text.strip():
            n = session.ingest_text(text, title=uploaded.name)
            st.success(f"Indexed {n} chunks")
        else:
            st.warning("Could not extract text from this file.")

    doc_title = session.memory.facts.get("current_document")
    if doc_title:
        st.markdown(
            f'<div class="doc-badge"><i class="fa-solid fa-file-lines"></i>{doc_title}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.caption("No document loaded yet.")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab_chat, tab_quiz, tab_flash, tab_plan, tab_progress = st.tabs(
    ["Chat", "Quiz", "Flashcards", "Study Plan", "Progress"]
)

# ---- Chat ------------------------------------------------------------------
with tab_chat:
    st.markdown('<div class="section-title"><i class="fa-regular fa-message"></i> Chat with your notes</div>', unsafe_allow_html=True)

    if "chat_log" not in st.session_state:
        st.session_state.chat_log = []

    for role, msg in st.session_state.chat_log:
        with st.chat_message(role):
            st.markdown(msg)

    if prompt := st.chat_input("Ask a question about your notes…"):
        st.session_state.chat_log.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                reply = session.chat(prompt)
            st.markdown(reply)
        st.session_state.chat_log.append(("assistant", reply))

# ---- Quiz ------------------------------------------------------------------
with tab_quiz:
    st.markdown('<div class="section-title"><i class="fa-solid fa-circle-check"></i> Practice Quiz</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    n_q = col1.slider("Questions", 3, 10, 5)
    diff = col2.selectbox("Difficulty", ["easy", "medium", "hard"], index=1)

    if st.button("Generate Quiz", type="primary", disabled=session.retriever.is_empty):
        with st.spinner("Building quiz…"):
            try:
                st.session_state.quiz = session.tools.make_quiz(n=n_q, difficulty=diff)
                st.session_state.quiz_answers = {}
            except Exception as exc:
                st.error(str(exc))
                st.session_state.quiz = None
    elif session.retriever.is_empty:
        st.info("Upload lecture notes first.")

    quiz = st.session_state.get("quiz")
    if quiz and len(quiz):
        for i, q in enumerate(quiz.questions):
            with st.container():
                st.markdown(f'<div class="card-question"><strong>Q{i+1}.</strong> {q.question}</div>', unsafe_allow_html=True)
                st.radio(
                    f"q{i}",
                    options=list(q.options.keys()),
                    format_func=lambda k, q=q: f"{k}.  {q.options[k]}",
                    key=f"q_{i}",
                    index=None,
                    label_visibility="collapsed",
                )

        if st.button("Submit Answers", type="primary"):
            answers = {i: st.session_state.get(f"q_{i}", "") for i in range(len(quiz.questions))}
            result = QuizGenerator.grade(quiz, answers)
            st.success(f"Score: {result['score']} / {result['total']}")
            session.tools.record_quiz_result(result["per_topic"])
            with st.expander("Review answers"):
                for i, q in enumerate(quiz.questions):
                    chosen = answers.get(i, "—")
                    icon = "✓" if chosen == q.answer else "✗"
                    color = "#34a853" if chosen == q.answer else "#ea4335"
                    st.markdown(
                        f"<span style='color:{color};font-weight:600'>{icon}</span> "
                        f"**Q{i+1}:** {q.question}  \n"
                        f"Your answer: **{chosen}** · Correct: **{q.answer}**  \n"
                        f"<span style='color:#5f6368;font-size:0.85rem'>{q.explanation}</span>",
                        unsafe_allow_html=True,
                    )

# ---- Flashcards ------------------------------------------------------------
with tab_flash:
    st.markdown('<div class="section-title"><i class="fa-solid fa-layer-group"></i> Flashcards</div>', unsafe_allow_html=True)

    n_cards = st.slider("Number of cards", 4, 20, 8)
    if st.button("Generate Flashcards", type="primary", disabled=session.retriever.is_empty):
        with st.spinner("Creating cards…"):
            try:
                st.session_state.flashcards = session.tools.make_flashcards(n=n_cards)
            except Exception as exc:
                st.error(str(exc))
                st.session_state.flashcards = None
    elif session.retriever.is_empty:
        st.info("Upload lecture notes first.")

    deck = st.session_state.get("flashcards")
    if deck and deck.cards:
        cols = st.columns(2)
        for i, card in enumerate(deck.cards):
            with cols[i % 2]:
                with st.expander(card.front):
                    st.markdown(card.back)
                    if card.topic:
                        st.caption(card.topic)

# ---- Study Plan ------------------------------------------------------------
with tab_plan:
    st.markdown('<div class="section-title"><i class="fa-regular fa-calendar"></i> Study Plan</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    weeks = col1.slider("Weeks until exam", 1, 8, 4)
    hours = col2.slider("Hours per week", 2, 20, 8)
    topics_input = st.text_input(
        "Topics (comma-separated, or leave blank to use progress data)",
        placeholder="e.g. Neural Networks, Backpropagation, CNNs",
    )

    if st.button("Build Study Plan", type="primary"):
        topics = [t.strip() for t in topics_input.split(",") if t.strip()] or None
        with st.spinner("Building plan…"):
            try:
                plan = session.tools.make_study_plan(topics=topics, weeks=weeks)
                st.session_state.study_plan = plan
            except Exception as exc:
                st.error(str(exc))
                st.session_state.study_plan = None

    plan = st.session_state.get("study_plan")
    if plan and plan.weeks:
        for w in plan.weeks:
            with st.expander(f"Week {w.week} — {w.theme}"):
                for task in w.tasks:
                    st.markdown(f"- {task}")
                st.markdown(f"**Self-test:** {w.self_test}")

    st.divider()
    st.markdown('<div class="section-title"><i class="fa-solid fa-arrow-trend-up"></i> What to revise next</div>', unsafe_allow_html=True)
    if st.button("Get Recommendations", type="primary"):
        with st.spinner("Analysing progress…"):
            recs = session.tools.recommend_next()
        st.markdown(recs)

# ---- Progress --------------------------------------------------------------
with tab_progress:
    st.markdown('<div class="section-title"><i class="fa-solid fa-chart-bar"></i> Your Progress</div>', unsafe_allow_html=True)

    progress = session.tools.get_progress()
    if progress:
        for topic, data in progress.items():
            mastery = data.get("mastery", 0.0)
            col1, col2 = st.columns([3, 1])
            col1.markdown(f"**{topic}**")
            col2.markdown(f"<span style='color:#1a73e8;font-weight:600'>{mastery:.0%}</span>", unsafe_allow_html=True)
            st.progress(mastery)
    else:
        st.info("Complete a quiz to start tracking your progress by topic.")
