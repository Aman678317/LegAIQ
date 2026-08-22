"""Deep Research Playground — a small Streamlit starter for the OpenAI Deep Research API.

Flow: type a research question, hit Run, and watch three live views:

  1. Activity feed  — what the model is doing (reasoning, web searches, citations).
  2. Report         — the final report streaming in as markdown.
  3. Raw events     — every Responses API event, inspectable and downloadable.

Everything interesting happens in `run_research()` at the bottom of this file.
Start extending there (extra tools, background mode, prompt rewriting, …).

Docs: https://developers.openai.com/api/docs/guides/deep-research
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
from openai import OpenAI

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

PAGE_TITLE = "Deep Research Playground"

MODELS = [
    "o4-mini-deep-research",  # cheaper and faster — good default for experiments
    "o3-deep-research",       # the heavier model
]

# Deep Research models require at least one data source. `web_search` is the
# simplest one; swap in file_search, code_interpreter, or remote MCP servers
# here when you want to extend the playground.
RESEARCH_TOOLS = [{"type": "web_search"}]

EXAMPLES = [
    "What are the most important developments in renewable energy storage since 2024? Cite reliable sources.",
    "Compare how the EU, US, and India regulate AI in hiring decisions. Include the current status of each framework.",
    "Summarize recent case law on employee non-compete agreements in India, with citations.",
]

TERMINAL_EVENTS = {"response.completed", "response.failed", "response.incomplete", "response.error"}

REFRESH_EVERY_SECONDS = 0.2  # throttle live UI updates so long runs stay smooth
RAW_TAIL_LINES = 12          # how many recent events to show in the live raw feed


# --------------------------------------------------------------------------- #
# Tiny .env loader (avoids a python-dotenv dependency for a starter project)
# --------------------------------------------------------------------------- #

def load_local_env(path: Path | None = None) -> None:
    path = path or Path(__file__).parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_local_env()


# --------------------------------------------------------------------------- #
# Pure helpers — no Streamlit here, so they are easy to test and reuse
# --------------------------------------------------------------------------- #

def event_to_dict(event: Any) -> dict[str, Any]:
    """Turn an SDK streaming event into a JSON-safe dictionary."""
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if isinstance(event, dict):
        return event
    return {"type": "unknown", "value": str(event)}


def truncate(text: str, limit: int = 160) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def fmt_elapsed(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m {secs:02d}s" if minutes else f"{secs}s"


def preview(payload: dict[str, Any], limit: int = 500) -> str:
    """Compact one-line JSON preview of an event for the raw feed."""
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[:limit] + " …"


def extract_citation(annotation: dict[str, Any]) -> dict[str, str] | None:
    """Keep only url citations (Deep Research reports cite web sources)."""
    url = annotation.get("url")
    if not url:
        return None
    return {"title": annotation.get("title") or url, "url": url}


def collect_citations(events: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Deduplicate citations by URL, preserving first-seen order."""
    seen: set[str] = set()
    citations: list[dict[str, str]] = []
    for payload in events:
        if payload.get("type") != "response.output_text.annotation.added":
            continue
        citation = extract_citation(payload.get("annotation") or {})
        if citation and citation["url"] not in seen:
            seen.add(citation["url"])
            citations.append(citation)
    return citations


def count_searches(events: list[dict[str, Any]]) -> int:
    return sum(1 for e in events if e.get("type") == "response.web_search_call.completed")


def feed_line(payload: dict[str, Any]) -> str | None:
    """Map an event to one human-readable activity line, or None to skip it."""
    kind = payload.get("type", "")

    if kind == "response.reasoning_summary_text.done":
        text = (payload.get("text") or "").strip()
        return f"🧠 &nbsp;{truncate(text)}" if text else None

    if kind == "response.web_search_call.completed":
        return "🔎 &nbsp;Web search finished"

    if kind == "response.output_item.added":
        item_type = (payload.get("item") or {}).get("type")
        if item_type == "code_interpreter_call":
            return "🐍 &nbsp;Running code interpreter…"

    if kind == "response.output_text.annotation.added":
        citation = extract_citation(payload.get("annotation") or {})
        if citation:
            return f"🔗 &nbsp;Citing [{truncate(citation['title'], 70)}]({citation['url']})"

    if kind == "response.completed":
        return "✅ &nbsp;Response completed"
    if kind == "response.failed":
        return "❌ &nbsp;Response failed"
    if kind == "response.incomplete":
        return "⚠️ &nbsp;Response incomplete (output token limit reached)"

    return None


