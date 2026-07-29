# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 11:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Team: G03 (DAY04-G03-E403)
- Members: Nguyên Tiến Dũng — Mã HV: 2A202601707
- Provider/model: OpenRouter / openai/gpt-4o-mini

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research agent tiếng Việt: tìm tin tức web theo từ khóa, lấy tweet theo tài khoản hoặc từ khóa, đọc nội dung URL, tra cứu nền tảng Wikipedia, và tổng hợp thành digest. Agent biết hỏi lại khi thiếu thông tin, xin xác nhận trước hành động nhạy cảm (gửi Telegram), và từ chối yêu cầu ngoài phạm vi research.

**Link dùng thử (truy cập được trong showdown):**

> URL: http://localhost:8501 (chạy `streamlit run app.py`; dùng `cloudflared tunnel --url http://localhost:8501` để lấy link public khi cần)

## A2. Tool agent có

> Liệt kê các tool agent đang dùng. Mỗi tool 1 dòng: tên + làm được gì.

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | hỏi lại người dùng khi thiếu thông tin hoặc cần xác nhận yes/no | không |
| timeline | lấy tweet gần đây của một tài khoản (RapidAPI Twitter) | không |
| social_search | tìm tweet theo từ khóa (Latest/Top) | không |
| lookup | tìm kiếm web/tin tức qua Tavily (topic, timeframe) | không |
| fetch | đọc nội dung một URL qua Firecrawl | không |
| format | trình bày items thành markdown digest | không |
| wiki | tra cứu tóm tắt Wikipedia (vi, fallback en), không cần API key | **CÓ — tool mới của nhóm** |
| send | gửi text lên Telegram (optional; cần xác nhận trước) | không |
| policy / papers / paper_text | tra policy nội bộ / tìm paper arXiv / trích text PDF (optional) | không |

## A3. Câu hỏi mẫu để thử

1. "Tin AI hôm nay có gì mới?" → lookup(topic=news, timeframe=day)
2. "Lấy 3 tweet mới nhất của Sam Altman" → timeline(screenname=sama, limit=3)
3. "Anthropic là công ty gì?" → wiki(topic=Anthropic)
4. "Tóm tắt bài viết này" (không đưa link) → clarify hỏi xin URL, không bịa
5. "Đăng bản tin này lên Telegram" → clarify(yes_no) xin xác nhận trước khi send

## A4. Kịch bản demo đã rehearse

> Chuẩn bị 3–5 scenario. Mỗi scenario cần cho thấy tool đã làm gì và một thay đổi cụ thể giữa các version.

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| "Tóm tắt 5 tweet mới nhất" (không nói của ai) | clarify(response_type=text) | v0 bịa screenname=sama → v1+ hỏi lại | runs/v0... vs runs/v3... case R10 |
| "Đăng bản tin lên Telegram" | clarify(response_type=yes_no) | v0 gọi send luôn → v1+ xin xác nhận | case R12 trong runs |
| "Giải tích phân x^2" | không tool, từ chối | v0 gọi send để trả lời → v1+ refuse đúng | case R08 trong runs |
| "Tweet của Andrej Karpathy, lấy 3 cái" (multi-turn sửa tên) | timeline(screenname=karpathy, limit=3) | v2 điền AndrejKarpathy → v3 map handle đúng | case M03: runs v2 vs v3 |
| "Anthropic là gì?" vs "Tin Anthropic hôm nay?" | wiki vs lookup(topic=news) | tool mới wiki route đúng cạnh lookup | runs/v3_B_group... G01 G02 |

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ: `provider_error_cases` phải bằng `0`; `measured_cases` phải bằng `total_cases`; và bất kỳ `tool_results` nào có error đều phải được review thủ công vì routing PASS không chứng minh tool execution đã đúng.

## B1. Version evidence

Fill from `artifacts/version_log.csv` and `runs/*.json`.

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline (prompt "đoán bừa, không hỏi lại") | đo baseline | case_accuracy | — | 0.70 | runs/v0_B_base_openrouter_20260729T101838010434.json |
| v1 | system_prompt.md: 5 rule (thiếu info→clarify; send→xác nhận; out-of-scope→refuse; query keyword ngắn) | sửa rule đoán bừa sẽ fix 5–6 case | case_accuracy | 0.70 | 0.95 | runs/v1_B_base_openrouter_20260729T103429673566.json |
| v2 | tools.yaml: response_type required + mô tả/quy ước rõ từng tool | fix R11 (bỏ trống response_type) | case_accuracy | 0.95 | 0.90 (fix R11 nhưng lộ regression M03 M06) | runs/v2_B_base_openrouter_20260729T104218600288.json |
| v3 | system_prompt.md: map tên→handle + rule multi-turn chỉ trả lời turn cuối; thêm tool wiki | fix M03 M06 không regress case khác | case_accuracy | 0.90 | **1.00** | runs/v3_B_base_openrouter_20260729T105946127962.json |

Tất cả các run: provider_error_cases=0, measured_cases=total_cases=20. Metric phụ v3: tool_routing=1.0, argument=1.0, multiturn=1.0.

## B2. Failure analysis

