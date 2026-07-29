from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    ARTIFACTS_DIR,
    ROOT,
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

TRANSCRIPTS_DIR = ROOT / "transcripts"


st.set_page_config(page_title="Day04 Research Agent", page_icon="🔎", layout="wide")

with st.sidebar:
    st.header("Cấu hình")
    provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"], index=0)
    version = st.text_input("Version label", value="v3")
    history_window = st.slider("History window (cặp turn)", 0, 10, 5)
    max_tool_rounds = st.slider("Max tool rounds", 1, 8, 4)

    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    artifact_version = build_artifact_version(version, system_prompt_path, tools_path)
    st.caption("Artifact version")
    st.code(artifact_version.artifact_version, language=None)

    if st.button("🗑️ Xóa hội thoại"):
        for key in ("history", "turns", "transcript_id"):
            st.session_state.pop(key, None)
        st.rerun()

st.title("🔎 Research Agent — Day04 G03")
st.caption("UI tái sử dụng `run_model_tool_loop` từ chat.py — cùng agent loop với CLI và eval.")

if "history" not in st.session_state:
    st.session_state.history = []  # [{role, content}]
if "turns" not in st.session_state:
    st.session_state.turns = []  # full turn records for display + transcript
if "transcript_id" not in st.session_state:
    st.session_state.transcript_id = "_".join([
        safe_slug(version),
        safe_slug(provider_name),
        datetime.now().strftime("%Y%m%dT%H%M%S%f"),
    ])


def render_turn(turn: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.write(turn["user"])
    with st.chat_message("assistant"):
        if turn.get("status") == "provider_error":
            st.error(turn.get("error"))
            return
        st.write(turn.get("assistant_text") or "")
        rounds = turn.get("rounds") or []
        tool_rounds = [r for r in rounds if r.get("tool_calls")]
        if tool_rounds:
            with st.expander(f"🔧 Tool trace ({sum(len(r['tool_calls']) for r in tool_rounds)} call)"):
                for round_record in rounds:
                    for event in round_record.get("tool_results", []):
                        result = event.get("result", {})
                        has_error = isinstance(result, dict) and result.get("error")
                        icon = "❌" if has_error else "✅"
                        st.markdown(
                            f"{icon} **round {round_record['round']}** — `{event['tool']}`"
                        )
                        st.code(json.dumps(event.get("args", {}), ensure_ascii=False, indent=2), language="json")
                        st.json(result, expanded=False)


for turn in st.session_state.turns:
    render_turn(turn)

user_text = st.chat_input("Nhập yêu cầu research...")
if user_text:
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(provider_name)

    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, history_window),
        {"role": "user", "content": user_text},
    ]

    turn_record: dict[str, Any] = {
        "turn_index": len(st.session_state.turns) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    with st.spinner("Agent đang xử lý..."):
        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=None,
                max_tool_rounds=max_tool_rounds,
            )
            turn_record.update(result)
            st.session_state.history.append({"role": "user", "content": user_text})
            st.session_state.history.append({"role": "assistant", "content": result["assistant_text"]})
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {str(exc)}",
            })

    turn_record["ended_at"] = now_iso()
    st.session_state.turns.append(turn_record)

    transcript = {
        "transcript_id": st.session_state.transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": None,
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": now_iso(),
        "turns": st.session_state.turns,
        "ui": "streamlit",
    }
    write_transcript(TRANSCRIPTS_DIR / f"{st.session_state.transcript_id}.transcript.json", transcript)
    st.rerun()

st.divider()
st.caption(
    f"Transcript: transcripts/{st.session_state.transcript_id}.transcript.json — "
    f"provider={provider_name} — version={version}"
)