def usage_text(result: "RunResult") -> str:
    usage = result.usage or {}
    input_tokens = usage.get("input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    if not (input_tokens or output_tokens):
        return "—"
    return f"{input_tokens:,} in · {output_tokens:,} out"


@dataclass
class RunResult:
    """Everything captured from one research run."""

    question: str
    model: str
    report: str = ""
    events: list[dict[str, Any]] = field(default_factory=list)
    citations: list[dict[str, str]] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    error: str | None = None
    elapsed: float = 0.0


# --------------------------------------------------------------------------- #
# The streaming runner — the heart of the playground
# --------------------------------------------------------------------------- #

def run_research(question: str, model: str, max_tool_calls: int = 0) -> RunResult:
    """Stream one Deep Research request, updating the live views as events arrive."""
    client = OpenAI(timeout=3600)  # deep research runs can take many minutes
    result = RunResult(question=question, model=model)

    started = time.monotonic()
    last_refresh = 0.0
    feed_lines: list[str] = []

    status = st.status("Starting Deep Research…", expanded=True)
    progress_line = status.empty()
    feed_box = status.container(height=220).empty()
    status.write("")  # small spacer so the status box doesn't jump on first event

    report_header = st.subheader("Report")
    report_box = st.empty()
    tail_expander = st.expander(f"Raw event stream (last {RAW_TAIL_LINES})", expanded=False)
    tail_box = tail_expander.empty()

    def refresh(force: bool = False) -> None:
        nonlocal last_refresh
        now = time.monotonic()
        if not force and now - last_refresh < REFRESH_EVERY_SECONDS:
            return
        last_refresh = now
        progress_line.markdown(
            f"`{fmt_elapsed(now - started)}` · {len(result.events)} events · "
            f"{count_searches(result.events)} web searches · "
            f"{len(result.citations)} citations"
        )
        feed_box.markdown("\n\n".join(feed_lines[-40:]) or "_Waiting for events…_")
        report_box.markdown((result.report + " ▌") if result.report else "_Report will stream in here…_")
        tail_box.code(
            "\n".join(
                f"#{i} {preview(e)}" for i, e in enumerate(result.events[-RAW_TAIL_LINES:], start=max(1, len(result.events) - RAW_TAIL_LINES + 1))
            )
            or "—",
            language="json",
        )

    try:
        request_kwargs: dict[str, Any] = {
            "model": model,
            "input": question,
            "tools": RESEARCH_TOOLS,
            "stream": True,
        }
        if max_tool_calls > 0:
            request_kwargs["max_tool_calls"] = max_tool_calls

        stream = client.responses.create(**request_kwargs)

        for event in stream:
            payload = event_to_dict(event)
            result.events.append(payload)
            kind = payload.get("type", "")

            if kind == "response.output_text.delta":
                result.report += payload.get("delta", "")

            elif kind == "response.output_text.annotation.added":
                citation = extract_citation(payload.get("annotation") or {})
                if citation:
                    result.citations.append(citation)

            elif kind == "response.completed":
                response = payload.get("response") or {}
                result.usage = response.get("usage")
                # Harvest citations from the final message too, in case any
                # annotation arrived only in the completed payload.
                for item in response.get("output", []):
                    for part in item.get("content", []):
                        for annotation in part.get("annotations", []):
                            citation = extract_citation(annotation)
                            if citation and all(c["url"] != citation["url"] for c in result.citations):
                                result.citations.append(citation)

            elif kind == "response.failed":
                result.error = ((payload.get("response") or {}).get("error") or {}).get("message") or "Request failed."

            elif kind == "response.error":
                result.error = payload.get("message") or payload.get("code") or "Stream error."

            line = feed_line(payload)
            if line:
                feed_lines.append(line)

            refresh(force=kind in TERMINAL_EVENTS)

        result.elapsed = time.monotonic() - started
        report_box.markdown(result.report or "_The response completed without any report text._")

        if result.error:
            status.update(label="Research failed", state="error", expanded=True)
            st.error(f"{result.error}  \n_(Full details in the raw events below — the failing event is usually the last one.)_")
        else:
            status.update(label=f"Research complete in {fmt_elapsed(result.elapsed)}", state="complete", expanded=False)

    except Exception as exc:  # noqa: BLE001 — a playground should surface every failure
        result.elapsed = time.monotonic() - started
        result.error = str(exc)
        status.update(label="Research failed", state="error", expanded=True)
        st.exception(exc)

    return result


# --------------------------------------------------------------------------- #
# UI
# --------------------------------------------------------------------------- #

def render_sidebar() -> tuple[str, int]:
    with st.sidebar:
        st.header("Settings")

        model = st.selectbox("Research model", MODELS, help="o4-mini is cheaper and faster; o3 goes deeper.")

        max_tool_calls = st.number_input(
            "Max tool calls (cost cap)",
            min_value=0,
            max_value=200,
            value=0,
            step=5,
            help="Deep Research can make many web searches. Set 0 for no cap, or e.g. 25 to bound cost and latency.",
        )

        st.divider()
        if os.getenv("OPENAI_API_KEY"):
            st.success("OPENAI_API_KEY detected")
        else:
            st.warning("Set OPENAI_API_KEY in `.env` or your environment, then restart Streamlit.")

        with st.expander("Example questions"):
            for example in EXAMPLES:
                if st.button(truncate(example, 58), key=f"example:{example}", use_container_width=True):
                    st.session_state["question_input"] = example
                    st.rerun()

        st.divider()
        st.caption(
            "Deep Research browses the web and can take **5–30 minutes** for hard questions. "
            "The mini model is usually faster. See the "
            "[Deep Research guide](https://developers.openai.com/api/docs/guides/deep-research) for details."
        )

    return model, int(max_tool_calls)


def render_results(result: RunResult) -> None:
    searches = count_searches(result.events)

    st.divider()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Elapsed", fmt_elapsed(result.elapsed))
    col2.metric("Events", len(result.events))
    col3.metric("Web searches", searches)
    col4.metric("Citations", len(result.citations))
    col5.metric("Tokens", usage_text(result), help="Input · output tokens reported by the API.")

    report_tab, sources_tab, raw_tab = st.tabs(["📄 Report", "🔗 Sources", "🌊 Raw events"])

    with report_tab:
        if result.report:
            st.markdown(result.report)
            st.download_button(
                "Download report (.md)",
                data=result.report,
                file_name=f"deep-research-report-{datetime.now():%Y%m%d-%H%M%S}.md",
                mime="text/markdown",
            )
        else:
            st.warning(f"No report text was produced.{' Error: ' + result.error if result.error else ''}")

    with sources_tab:
        st.caption("URL citations attached to the report text, in first-seen order.")
        if result.citations:
            for i, citation in enumerate(result.citations, start=1):
                st.markdown(f"{i}. [{citation['title']}]({citation['url']})")
        else:
            st.info("No citations were returned for this run.")

    with raw_tab:
        st.caption("Every Responses API event from this run. Pick one to inspect its full payload.")

        available_types = sorted({e.get("type", "unknown") for e in result.events})
        chosen_types = st.multiselect("Filter by event type", available_types, default=available_types)
        filtered = [e for e in result.events if e.get("type", "unknown") in chosen_types]

        if not filtered:
            st.info("No events match the filter.")
        else:
            labels = [f"{i}. {e.get('type', 'unknown')}" for i, e in enumerate(filtered)]
            selected = st.selectbox(f"Inspect an event ({len(filtered)} shown)", range(len(labels)), format_func=labels.__getitem__)
            st.json(filtered[selected], expanded=4)

        st.download_button(
            "Download all events (.json)",
            data=json.dumps(result.events, indent=2, ensure_ascii=False, default=str),
            file_name=f"deep-research-events-{datetime.now():%Y%m%d-%H%M%S}.json",
            mime="application/json",
        )


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="🔎", layout="wide")
    st.title("🔎 Deep Research Playground")
    st.caption("A small, inspectable starter app for the OpenAI Deep Research API (Responses API, streamed).")

    model, max_tool_calls = render_sidebar()

    question = st.text_area(
        "Research question",
        key="question_input",
        height=140,
        placeholder="Ask a focused question and describe the evidence or sources you want cited.",
    )

    run_col, clear_col = st.columns([3, 1])
    with run_col:
        run_clicked = st.button("Run research", type="primary", use_container_width=True)
    with clear_col:
        clear_clicked = st.button("Clear results", use_container_width=True)
        if clear_clicked:
            st.session_state.pop("result", None)
            st.rerun()

    if run_clicked:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("No API key found. Put `OPENAI_API_KEY=...` in `.env` (see `.env.example`) or export it, then rerun.")
        elif not question.strip():
            st.warning("Enter a research question first.")
        else:
            st.session_state["result"] = run_research(question.strip(), model, max_tool_calls)

    result = st.session_state.get("result")
    if result:
        render_results(result)
    elif not run_clicked:
        st.info("Paste a research question above and hit **Run research**. Results, sources, and raw API events will appear here.")


if __name__ == "__main__":
    main()
