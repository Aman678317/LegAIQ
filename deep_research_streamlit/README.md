# Deep Research Streamlit Playground

A deliberately small Streamlit app for experimenting with **OpenAI Deep Research**
(`o3-deep-research` / `o4-mini-deep-research` via the Responses API, streamed).

Paste a research question, hit **Run research**, and watch three live views:

1. **Activity feed** — reasoning summaries, finished web searches, and citations as they happen.
2. **Report** — the final report streaming in as markdown, with a download button.
3. **Raw events** — every Responses API streaming event, filterable by type,
   inspectable as JSON, and downloadable for offline study.

## Run locally

From this directory (Python 3.13 is already set up in `.venv`):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env   # then put your real key in .env
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app also reads `OPENAI_API_KEY` from your environment if you prefer.
The active Python 3.14 installation has an incompatible Streamlit/protobuf
combination — use the bundled `.venv` (3.13).

## What to explore

- Switch models in the sidebar (`o4-mini-deep-research` is the default).
- Set **Max tool calls** to cap how many web searches a run may make (cost/latency control).
- Try the example questions in the sidebar, or paste your own brief.
- After a run, filter raw events by type (e.g. only `response.output_text.delta`)
  to understand the streaming protocol.
- The Usage metric shows input/output tokens reported by the API.

## Extending it

Everything interesting lives in `run_research()` in `app.py`:

- Add data sources in `RESEARCH_TOOLS` (file search, code interpreter, remote MCP).
- Switch to `background=True` + polling for very long runs (see the
  [Deep Research guide](https://developers.openai.com/api/docs/guides/deep-research)).
- Add a prompt-rewriting step with a small fast model before the research call.

The pure helpers (`event_to_dict`, `feed_line`, `collect_citations`, …) have no
Streamlit dependency, so you can unit-test or reuse them easily.

Streaming reference: [streaming events](https://developers.openai.com/api/reference/resources/responses/streaming-events/).
