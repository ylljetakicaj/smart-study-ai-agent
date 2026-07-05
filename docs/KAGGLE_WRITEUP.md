# Smart Study AI Agent — Kaggle Writeup

## Project Overview

The Smart Study AI Agent is an autonomous study companion for university
students. A student uploads their lecture notes — PDF, PowerPoint, or plain
text — and the agent becomes a personal tutor for that material. It summarizes
documents, answers questions grounded in the uploaded content, generates
multiple-choice quizzes and flashcards, writes exam-style questions, builds
personalized weekly study plans, explains difficult concepts at multiple depths,
tracks per-topic mastery, and recommends what to revise next. When a question
reaches beyond the uploaded notes, the agent draws on external tools —
Wikipedia, arXiv, and a dictionary — exposed through a Model Context Protocol
(MCP) server.

The system is built in Python around Google's Gemini model, orchestrated with
the Google Agent Development Kit (ADK), and presented through a clean Streamlit
interface with five tabs: Chat, Quiz, Flashcards, Study Plan, and Progress. It
is deliberately modular: each capability lives in its own module behind a small
interface, so components can be tested, replaced, or extended independently.

## Problem Statement

Students today are not short of information — they are overwhelmed by it. A
single course can generate dozens of lecture PDFs and slide decks, plus
supplementary readings. The bottleneck is converting that volume into durable
understanding. The manual workflow is slow and error-prone: re-reading notes
passively, hand-crafting flashcards, inventing practice questions, and guessing
which topics deserve attention before an exam. Generic chatbots help a little
but suffer three gaps. First, they are not grounded in the student's *own*
material, so answers drift from what will actually be examined. Second, they are
stateless — they forget what the student struggled with last session. Third,
they answer passively rather than acting: they will not proactively quiz, plan,
or adapt.

The Smart Study AI Agent targets exactly these gaps: grounding answers in
uploaded notes, remembering progress across sessions, and behaving as an active
agent that selects tools and adapts its output to the learner.

## Motivation

I wanted a capstone that was genuinely useful to me and my peers, not a toy.
Study support is a problem every student feels, which makes it a strong showcase
for agentic AI: it naturally requires retrieval (grounding in notes), memory
(tracking mastery), tool use (quizzes, plans, external lookups), and adaptive
reasoning (weighting weak topics). It also demonstrates a full feedback loop —
the hallmark of a real agent — where the output of one action (a quiz) changes
the behavior of a later action (the study plan). Building it end-to-end,
including a usable UI, made the course concepts concrete rather than abstract.

## Architecture

The request flow is layered:

**User → Streamlit → Study Agent (ADK) → Gemini → Tools/MCP → Response.**

The Streamlit UI captures uploads and user intent across its five tabs. It
constructs a single `StudySession` object (cached in session state) that owns
all durable state, guaranteeing a consistent view of memory and indexed
documents across Streamlit's frequent reruns.

The Study Agent is an ADK `LlmAgent` backed by Gemini. It interprets each
message and decides which tool to call rather than answering blindly. Two
categories of tools are registered: internal function tools (summarize, answer,
explain, plan, recommend) and an external `MCPToolset`. ADK derives each tool's
schema directly from the Python function's signature and docstring, which is why
the tool functions are so carefully documented — the documentation *is* the
contract.

Supporting the agent is a **tool layer** of specialized components:

- **Retriever** — extracts text from PDF/PPTX/TXT, chunks it into overlapping
  passages, and retrieves the most relevant chunks per query using TF-IDF cosine
  similarity. This provides retrieval-augmented generation (RAG) without a heavy
  vector-database dependency, while keeping a clean interface that could be
  swapped for Gemini embeddings later.
- **Memory** — two kinds. A conversation memory (a rolling window of turns) gives
  the agent continuity; a progress memory models per-topic mastery, attempts, and
  recency, updated from quiz results via an exponential moving average. Both are
  persisted to a JSON file so state survives restarts.
- **Quiz generator** — prompts Gemini for strict JSON, validates and repairs it,
  and grades attempts, returning per-topic results that feed back into memory.
- **Flashcard generator** — produces cards and attaches a simplified SM-2
  spaced-repetition scheduler, demonstrating applied learning science.
- **Planner** — builds a personalized weekly plan weighted toward weak or stale
  topics using the progress model, and provides both LLM-reasoned and
  deterministic revision recommendations.

