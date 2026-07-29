from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import ROOT, run_model_tool_loop
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
RUNS_DIR = ROOT / "runs"
load_lab_env(ROOT)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S%f")


def execute_scenario(user_text: str, provider_name: str, version: str, model: str | None) -> dict[str, Any]:
    prompt_path = ARTIFACTS_DIR / "system_prompt.md"
    tools_path = ARTIFACTS_DIR / "tools.yaml"
    system_prompt = prompt_path.read_text(encoding="utf-8")
    declarations = load_tool_declarations(tools_path)
    artifact_version = build_artifact_version(version, prompt_path, tools_path)
    provider = make_provider(provider_name)
    selected_model = model or getattr(provider, "default_model", None)
    result = run_model_tool_loop(
        provider=provider,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        tools=to_openai_tools(declarations),
        model=selected_model,
        max_tool_rounds=4,
    )
    run_id = f"ui_{version}_{provider_name}_{timestamp()}"
    record = {
        "run_id": run_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": selected_model,
        "input": user_text,
        **result,
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    run_path = RUNS_DIR / f"{run_id}.json"
    transcript_path = TRANSCRIPTS_DIR / f"{run_id}.transcript.json"
    serialized = json.dumps(record, ensure_ascii=False, indent=2, default=str)
    run_path.write_text(serialized, encoding="utf-8")
    transcript_path.write_text(
        json.dumps({
            "transcript_id": run_id,
            **artifact_version_dict(artifact_version),
            "provider": provider_name,
            "model": selected_model,
            "turns": [{
                "turn_index": 1,
                "user": user_text,
                **result,
            }],
        }, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    record["run_path"] = str(run_path)
    record["transcript_path"] = str(transcript_path)
    return record


def show_trace(record: dict[str, Any]) -> None:
    st.subheader("Tool trace")
    events = record.get("tool_events", [])
    if not events:
        st.info("Không có tool nào được gọi.")
    for index, event in enumerate(events, start=1):
        result = event.get("result") or {}
        status = "error" if isinstance(result, dict) and result.get("error") else "ok"
        round_number = next(
            (round_record.get("round") for round_record in record.get("rounds", [])
             if any(item is event or item == event for item in round_record.get("tool_results", []))),
            "?",
        )
        with st.expander(f"#{index} {event.get('tool')} · round {round_number} · {status}"):
            st.json({"tool": event.get("tool"), "args": event.get("args"), "status": status, "result": result})


def show_record(record: dict[str, Any], label: str = "Result") -> None:
    st.subheader(label)
    st.write(record.get("assistant_text") or "(no final response)")
    st.caption(
        f"artifact_version={record.get('artifact_version')} · "
        f"run={record.get('run_path')} · transcript={record.get('transcript_path')}"
    )
    show_trace(record)
    with st.expander("Full run JSON"):
        st.json(record)


st.set_page_config(page_title="Research Agent Eval UI", layout="wide")
st.title("Research Agent · Evidence UI")
st.caption("Run the same scenario across artifact versions and inspect the complete tool trace.")

with st.sidebar:
    provider_name = st.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"], index=0)
    version = st.selectbox("Version", ["v0", "v1", "v2", "v3"], index=3)
    model = st.text_input("Model (optional)") or None
    st.markdown("**Current artifacts**")
    st.code(f"system_prompt.md\ntools.yaml\nversion={version}")

scenario = st.text_area(
    "Scenario",
    value="Tin tức AI hôm nay có gì nổi bật?",
    height=110,
    help="Nhập một request để xem response, round và kết quả từng tool.",
)

col_run, col_compare = st.columns(2)
with col_run:
    run_clicked = st.button("Run scenario", type="primary", use_container_width=True)
with col_compare:
    compare_clicked = st.button("Compare v0 → v3", use_container_width=True)

if run_clicked and scenario.strip():
    with st.spinner("Calling provider and tools..."):
        try:
            st.session_state["last_record"] = execute_scenario(scenario.strip(), provider_name, version, model)
        except Exception as exc:
            st.error(f"Run failed: {type(exc).__name__}: {exc}")

if compare_clicked and scenario.strip():
    with st.spinner("Running scenario across v0, v1, v2, v3..."):
        comparison: dict[str, dict[str, Any]] = {}
        try:
            for candidate in ["v0", "v1", "v2", "v3"]:
                comparison[candidate] = execute_scenario(scenario.strip(), provider_name, candidate, model)
            st.session_state["comparison"] = comparison
        except Exception as exc:
            st.error(f"Comparison failed: {type(exc).__name__}: {exc}")

if st.session_state.get("last_record"):
    show_record(st.session_state["last_record"])

comparison = st.session_state.get("comparison")
if comparison:
    st.header("Version comparison")
    for candidate, record in comparison.items():
        with st.expander(f"{candidate} · {record.get('artifact_version')}", expanded=candidate == version):
            show_record(record, label=f"{candidate} response")
