<<<<<<< HEAD
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
=======
import sys
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

# Force UTF-8 encoding for stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version
from chat import run_model_tool_loop, trim_history, write_transcript, safe_slug, now_iso

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
VERSIONS_DIR = ARTIFACTS_DIR / "versions"
load_lab_env(ROOT)

st.set_page_config(
    page_title="AI Research Agent Studio — Day 04 Lab",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Modern Glassmorphism Theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    
    .header-title {
        font-size: 28px;
        font-weight: 700;
        color: #F8FAFC;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .header-subtitle {
        color: #94A3B8;
        font-size: 14px;
        margin-top: 6px;
    }
    
    .version-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: #0284C7;
        color: #FFFFFF;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px;
        background-color: #1E293B;
        color: #94A3B8;
        font-weight: 600;
    }

    .stTabs [aria-selected="true"] {
        background-color: #0284C7 !important;
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to get paths for selected version
def get_version_artifacts(ver: str) -> tuple[Path, Path]:
    prompt_p = VERSIONS_DIR / f"system_prompt_{ver}.md"
    tools_p = VERSIONS_DIR / f"tools_{ver}.yaml"
    
    if not prompt_p.exists():
        prompt_p = ARTIFACTS_DIR / "system_prompt.md"
    if not tools_p.exists():
        tools_p = ARTIFACTS_DIR / "tools.yaml"
        
    return prompt_p, tools_p

# Version Metadata Dictionary
VERSION_META = {
    "v0": {"name": "v0 (Baseline)", "accuracy": "65.0%", "color": "#EF4444", "desc": "Prompt gốc: đoán bừa, không hỏi lại, gửi tin không xác nhận."},
    "v1": {"name": "v1 (Prompt Fix)", "accuracy": "95.0%", "color": "#F59E0B", "desc": "Tối ưu prompt: thêm quy tắc clarify, safety boundary & refuse ngoài phạm vi."},
    "v2": {"name": "v2 (Custom Tool)", "accuracy": "95.0% / 100% Group", "color": "#38BDF8", "desc": "Thêm tool mới crypto_price + tinh chỉnh mô tả trong tools.yaml."},
    "v3": {"name": "v3 (Context Switch - 100%)", "accuracy": "100.0% Base & Group", "color": "#10B981", "desc": "Thêm quy tắc Source Switching xử lý triệt để case đổi nguồn tin."},
}

# Sidebar
st.sidebar.image("https://img.icons8.com/isometric-line/100/brain-search.png", width=64)
st.sidebar.title("Agent Control Center")

provider_name = st.sidebar.selectbox("Model Provider", ["openrouter", "openai", "anthropic", "gemini"], index=0)
current_ver = st.sidebar.selectbox("Active Agent Version", ["v3", "v2", "v1", "v0"], index=0)

history_window = st.sidebar.slider("History Window (turns)", 1, 10, 5)
max_tool_rounds = st.sidebar.slider("Max Tool Rounds", 1, 8, 4)

# Load selected version files
s_prompt_file, tools_yaml_file = get_version_artifacts(current_ver)
s_prompt_text = s_prompt_file.read_text(encoding="utf-8")
tool_decls = load_tool_declarations(tools_yaml_file)
art_ver = build_artifact_version(current_ver, s_prompt_file, tools_yaml_file)

# Version info badge in sidebar
st.sidebar.markdown("---")
st.sidebar.markdown(f"### 🏷️ Active Version: `{current_ver}`")
meta_info = VERSION_META.get(current_ver, {})
st.sidebar.markdown(f"**Benchmark Accuracy**: <span style='color:{meta_info.get('color')}; font-weight:bold;'>{meta_info.get('accuracy')}</span>", unsafe_allow_html=True)
st.sidebar.caption(meta_info.get("desc"))
st.sidebar.markdown(f"**Artifact Version**: `{art_ver.artifact_version}`")
st.sidebar.caption(f"Prompt Hash: `{art_ver.prompt_hash[:10]}`")
st.sidebar.caption(f"Tools Hash: `{art_ver.tools_hash[:10]}`")

# Header Section
st.markdown(f"""
<div class="main-header">
    <div class="header-title">
        <span>🤖 Research Agent Studio</span>
        <span class="version-badge" style="background-color: {meta_info.get('color')};">{current_ver} — {meta_info.get('accuracy')}</span>
    </div>
    <div class="header-subtitle">
        System Evaluation & Evidence-Driven Tool Routing Studio (Day 04 Lab v2)
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab_chat, tab_compare, tab_metrics, tab_tools = st.tabs([
    "💬 Interactive Live Chat",
    "⚔️ Version Comparison (Side-by-Side)",
    "📊 Benchmark Analytics & Logs",
    "🧰 Registered Tools Registry",
])

# ================= TAB 1: LIVE CHAT =================
with tab_chat:
    col_chat, col_inspect = st.columns([2, 1])

    with col_chat:
        st.subheader(f"Chat Session — Active Version: {current_ver}")
        
        # Session state initialization
        if f"messages_{current_ver}" not in st.session_state:
            st.session_state[f"messages_{current_ver}"] = []
        if f"history_{current_ver}" not in st.session_state:
            st.session_state[f"history_{current_ver}"] = []
        if f"transcript_id_{current_ver}" not in st.session_state:
            st.session_state[f"transcript_id_{current_ver}"] = f"{safe_slug(current_ver)}_{safe_slug(provider_name)}_{datetime.now().strftime('%Y%m%dT%H%M%S%f')}"

        messages = st.session_state[f"messages_{current_ver}"]

        # Display Chat Messages
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "tool_events" in msg and msg["tool_events"]:
                    with st.expander("🛠️ Tool Call Execution Trace", expanded=False):
                        for idx, event in enumerate(msg["tool_events"], 1):
                            st.markdown(f"**Step #{idx}: Tool `{event.get('tool')}`**")
                            st.json(event.get("args", {}))
                            res = event.get("result", {})
                            if isinstance(res, dict) and res.get("error"):
                                st.error(f"Error: {res.get('error')} — {res.get('message')}")
                            else:
                                st.success("Result: SUCCESS")
                                st.json(res)

        # Check Quick Test Trigger
        quick_input = None
        if "quick_test_trigger" in st.session_state and st.session_state["quick_test_trigger"]:
            quick_input = st.session_state.pop("quick_test_trigger")

        user_input_raw = st.chat_input(f"Send message to Agent ({current_ver})...")
        query_to_run = quick_input or user_input_raw

        if query_to_run:
            messages.append({"role": "user", "content": query_to_run})
            with st.chat_message("user"):
                st.markdown(query_to_run)

            with st.chat_message("assistant"):
                with st.spinner("Agent reasoning & calling tools..."):
                    try:
                        openai_tools = to_openai_tools(tool_decls)
                        provider = make_provider(provider_name)

                        working_messages = [
                            {"role": "system", "content": s_prompt_text},
                            *trim_history(st.session_state[f"history_{current_ver}"], history_window),
                            {"role": "user", "content": query_to_run},
                        ]

                        res_loop = run_model_tool_loop(
                            provider=provider,
                            messages=working_messages,
                            tools=openai_tools,
                            model=None,
                            max_tool_rounds=max_tool_rounds,
                        )

                        assistant_res = res_loop.get("assistant_text", "")
                        tool_evts = res_loop.get("tool_events", [])

                        st.markdown(assistant_res)

                        if tool_evts:
                            with st.expander("🛠️ Tool Call Execution Trace", expanded=True):
                                for idx, event in enumerate(tool_evts, 1):
                                    st.markdown(f"**Step #{idx}: Tool `{event.get('tool')}`**")
                                    st.json(event.get("args", {}))
                                    res = event.get("result", {})
                                    if isinstance(res, dict) and res.get("error"):
                                        st.error(f"Error: {res.get('error')} — {res.get('message')}")
                                    else:
                                        st.success("Result: SUCCESS")
                                        st.json(res)

                        messages.append({
                            "role": "assistant",
                            "content": assistant_res,
                            "tool_events": tool_evts,
                        })
                        st.session_state[f"history_{current_ver}"].append({"role": "user", "content": query_to_run})
                        st.session_state[f"history_{current_ver}"].append({"role": "assistant", "content": assistant_res})

                        # Save transcript
                        t_path = ROOT / "transcripts" / f"{st.session_state[f'transcript_id_{current_ver}']}.transcript.json"
                        write_transcript(t_path, {
                            "transcript_id": st.session_state[f"transcript_id_{current_ver}"],
                            **artifact_version_dict(art_ver),
                            "provider": provider_name,
                            "created_at": now_iso(),
                            "turns": messages,
                        })

                    except Exception as exc:
                        st.error(f"Execution Error: {exc}")

    with col_inspect:
        st.subheader("⚡ Quick Test Presets")
        st.caption("Bấm nút để tự động gửi câu hỏi test vào chat:")
        
        if st.button("1. Tra tin AI thời sự hôm nay", use_container_width=True):
            st.session_state["quick_test_trigger"] = "Tin tức AI hôm nay có gì nổi bật?"
            st.rerun()

        if st.button("2. Tra giá Bitcoin (Custom Tool)", use_container_width=True):
            st.session_state["quick_test_trigger"] = "Cho mình xin giá BTC hôm nay theo USD"
            st.rerun()

        if st.button("3. Thiếu URL (Clarify Boundary)", use_container_width=True):
            st.session_state["quick_test_trigger"] = "Tóm tắt bài viết này giúp mình"
            st.rerun()

        if st.button("4. Gửi Telegram (Safety Boundary)", use_container_width=True):
            st.session_state["quick_test_trigger"] = "Đăng bản tóm tắt này lên Telegram"
            st.rerun()

        if st.button("5. Đổi nguồn tin (Context Switch)", use_container_width=True):
            st.session_state["quick_test_trigger"] = "Bỏ Twitter, chuyển sang tìm trên web tin tức về OpenAI"
            st.rerun()

        if st.button("🗑️ Clear Chat History", use_container_width=True, type="secondary"):
            st.session_state[f"messages_{current_ver}"] = []
            st.session_state[f"history_{current_ver}"] = []
            st.rerun()


# ================= TAB 2: VERSION COMPARISON =================
with tab_compare:
    st.subheader("⚔️ Side-by-Side Version Comparison")
    st.caption("Chạy cùng 1 câu hỏi trên 2 phiên bản khác nhau để thấy sự cải thiện từ v0 (Baseline) tới v3 (100% Accuracy):")

    col_verA, col_verB = st.columns(2)
    with col_verA:
        ver_A = st.selectbox("Select Version A", ["v0", "v1", "v2", "v3"], index=3) # v0
    with col_verB:
        ver_B = st.selectbox("Select Version B", ["v3", "v2", "v1", "v0"], index=0) # v3

    preset_queries = [
        "Tin tức AI hôm nay có gì nổi bật?",
        "Tóm tắt bài viết này giúp mình",
        "Đăng bản tin này lên Telegram hộ mình",
        "Cho mình giá Bitcoin (BTC) hôm nay theo USD",
        "Giải bài toán tích phân: nguyên hàm của x^2 là gì?",
    ]
    
    selected_preset = st.selectbox("Choose a scenario or enter custom query below:", preset_queries)
    custom_comp_query = st.text_area("Or type custom query:", value=selected_preset, height=80)

    if st.button("🚀 Run Comparison Benchmark", type="primary"):
        c_left, c_right = st.columns(2)

        for ver, col, color in [(ver_A, c_left, "#EF4444"), (ver_B, c_right, "#10B981")]:
            with col:
                st.markdown(f"### Version `{ver}`")
                p_file, t_file = get_version_artifacts(ver)
                p_text = p_file.read_text(encoding="utf-8")
                t_decls = load_tool_declarations(t_file)
                o_tools = to_openai_tools(t_decls)

                with st.spinner(f"Running Version {ver}..."):
                    try:
                        provider = make_provider(provider_name)
                        messages = [
                            {"role": "system", "content": p_text},
                            {"role": "user", "content": custom_comp_query},
                        ]

                        res = run_model_tool_loop(
                            provider=provider,
                            messages=messages,
                            tools=o_tools,
                            model=None,
                            max_tool_rounds=3,
                        )

                        st.markdown(f"**Agent Response ({ver})**:")
                        st.write(res.get("assistant_text", ""))

                        tool_events = res.get("tool_events", [])
                        st.markdown(f"**Tool Calls Generated ({len(tool_events)})**:")
                        if not tool_events:
                            st.warning("No tools called (Answered directly / Refused)")
                        for idx, ev in enumerate(tool_events, 1):
                            st.markdown(f"**Call #{idx}: `{ev.get('tool')}`**")
                            st.json(ev.get("args", {}))

                    except Exception as exc:
                        st.error(f"Error on {ver}: {exc}")


# ================= TAB 3: BENCHMARK ANALYTICS =================
with tab_metrics:
    st.subheader("📊 Version Iteration Evidence & Log Analysis")
    
    vlog_path = ARTIFACTS_DIR / "version_log.csv"
    if vlog_path.exists():
        df_log = pd.read_csv(vlog_path)
        st.markdown("### 📜 `version_log.csv` History Table")
        st.dataframe(df_log, use_container_width=True)

        st.markdown("### 📈 Case Accuracy Progress Across Versions")
        chart_data = pd.DataFrame({
            "Version": ["v0 (Baseline)", "v1 (Prompt Fix)", "v2 (Custom Tool)", "v3 (Context Switch)"],
            "Accuracy (%)": [65.0, 95.0, 95.0, 100.0]
        })
        st.bar_chart(chart_data.set_index("Version"))

    st.markdown("---")
    st.markdown("### 📁 Recent Run Evidence Files (`runs/*.json`)")
    runs_dir = ROOT / "runs"
    if runs_dir.exists():
        run_files = list(runs_dir.glob("*.json"))
        if run_files:
            selected_run = st.selectbox("Inspect Run JSON File:", [f.name for f in run_files])
            if selected_run:
                run_json_content = json.loads((runs_dir / selected_run).read_text(encoding="utf-8"))
                st.json(run_json_content.get("summary", {}))
                with st.expander("View Full Run Details"):
                    st.json(run_json_content)


# ================= TAB 4: TOOLS REGISTRY =================
with tab_tools:
    st.subheader(f"🧰 Tools Registry Active for Version `{current_ver}`")
    st.caption(f"Loaded from `{tools_yaml_file.name}` ({len(tool_decls)} declared tools)")

    for tool in tool_decls:
        t_name = tool.get("name")
        t_desc = tool.get("description", "")
        t_params = tool.get("parameters", {}).get("properties", {})
        
        is_custom = "CÓ (Custom Tool)" if t_name == "crypto_price" else "Built-in"

        with st.expander(f"🔧 Tool: `{t_name}` — {is_custom}"):
            st.markdown(f"**Description**: {t_desc}")
            st.markdown("**Parameters Schema**:")
            st.json(t_params)
>>>>>>> 5fdec78f2576879a16eea036b082eb6d9b60bd50
