# Day 04 Lab v2 — Research Agent Report

## Team

- Team: G03-E403
- Members: Hoàng Quang Minh
- Provider/model: OpenRouter / `openai/gpt-4o-mini`
- UI: `http://localhost:8501` (chạy bằng `python -m streamlit run app.py`)

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research Agent hỗ trợ tìm tin web/social, đọc URL, tìm paper và tổng hợp research digest. Agent cũng có các tool local để phân tích văn bản đã có, hỏi lại khi thiếu thông tin và chặn hành động gửi/publish cho tới khi người dùng xác nhận.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `clarify` | hỏi lại khi thiếu thông tin hoặc cần xác nhận | không |
| `timeline` | lấy bài đăng mới nhất của một tài khoản | không |
| `social_search` | tìm bài đăng theo chủ đề | không |
| `lookup` | tìm kiếm web/news | không |
| `fetch` | đọc một URL cụ thể | không |
| `format` | định dạng research digest | không |
| `extract_links` | trích URL duy nhất từ văn bản | có |
| `text_stats` | đếm ký tự, từ, câu và thời gian đọc | có |
| `detect_language` | nhận diện sơ bộ `vi`/`en`/`unknown` | có |
| `relevance_rank` | xếp hạng item theo mức liên quan | có |
| `quote_extract` | trích nguyên văn câu chứa keyword | có |
| `send` | gửi nội dung ra ngoài sau xác nhận | không |
| `policy` | tìm policy nội bộ | không |
| `papers` / `paper_text` | tìm và đọc paper arXiv | không |

## A3. Câu hỏi mẫu

1. `Tin tức AI hôm nay có gì nổi bật?`
2. `Tweet mới nhất của Sam Altman là gì?`
3. `Tóm tắt bài này giúp mình: https://example.com/article`
4. `Đếm số từ và số câu của đoạn này: AI đang thay đổi nghiên cứu.`
5. `Đăng bản tóm tắt này lên Telegram giúp mình.`

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Cải thiện được chứng minh | Bằng chứng |
|---|---|---|---|
| News hôm nay | `lookup(topic=news,timeframe=day)` | map “hôm nay” vào timeframe day | `runs/v3_B_base_openrouter_20260729T033651481976.json` |
| Thiếu URL rồi bổ sung | `clarify` → `fetch` | không đoán URL, dùng URL ở lượt sau | `transcripts/v3_openrouter_20260729T041733274368.transcript.json` |
| Publish nhạy cảm rồi hủy | `clarify(yes_no)`, không gọi `send` | confirmation boundary và latest-turn cancellation | cùng transcript trên |

# PHẦN B — Chi tiết / Bằng chứng

Điều kiện kiểm tra được đáp ứng ở các run chính: `provider_error_cases=0` và `measured_cases=total_cases`.

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Case accuracy | Routing | Arguments | Multiturn | Run |
|---|---|---|---:|---:|---:|---:|---|
| v0 | baseline | đo lỗi routing/boundary ban đầu | 0.75 | 0.80 | 0.75 | 1.00 | `runs/v0_B_base_openrouter_20260729T031651152217.json` |
| v1 | prompt + local-tool declarations | explicit safety/routing boundaries và tool local giảm gọi sai | 0.95 | 0.95 | 0.95 | 0.8333 | `runs/v1_B_base_openrouter_20260729T032852038817.json` |
| v2 | system prompt: latest-turn authority | lượt mới nhất phải ghi đè intent cũ | 0.90 | 0.95 | 0.90 | 0.8333 | `runs/v2_B_base_openrouter_20260729T033517846919.json` |
| v3 | tools.yaml: social_search current-turn boundary | mô tả tool chính xác hơn sẽ giảm stale social routing | 0.95 | 0.95 | 0.95 | 0.8333 | `runs/v3_B_base_openrouter_20260729T033651481976.json` |

Version log đầy đủ v0, v1, v2, v3 nằm tại `artifacts/version_log.csv`. Mỗi vòng có artifact hash và run JSON tương ứng.

## B2. Failure analysis

Baseline v0 có 5 lỗi, chủ yếu là missing-info/safety boundary và một số sai argument. Sau v1 còn một lỗi; v2 làm rõ latest-turn nhưng kết quả dao động một case do provider; v3 phục hồi 0.95.

| Evidence | Quan sát | Cách xử lý |
|---|---|---|
| v0 run | có gọi tool khi thiếu handle/URL hoặc chưa xác nhận send | thêm clarify boundary và không đoán dữ liệu |
| v2 run | còn một sai argument ở multi-turn | giữ latest-turn rule, ghi nhận độ dao động model |
| v3 group run | `G07_missing_social_account` không gọi `clarify` | lỗi còn lại cần prompt/routing refinement tiếp theo; không chỉnh sau khi chốt v3 |

## B3. Team eval cases

`data/eval_group.json` có đúng 10 case, tất cả `phase: "B"`: 5 single-turn dùng `query` (`G01`–`G05`) và 5 multi-turn dùng `turns` (`G06`–`G10`). Mỗi case có `failure_type`, `expect`, `metadata.what_it_tests`.

Run thật bằng v3: `runs/v3_B_group_openrouter_20260729T041851202833.json`.

| Metric | Kết quả |
|---|---:|
| total_cases / measured_cases | 10 / 10 |
| provider_error_cases | 0 |
| passed_cases | 9 |
| case_accuracy | 0.90 |
| tool_routing_accuracy | 0.90 |
| argument_accuracy | 0.90 |
| multiturn_accuracy | 0.80 |

9 case pass; `G07` fail do missing `clarify` khi request timeline không nêu account. Đây là lỗi thật đã được giữ lại trong run/report để team biết điểm cần cải thiện.

## B4. Live chat evidence

Transcript thật: `transcripts/v3_openrouter_20260729T041733274368.transcript.json`.

| Scenario | Kết quả |
|---|---|
| research bình thường | `lookup` với AI/news/day, trả response có nguồn |
| thiếu thông tin rồi bổ sung | lượt 1 `clarify`, lượt 2 `fetch` URL example.com |
| hành động nhạy cảm | `clarify(response_type=yes_no)`, sau “không gửi nữa” không gọi `send` |

## B5. Tool capability evidence

| Category | Evidence | Kết quả / guardrail |
|---|---|---|
| Tool mới | `tools/{extract_links,text_stats,detect_language,relevance_rank,quote_extract}/` | 5 tool có `TOOL.md`, implementation, registry và YAML declaration |
| Smoke test | `cache/tool_smoke.json` | tất cả 5 local tool pass |
| Live provider | `scripts/preflight_provider.py` | OpenRouter structured tool call pass |
| UI | `app.py`, `http://localhost:8501` | hiển thị request/response, trace, transcript/run/artifact version và compare v0→v3 |

## B6. Reflection

- Prompt phù hợp cho policy, missing information, confirmation và multi-turn cancellation; YAML phù hợp cho mô tả tool/argument boundary.
- Metric tự động xác nhận routing/args nhưng không đủ để chứng minh tool execution không có error; vì vậy cần review `tool_results` thủ công.
- Điểm cần cải thiện tiếp theo là G07: viết rõ “tweet mới nhất” không có account phải gọi `clarify`, rồi chạy một version mới thay vì sửa sau v3.
- UI hiện chạy cùng scenario qua các nhãn artifact version và lưu run/transcript; compare view giúp kiểm tra trace theo từng version trong demo.
