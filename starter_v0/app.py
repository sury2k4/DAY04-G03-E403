from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
RUNS_DIR = ROOT / "runs"
TRANSCRIPTS_DIR = ROOT / "transcripts"
SYSTEM_PROMPT_PATH = ARTIFACTS_DIR / "system_prompt.md"
TOOLS_PATH = ARTIFACTS_DIR / "tools.yaml"
CURRENT_VERSION = "v4"

load_lab_env(ROOT)


def new_transcript(provider_name: str, model: str | None) -> tuple[Path, dict[str, Any]]:
    artifact = build_artifact_version(CURRENT_VERSION, SYSTEM_PROMPT_PATH, TOOLS_PATH)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join(
        [safe_slug(CURRENT_VERSION), safe_slug(provider_name), timestamp]
    )
    path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact),
        "provider": provider_name,
        "model": model,
        "system_prompt": str(SYSTEM_PROMPT_PATH),
        "tools": str(TOOLS_PATH),
        "history_window": 5,
        "max_tool_rounds": 4,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    write_transcript(path, transcript)
    return path, transcript


def load_historical_cases() -> dict[str, dict[str, dict[str, Any]]]:
    by_case: dict[str, dict[str, dict[str, Any]]] = {}
    for path in sorted(RUNS_DIR.glob("v[0-3]_B_base_*.json")):
        run = json.loads(path.read_text(encoding="utf-8"))
        version = run.get("version", "")
        for item in run.get("results", []):
            by_case.setdefault(item["id"], {})[version] = {
                "artifact_version": run.get("artifact_version"),
                "run_id": run.get("run_id"),
                "request": item.get("input"),
                "passed": item.get("result", {}).get("passed"),
                "response": item.get("result", {}).get("actual_text"),
                "tool_calls": item.get("result", {}).get("actual_tool_calls", []),
                "failures": item.get("result", {}).get("failures", []),
            }
    return by_case


def show_rounds(rounds: list[dict[str, Any]]) -> None:
    for round_record in rounds:
        round_number = round_record.get("round")
        calls = round_record.get("tool_calls") or []
        results = round_record.get("tool_results") or []
        with st.expander(
            f"Round {round_number} · {len(calls)} tool call(s)",
            expanded=bool(calls),
        ):
            if round_record.get("assistant_text"):
                st.caption("Assistant intermediate response")
                st.write(round_record["assistant_text"])
            if not calls:
                st.info("No tool call in this round.")
            for index, call in enumerate(calls):
                event = results[index] if index < len(results) else {}
                result = event.get("result")
                has_error = isinstance(result, dict) and bool(result.get("error"))
                st.markdown(
                    f"**{call.get('name')}** — "
                    f"{'ERROR' if has_error else 'SUCCESS'}"
                )
                st.caption("Arguments")
                st.json(call.get("args") or {})
                st.caption("Result / error")
                st.json(result if result is not None else {"status": "not_executed"})


def render_trace_history() -> None:
    if not st.session_state.turns:
        st.info("Send a request to see request, response, rounds and tool traces.")
        return
    for turn in reversed(st.session_state.turns):
        with st.container(border=True):
            st.markdown(f"**Request:** {turn['user']}")
            st.markdown(f"**Final response:** {turn.get('assistant_text') or '—'}")
            st.caption(
                f"Status: {turn.get('status')} · "
                f"Transcript: {st.session_state.transcript['transcript_id']} · "
                f"Artifact: {st.session_state.transcript['artifact_version']}"
            )
            show_rounds(turn.get("rounds") or [])


def render_version_comparison() -> None:
    cases = load_historical_cases()
    if not cases:
        st.warning("No v0–v3 base runs found.")
        return
    case_id = st.selectbox("Scenario", sorted(cases))
    versions = cases[case_id]
    request = next(iter(versions.values())).get("request")
    st.markdown(f"**Same request:** {request}")
    columns = st.columns(4)
    for column, version in zip(columns, ("v0", "v1", "v2", "v3")):
        item = versions.get(version)
        with column:
            st.subheader(version)
            if not item:
                st.warning("No run")
                continue
            st.metric("Result", "PASS" if item["passed"] else "FAIL")
            st.caption(item["artifact_version"])
            st.write("Tool calls")
            st.json(item["tool_calls"])
            if item["failures"]:
                st.error("\n".join(item["failures"]))
            elif item["response"]:
                st.write(item["response"])
            st.caption(f"Run: {item['run_id']}")


st.set_page_config(page_title="Research Agent Evidence UI", page_icon="🔎", layout="wide")
st.title("🔎 Research Agent Evidence UI")
st.caption("Live agent chat, complete tool traces, transcripts and v0–v3 comparison.")

with st.sidebar:
    st.header("Run configuration")
    provider_name = st.selectbox(
        "Provider", ["openrouter", "openai", "anthropic", "gemini"]
    )
    model_text = st.text_input("Model override", value="")
    st.text_input("Version", value=CURRENT_VERSION, disabled=True)
    current_artifact = build_artifact_version(
        CURRENT_VERSION, SYSTEM_PROMPT_PATH, TOOLS_PATH
    )
    st.code(current_artifact.artifact_version)
    if st.button("Start new transcript", use_container_width=True):
        for key in ("transcript", "transcript_path", "turns", "history"):
            st.session_state.pop(key, None)
        st.rerun()

if "turns" not in st.session_state:
    st.session_state.turns = []
if "history" not in st.session_state:
    st.session_state.history = []
if "transcript" not in st.session_state:
    path, transcript = new_transcript(provider_name, model_text or None)
    st.session_state.transcript_path = path
    st.session_state.transcript = transcript

tab_chat, tab_trace, tab_compare = st.tabs(
    ["Live chat", "Evidence trace", "Compare v0–v3"]
)

with tab_chat:
    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_text = st.chat_input("Ask the research agent…")
    if user_text:
        with st.chat_message("user"):
            st.markdown(user_text)
        turn_record = {
            "turn_index": len(st.session_state.turns) + 1,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }
        try:
            provider = make_provider(provider_name)
            declarations = load_tool_declarations(TOOLS_PATH)
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_PATH.read_text(encoding="utf-8"),
                },
                *trim_history(st.session_state.history, 5),
                {"role": "user", "content": user_text},
            ]
            with st.spinner("Running model and tools…"):
                result = run_model_tool_loop(
                    provider=provider,
                    messages=messages,
                    tools=to_openai_tools(declarations),
                    model=model_text or None,
                    max_tool_rounds=4,
                )
            turn_record.update(result)
        except Exception as exc:
            turn_record.update(
                {
                    "status": "provider_error",
                    "assistant_text": "The provider request failed.",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        turn_record["ended_at"] = now_iso()
        st.session_state.turns.append(turn_record)
        st.session_state.history.extend(
            [
                {"role": "user", "content": user_text},
                {
                    "role": "assistant",
                    "content": turn_record.get("assistant_text") or "",
                },
            ]
        )
        st.session_state.transcript["turns"] = st.session_state.turns
        write_transcript(
            st.session_state.transcript_path, st.session_state.transcript
        )
        with st.chat_message("assistant"):
            st.markdown(turn_record.get("assistant_text") or "")
            if turn_record.get("error"):
                st.error(turn_record["error"])
        st.rerun()

with tab_trace:
    st.caption(f"Transcript file: {st.session_state.transcript_path}")
    render_trace_history()

with tab_compare:
    st.write(
        "Select one fixed scenario to inspect the request, calls, failures, run ID "
        "and artifact version across the four real historical runs."
    )
    render_version_comparison()
