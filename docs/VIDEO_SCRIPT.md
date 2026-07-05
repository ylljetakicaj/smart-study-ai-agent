# 🎬 Smart Study AI Agent — 5-Minute Demo Script

*Target runtime: ~5:00. Timings are cumulative. Screen actions are in italics.*

---

## [0:00 – 0:35] · Problem

> "University students drown in material — dozens of lecture PDFs, slide decks,
> and readings per course. The hard part isn't a lack of information; it's
> turning that pile into *understanding*. Students waste hours re-reading,
> making flashcards by hand, and guessing what to revise before an exam.
>
> What if an AI agent could read your notes, quiz you, plan your week, and
> actually *remember* how you're doing — adapting as you learn? That's the
> Smart Study AI Agent."

*Show a cluttered desktop of PDFs, then cut to the clean app landing page.*

---

## [0:35 – 1:15] · Solution

> "Smart Study AI is an autonomous study companion. You upload your lecture
> notes, and it can summarize them, answer questions grounded in *your*
> material, generate quizzes and flashcards, write exam-style questions, and
> build a personalized weekly study plan.
>
> The key word is *agent*. It doesn't just answer prompts — it decides which
> tool to use, reaches out to external sources when your notes fall short, and
> keeps a memory of your progress so every plan gets smarter."

*Pan across the five tabs: Chat, Quiz, Flashcards, Study Plan, Progress.*

---

## [1:15 – 2:00] · Architecture

> "Under the hood, the user talks to a **Streamlit** interface. That feeds a
> **Study Agent built on Google's Agent Development Kit**, powered by the
> **Gemini** model. The agent routes each request to the right tool.
>
> There's a **retriever** that chunks and indexes your documents for grounded
> answers, a **memory** layer that persists both conversation and per-topic
> mastery, and dedicated generators for **quizzes**, **flashcards**, and
> **study plans**. Crucially, an **MCP server** exposes external tools —
> Wikipedia, arXiv, and a dictionary — so the agent can look beyond your notes
> when needed."

*Display the architecture diagram (`frontend/architecture.svg`), tracing the flow top to bottom.*

---

## [2:00 – 4:00] · Live Demo

**Upload (2:00 – 2:20)**
> "Let's upload a lecture PDF on neural networks."

*Drag a PDF into the sidebar. Show the 'Indexed into N chunks' confirmation.*

**Chat + grounding + MCP (2:20 – 2:55)**
> "I'll ask a question about the notes."

*Type: "Explain backpropagation using my notes."* — show the grounded answer.

> "Now something not in my notes — watch it reach out through the MCP server."

*Type: "Find recent arXiv papers on attention mechanisms."* — show external results.

**Quiz + progress feedback (2:55 – 3:25)**
> "Let's test ourselves."

*Go to the Quiz tab, generate 5 questions, answer them, hit Submit. Show the
score and per-question explanations.*

> "Notice my answers just updated the progress model behind the scenes."

**Flashcards (3:25 – 3:40)**
*Flip through two auto-generated flashcards on the Flashcards tab.*

**Study plan + adaptation (3:40 – 4:00)**
> "Because it tracked my weak topics from the quiz, the study plan now front-loads
> exactly what I struggled with."

*Generate a 4-week plan; expand Week 1 to show weak topics prioritized.*

---

## [4:00 – 4:40] · Course Concepts Used

> "This project puts the AI Agents course into practice:
> - **Agent architecture** with Google ADK and an LLM that plans and acts.
> - **Tool calling** — every capability is a documented function the agent invokes.
> - **MCP integration** for external tools over a standard protocol.
> - **Memory** for conversation and a persistent learning model.
> - **Retrieval-augmented generation** to keep answers grounded.
> - **Structured prompts** with JSON outputs for reliable parsing.
> - And an **adaptive feedback loop** where quiz results reshape future plans."

*Overlay a checklist of these concepts as you name them.*

---

## [4:40 – 5:00] · Conclusion

> "The Smart Study AI Agent turns a pile of lecture notes into an active,
> adaptive tutor — one that remembers you, tests you, and plans your path to
> exam day. It's modular, production-ready, and easy to extend with new tools
> or models.
>
> Thanks for watching — the full code and documentation are in the repository."

*End on the GitHub repo page / README.*
