# Frontend

The primary user interface is a **Streamlit** app defined in [`../app/main.py`](../app/main.py).

This folder is reserved for optional front-end assets:

- `assets/` — logos, screenshots, and custom images used by the UI.
- `styles/` — custom CSS injected via `st.markdown(..., unsafe_allow_html=True)`.
- Future work: a React/Next.js SPA that talks to the agent over a FastAPI
  backend (see "Future Improvements" in the root README).

To launch the current UI:

```bash
streamlit run app/main.py
```
