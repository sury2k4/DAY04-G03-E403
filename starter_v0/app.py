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

tab_chat, tab_evidence, tab_compare = st.tabs(["💬 Chat", "📊 Evidence v0→v3", "⚖️ So sánh version"])

with tab_evidence:
    st.subheader("Câu chuyện tối ưu qua 4 version (từ runs/*.json thật)")
    runs_dir = ROOT / "runs"
    run_rows: list[dict[str, Any]] = []
    for run_file in sorted(runs_dir.glob("*.json")):
        try:
            payload = json.loads(run_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        summary = payload.get("summary", {})
        run_rows.append({
            "version": payload.get("version"),
            "suite": payload.get("suite"),
            "case_accuracy": summary.get("case_accuracy"),
            "routing": summary.get("tool_routing_accuracy"),
            "args": summary.get("argument_accuracy"),
            "multiturn": summary.get("multiturn_accuracy"),
            "passed": f"{summary.get('passed_cases')}/{summary.get('total_cases')}",
            "provider_errors": summary.get("provider_error_cases"),
            "artifact_version": payload.get("artifact_version"),
            "run_file": run_file.name,
        })
    if not run_rows:
        st.info("Chưa có run nào trong runs/. Chạy run_eval.py trước.")
    else:
        base_rows = [r for r in run_rows if r["suite"] == "base"]
        latest_by_version: dict[str, dict[str, Any]] = {}
        for row in base_rows:
            latest_by_version[row["version"]] = row  # sorted by filename => latest wins
        chart_rows = [latest_by_version[v] for v in sorted(latest_by_version)]
        st.markdown("**Base suite (20 case cố định) — case_accuracy theo version:**")
        st.bar_chart(
            {r["version"]: r["case_accuracy"] for r in chart_rows},
            height=260,
        )
        col1, col2, col3, col4 = st.columns(4)
        story = {
            "v0": "Baseline: prompt 'đoán bừa' — 14/20",
            "v1": "Sửa prompt: clarify/confirm/refuse — 19/20",
            "v2": "Sửa tools.yaml: fix R11, lộ regression — 18/20",
            "v3": "Map handle + rule multi-turn — 20/20",
        }
        for col, ver in zip((col1, col2, col3, col4), ("v0", "v1", "v2", "v3")):
            row = latest_by_version.get(ver)
            if row:
                col.metric(ver, f"{row['case_accuracy']:.2f}", help=story.get(ver, ""))
        st.markdown("**Tất cả các run (base + group):**")
        st.dataframe(run_rows, use_container_width=True)

        st.markdown("**Soi chi tiết một run — case nào fail, vì sao:**")
        selected = st.selectbox("Chọn run file", [r["run_file"] for r in run_rows], index=len(run_rows) - 1)
        payload = json.loads((runs_dir / selected).read_text(encoding="utf-8"))
        for item in payload.get("results", []):
            result = item["result"]
            icon = "✅" if result.get("passed") else "❌"
            with st.expander(f"{icon} {item['id']} — {result.get('failure_type') or 'PASS'}"):
                st.write("**Input:**", item.get("input"))
                st.write("**Expected:**")
                st.json(item.get("expect"), expanded=False)
                st.write("**Actual tool calls:**")
                st.json(result.get("actual_tool_calls"), expanded=False)
                if result.get("failures"):
                    st.error("; ".join(result["failures"]))

with tab_compare:
    st.subheader("Cùng một case — hành vi thay đổi qua từng version")
    runs_dir = ROOT / "runs"
    version_results: dict[str, dict[str, Any]] = {}  # version -> case_id -> result item
    for run_file in sorted(runs_dir.glob("*.json")):
        try:
            payload = json.loads(run_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("suite") != "base":
            continue
        version_results[payload.get("version")] = {
            item["id"]: item for item in payload.get("results", [])
        }
    if not version_results:
        st.info("Chưa có base run nào trong runs/.")
    else:
        versions = sorted(version_results)
        all_case_ids = sorted({cid for cases in version_results.values() for cid in cases})
        interesting = [c for c in all_case_ids if any(
            not version_results[v].get(c, {}).get("result", {}).get("passed", True)
            for v in versions if c in version_results[v]
        )]
        st.caption(f"Các case từng fail ở ít nhất một version: {', '.join(interesting)}")
        case_id = st.selectbox("Chọn case", all_case_ids, index=all_case_ids.index("R10_missing_handle") if "R10_missing_handle" in all_case_ids else 0)

        sample = next((version_results[v][case_id] for v in versions if case_id in version_results[v]), None)
        if sample:
            st.markdown("**Input:**")
            st.json(sample.get("input"), expanded=False) if isinstance(sample.get("input"), list) else st.info(sample.get("input"))
            st.markdown("**Expected:**")
            st.json(sample.get("expect"), expanded=False)

        cols = st.columns(len(versions))
        for col, ver in zip(cols, versions):
            item = version_results[ver].get(case_id)
            with col:
                st.markdown(f"### {ver}")
                if not item:
                    st.caption("không có trong run")
                    continue
                result = item["result"]
                if result.get("passed"):
                    st.success("PASS")
                else:
                    st.error(f"FAIL — {result.get('failure_type')}")
                st.markdown("Tool calls thực tế:")
                st.json(result.get("actual_tool_calls") or "không gọi tool", expanded=True)
                if result.get("failures"):
                    st.caption("Lỗi: " + "; ".join(result["failures"]))

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


with tab_chat:
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