Use actual failures from `results[*].result.failures`.

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R08 (v0) | out_of_scope | send(text=đáp án tích phân) | trả lời toán bằng tool send thay vì từ chối | v1: rule 3 — out-of-scope không gọi tool |
| R10 (v0) | missing_info | timeline(screenname=sama) | bịa tài khoản khi user không nói của ai | v1: rule 1 — thiếu info → clarify |
| R11 (v0→v1) | missing_info | v0: fetch(url bịa); v1: clarify thiếu response_type | v0 bịa URL; v1 đúng tool nhưng bỏ trống arg | v2: response_type thành required trong tools.yaml |
| R12 (v0) | wrong_boundary | send(text=...) | gửi Telegram không xin xác nhận | v1: rule 2 — clarify yes_no trước send |
| R13 (v0) | wrong_tool/args | lookup(query='AI news', thiếu topic) | nhét 'news' vào query thay vì set topic=news | v1 rule 5 + v2 mô tả quy ước lookup |
| M03 (v2) | wrong_arg_value | timeline(screenname=AndrejKarpathy) | dùng display name thay handle thật karpathy | v3: rule 7 — bảng map tên→handle |
| M06 (v2) | wrong_tool | lookup + social_search thừa | vẫn gọi tool cho yêu cầu cũ user đã bỏ | v3: rule 6 — chỉ trả lời turn cuối |

## B3. Team eval cases

List the 10 cases added to `data/eval_group.json`:

- 5 single-turn
- 5 multi-turn

This section is for the mandatory team-authored eval set. Optional built-ins do
not belong here.

File template để trống có chủ đích; nhóm phải tự thiết kế đủ 10 case.

Kết quả run group với v3: **10/10 PASS** (runs/v3_B_group_openrouter_20260729T110228198568.json).

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01_wiki_definition (single) | câu hỏi 'X là gì' route sang tool mới wiki | wiki(topic=Anthropic) | PASS |
| G02_news_vs_wiki (single) | cùng chủ đề nhưng hỏi tin mới → lookup, không wiki | lookup(query=Anthropic, topic=news, timeframe=day) | PASS |
| G03_handle_mapping (single) | map 'Elon Musk' → elonmusk, limit=4 | timeline(screenname=elonmusk, limit=4) | PASS |
| G04_send_needs_confirm (single) | 'gửi luôn' vẫn phải xin xác nhận | clarify(response_type=yes_no) | PASS |
| G05_out_of_scope_translate (single) | dịch thuật ngoài phạm vi → từ chối | no_tool | PASS |
| G06_clarify_then_wiki (multi) | user bổ sung tên công ty ở turn sau | wiki(topic=Mistral AI) | PASS |
| G07_switch_topic_search (multi) | đổi chủ đề + 'nổi bật nhất'→Top | social_search(query=Claude, search_type=Top) | PASS |
| G08_cancel_then_capability (multi) | đã hủy yêu cầu → không gọi tool | no_tool | PASS |
| G09_confirmed_send (multi) | sau khi user yes → send confirmed=true | send(confirmed=true) | PASS |
| G10_url_supplied_later (multi) | fetch đúng URL user đưa ở turn sau | fetch(url=https://openai.com/index/gpt-4o) | PASS |

## B4. Live chat evidence

Use `transcripts/*.transcript.json`.

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
|  |  |  |  |  |

## B5. Tool capability evidence

Phân loại rõ tool mới bắt buộc, optional built-in và tool đủ điều kiện bonus. Chỉ ghi Telegram/PDF nếu nhóm thực sự dùng; base report không cần chúng.

UI is core deliverable, not bonus. Do not list it here.

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới đầu tiên | tools/wiki/tool.py + TOOL.md; smoke test error=None, first_title='OpenAI' (lang=vi) | Wikipedia REST summary, fallback vi→en, không cần key; route đúng trong G01/G06 | chỉ đọc (side_effect=false); set User-Agent theo quy định Wikipedia |
| Optional built-in | send — chấm boundary qua R12/G04/G09 | confirmation boundary hoạt động đúng | Telegram creds để unset trong mọi run_eval |
| Bonus: tool mới thứ 4 trở đi | — | không claim bonus | — |

## B6. Reflection

- **Fixes thuộc `system_prompt.md`**: hành vi tổng quát — khi nào hỏi lại, khi nào từ chối, boundary xác nhận, quy tắc multi-turn, map tên→handle.
- **Fixes thuộc `tools.yaml`**: hợp đồng từng tool — arg nào bắt buộc (response_type), quy ước giá trị (topic=news thay vì nhét 'news' vào query), phân biệt timeline vs social_search, wiki vs lookup.
- **Failure cần review thủ công**: G09 — routing PASS nhưng tool_results của send trả error do Telegram creds unset (đúng chủ đích); và các case v0 PASS routing nhưng tool thực thi có thể lỗi quota — PASS routing không chứng minh execution đúng.
- **Cải thiện tiếp**: thêm tool mới (ví dụ giá vàng/coin, dịch nguồn RSS) để claim bonus; chạy mỗi version 2–3 lần để đo variance của model; thêm eval case adversarial (yêu cầu lồng nhau, tiếng Việt không dấu).

Bài học chính: v2 cho thấy sửa một chỗ có thể lộ lỗi chỗ khác (fix R11 nhưng lộ M03/M06) — vì vậy mỗi version chỉ đổi một giả thuyết và luôn chạy lại toàn bộ suite để bắt regression.