The **MCP server** is a standalone process (built with the `mcp` SDK's FastMCP)
exposing `wiki_summary`, `arxiv_search`, and `web_define`. The ADK agent spawns
it over stdio and treats its tools like any other, demonstrating external tool
integration over a standard protocol.

## Implementation

The codebase is organized for clarity and testability. Every module depends only
on tiny interfaces — most importantly a single `GeminiLLM.generate(prompt) ->
str` method. Because generators and the planner accept any object with that
method, the LLM can be mocked, and I verified the entire non-LLM pipeline
(retrieval, chunking, grading, spaced repetition, priority ranking, persistence)
with lightweight tests that need no API key.

Prompts live in a single `prompts.py` module as structured templates following a
consistent ROLE / TASK / RULES / INPUT / OUTPUT shape. Generation tasks that must
be parsed (quizzes, flashcards, exams, plans) instruct the model to return only
JSON matching an explicit schema. Because LLMs occasionally wrap JSON in prose or
code fences, a small resilient parser strips fences and, if needed, extracts the
outermost `{...}` before parsing — so minor formatting drift does not break the
pipeline. Malformed items are skipped defensively rather than crashing a study
session.

The agent degrades gracefully. Chat first attempts the full ADK agent (which can
autonomously select internal tools and MCP tools); if ADK is unavailable in a
given environment, it falls back to the retrieval-augmented question-answering
tool so the app remains functional everywhere. This separation of "brain" (ADK)
from "hands" (plain Python tools) means the same tool code powers both the
conversational path and the explicit UI buttons, eliminating duplicated logic.

The adaptive loop is the implementation's centerpiece. When a student submits a
quiz, grading produces per-topic correctness. That result updates the mastery
model in memory, which is persisted immediately. The next time the student
generates a study plan or asks for revision priorities, the planner reads that
same model and allocates more time to low-mastery, long-untouched topics. One
action visibly changes a later one — the behavior that distinguishes an agent
from a prompt wrapper.

The Streamlit UI mirrors the capstone's required surface exactly: a sidebar for
the API key and file upload; a Chat tab with persistent history; a Quiz tab that
generates, grades, and explains; a Flashcards tab with flip and navigation; a
Study Plan tab with expandable weeks; and a Progress dashboard showing mastery
bars and prioritized revision recommendations.

## Technologies

- **Python** — the entire implementation.
- **Google Gemini** (`google-generativeai`) — the reasoning LLM, configured with
  a tutor persona as a system instruction; the API key is read from an
  environment variable and never hardcoded.
- **Google ADK** (`google-adk`) — the agent framework: `LlmAgent`,
  `FunctionTool`, `MCPToolset`, and the in-memory runner.
- **MCP** (`mcp` / FastMCP) — the external tool server, communicating over stdio.
- **pypdf** and **python-pptx** — document text extraction.
- **Streamlit** — the web UI.
- **Standard library only** for retrieval (TF-IDF), memory (JSON), and spaced
  repetition, keeping the project lightweight and reproducible.

## Challenges

The first challenge was **reliable structured output**. LLMs are probabilistic
and occasionally return JSON wrapped in prose or fences, or with a missing field.
I solved this with strict schema-constrained prompts plus a tolerant parser and
per-item validation, so a single malformed question never derails a quiz.

The second was **state under Streamlit's execution model**. Streamlit reruns the
whole script on every interaction, which naively would reset the retriever index
and memory on each click. Consolidating all durable state into one `StudySession`
cached in `st.session_state` fixed this and kept the mental model simple.

The third was **environment portability**. ADK and the MCP server add moving
parts that may not be present in every runtime. Designing the tools as plain
functions with a graceful chat fallback meant the core study features work with
only Gemini available, while the full agentic path activates when ADK is present.

The fourth was **keeping retrieval lightweight**. A vector database would have
added significant dependencies and setup friction for a single-student use case.
A transparent TF-IDF retriever with overlapping chunks gave good grounding for
lecture-sized corpora, behind an interface that leaves the door open to
embeddings later.

## Lessons Learned

I learned that **good tool design is mostly good documentation**. Because ADK
generates tool schemas from function signatures and docstrings, writing clear,
precise docstrings directly improved the agent's tool-selection accuracy. The
docstring is not a comment — it is the API the model reasons over.

I learned to **separate the brain from the hands**. Keeping the LLM/agent
orchestration distinct from pure-Python capability code made the system testable
without an API key, portable across environments, and free of duplicated logic
between chat and buttons.

I learned that **memory is what makes an agent feel intelligent**. The single
most compelling moment in the demo is when a study plan visibly reflects the
topics a student just failed. That adaptive loop, more than any individual
feature, is what elevates the project from a chatbot to an agent.

Finally, I learned the value of **defensive parsing and graceful degradation**.
Assuming the model or a dependency might misbehave — and handling it — is what
separates a demo that works once from software that works reliably.

## Future Work

Several extensions would deepen the system. **Vector retrieval** with Gemini
embeddings and a persistent store would scale grounding to large, multi-document
corpora with true semantic search. A **multi-agent design** — separate Tutor,
Examiner, and Planner sub-agents coordinated by a router — would let each
specialize and would showcase agent-to-agent orchestration. Replacing the JSON
memory file with a **database and user accounts** would support multiple students
and richer analytics. Additional **MCP tools** (Google Scholar, YouTube lecture
transcripts, Anki export) would broaden external reach. A **voice interface** and
a dedicated **React front-end** would improve accessibility and mobile use.
Finally, an **evaluation harness** measuring answer groundedness and quiz quality
would let the system be tuned and regression-tested systematically.

## Conclusion

The Smart Study AI Agent demonstrates a complete, modular agentic system:
grounded retrieval over a student's own notes, persistent memory of their
progress, structured tool calling, external integration through MCP, and an
adaptive feedback loop that turns assessment into personalized planning. It is
useful, extensible, and faithful to the AI Agents course — a study companion that
does not just answer, but remembers, tests, plans, and adapts.

*(Word count: ~1,180)*
