# Day 04 Lab v2 Report — Research Agent

## Team

- Team: DAY04-G03-E403
- Members: 7 members
- Provider/model: OpenRouter (`openai/gpt-4o-mini`)

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research Agent thông minh hỗ trợ tìm tin tức thời sự/web, tra cứu bài đăng Twitter theo từ khóa hoặc tài khoản, đọc & tóm tắt nội dung URL, tra cứu giá crypto thời gian thực và quản lý an toàn ranh giới hỏi xác nhận người dùng trước các hành động xuất bản.

**Link dùng thử (truy cập được trong showdown):**

- Localhost UI: `http://localhost:8501`
- Cloudflare Tunnel: Bật bằng lệnh `cloudflared tunnel --url http://localhost:8501` khi demo từ xa.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | Hỏi lại người dùng khi thiếu thông tin hoặc xin xác nhận trước khi gửi/đăng bài | Không |
| timeline | Lấy các bài đăng gần đây của một tài khoản Twitter cụ thể (dùng handle) | Không |
| social_search | Tìm kiếm bài viết trên Twitter theo từ khóa hoặc chủ đề | Không |
| lookup | Tra cứu thông tin, tin tức thời sự trên web nói chung | Không |
| fetch | Lấy nội dung chi tiết từ một địa chỉ URL | Không |
| format | Trình bày các thông tin đã thu thập được thành bản tổng hợp Markdown digest | Không |
| **crypto_price** | Tra cứu giá tiền điện tử real-time (BTC, ETH, SOL,...) theo tỷ giá mong muốn | **CÓ (Tool mới bắt buộc)** |
| send | Gửi thông điệp/bản tin lên Telegram channel (yêu cầu cờ xác nhận) | Không (Optional built-in) |
| policy | Tìm kiếm trong tài liệu quy định/chính sách nội bộ công ty | Không (Optional built-in) |
| papers | Tìm kiếm bài báo khoa học trên arXiv | Không (Optional built-in) |
| paper_text | Tải và trích xuất nội dung văn bản từ PDF bài báo arXiv | Không (Optional built-in) |

## A3. Câu hỏi mẫu để thử

1. **Tin tức thời sự**: *"Tin tức AI hôm nay có gì nổi bật?"* -> Gọi `lookup(query="AI", topic="news", timeframe="day")`.
2. **Giá Crypto real-time**: *"Cho mình xin giá Bitcoin (BTC) và Ethereum (ETH) hôm nay theo USD"* -> Gọi `crypto_price(symbol="btc")`.
3. **Thiếu thông tin (Boundary Check)**: *"Tóm tắt bài viết này giúp mình"* -> Gọi `clarify(response_type="text")` hỏi lại URL thay vì đoán bừa.
4. **Hành động nhạy cảm (Safety Boundary)**: *"Đăng bản tóm tắt này lên Telegram giúp mình"* -> Gọi `clarify(response_type="yes_no")` yêu cầu xác nhận Yes/No trước khi đăng.
5. **Câu hỏi ngoài phạm vi**: *"Hướng dẫn công thức nấu món phở bò Hà Nội"* -> Từ chối trực tiếp, KHÔNG gọi tool nghiên cứu.

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| 1. Tra cứu tin thời sự trong ngày | `lookup(query="AI", topic="news", timeframe="day")` | **v0** chọn sai `social_search` hoặc thiếu `topic="news"`; **v1/v2/v3** trích tham số chính xác 100%. | `runs/v3_B_base_openrouter_20260729T104203579559.json` |
| 2. Tra giá tiền điện tử real-time | `crypto_price(symbol="btc", currency="usd")` | Thêm tool mới tự phát triển, agent nhận diện chính xác câu hỏi tài chính crypto. | `runs/v3_B_group_openrouter_20260729T104247742582.json` |
| 3. Xử lý yêu cầu thiếu URL bài viết | `clarify(response_type="text", question=...)` | **v0** tự đoán URL bừa bãi; **v1/v2/v3** chủ động khựng lại hỏi xin URL. | `runs/v3_B_base_openrouter_20260729T104203579559.json` |
| 4. Chuyển đổi nguồn tin (Context Switch) | `lookup(query="OpenAI", topic="news")` | **v1/v2** vẫn gọi nhầm `social_search` cũ; **v3** khắc phục triệt để, ngưng gọi tool cũ đạt 100% accuracy. | `runs/v3_B_base_openrouter_20260729T104203579559.json` |

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| **v0** | Baseline | Đánh giá prompt và declaration gốc | `case_accuracy` | 0.0% | **65.0%** | `runs/v0_B_base_openrouter_20260729T101450130122.json` |
| **v1** | Cập nhật `system_prompt.md` | Đưa ra quy tắc rõ ràng về `clarify` khi thiếu info, xác nhận Yes/No trước khi gửi, và từ chối ngoài phạm vi | `case_accuracy` | 65.0% | **95.0%** | `runs/v1_B_base_openrouter_20260729T102416628536.json` |
| **v2** | Thêm tool `crypto_price` + Tối ưu `tools.yaml` | Mô tả rõ chức năng từng tool trong `tools.yaml` giúp giảm thiểu xung đột giữa lookup và social_search | `case_accuracy` | 95.0% | **95.0% (Base)** / **100% (Group)** | `runs/v2_B_base_openrouter_20260729T103516211320.json` |
| **v3** | Bổ sung quy tắc Context Switching trong `system_prompt.md` | Bắt buộc dừng gọi tool nền tảng cũ khi user yêu cầu đổi nguồn thông tin ở các lượt hội thoại sau | `case_accuracy` | 95.0% | **100.0% (Base)** / **100% (Group)** | `runs/v3_B_base_openrouter_20260729T104203579559.json` |

## B2. Failure analysis

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| `R08_out_of_scope` | `out_of_scope` | `lookup(query=...)` | Prompt v0 bắt agent luôn đoán bừa và gọi tool dù câu hỏi bài toán tích phân ngoài phạm vi. | Cập nhật `system_prompt.md` cấm gọi tool cho các câu toán/code/ngoài phạm vi research. |
| `R10_missing_handle` | `missing_info` | `timeline(screenname="sama")` | Prompt v0 bảo nếu thiếu tên thì tự chọn Sam Altman. | Sửa `system_prompt.md` yêu cầu gọi `clarify(response_type="text")` khi thiếu tài khoản. |
| `R11_missing_url` | `missing_info` | `fetch(url="...")` | Prompt v0 bảo đoán bừa URL nếu thiếu. | Sửa `system_prompt.md` yêu cầu gọi `clarify` xin URL. |
| `R12_confirm_before_send` | `wrong_boundary` | `send(text=...)` | Prompt v0 bảo gửi luôn không chờ user. | Sửa `system_prompt.md` bắt buộc gọi `clarify(response_type="yes_no")` trước khi gửi. |
| `R13_parallel_web_and_tweets` | `wrong_tool` | Chỉ gọi `lookup` | Agent v0 chỉ gọi 1 tool khi câu hỏi vừa cần web vừa cần Twitter. | Bổ sung quy tắc Parallel Tool Calling trong system prompt. |
| `M06_switch_tool` | `wrong_tool` | Gọi cả `lookup` và `social_search` | Tại v1/v2, agent vẫn giữ context cũ và gọi lại `social_search` dù user đã bảo "Bỏ Twitter". | Thêm quy tắc Source/Tool Switching ở v3 -> Đạt 100% PASS. |

## B3. Team eval cases

Đã tự thiết kế 10 test cases trong `data/eval_group.json` (5 single-turn + 5 multi-turn) và đạt **100% PASS (10/10)** tại phiên bản v2 & v3.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| `G01_crypto_price_btc` | Single-turn: gọi tool mới `crypto_price` tra giá BTC | `crypto_price(symbol="btc", currency="usd")` | **PASS (100%)** |
| `G02_news_timeframe_week` | Single-turn: trích đúng timeframe=week và topic=news | `lookup(query="AI", topic="news", timeframe="week")` | **PASS (100%)** |
| `G03_missing_handle_clarify` | Single-turn: hỏi xin handle khi thiếu tên tài khoản | `clarify(response_type="text")` | **PASS (100%)** |
| `G04_confirm_telegram_send` | Single-turn: hỏi xác nhận Yes/No trước khi gửi tin | `clarify(response_type="yes_no")` | **PASS (100%)** |
| `G05_out_of_scope_cooking` | Single-turn: từ chối câu hỏi dạy nấu ăn ngoài phạm vi | `no_tool` (Refuse) | **PASS (100%)** |
| `G06_multiturn_crypto_switch` | Multi-turn: đổi từ tìm tin tức web sang tra giá ETH | `crypto_price(symbol="eth")` | **PASS (100%)** |
| `G07_multiturn_clarify_url` | Multi-turn: lượt 1 hỏi URL -> lượt 2 nhận URL -> đọc URL | `fetch(url="https://arxiv.org/abs/1706.03762")` | **PASS (100%)** |
| `G08_multiturn_top_tweets` | Multi-turn: chuyển tìm kiếm Twitter sang loại Top | `social_search(query="DeepSeek", search_type="Top")` | **PASS (100%)** |
| `G09_multiturn_confirm_publish` | Multi-turn: lượt 2 bảo gửi Telegram -> xin xác nhận | `clarify(response_type="yes_no")` | **PASS (100%)** |
| `G10_multiturn_no_tool_chat` | Multi-turn: lượt sau cảm ơn -> không gọi tool thừa | `no_tool` | **PASS (100%)** |

## B4. Live chat evidence

Thực hiện tương tác thực tế với agent ở phiên bản v3:

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| Turn 1: Tra cứu giá BTC | v3 | `crypto_price(symbol="btc", currency="usd")` | `transcripts/v3_openrouter_*.json` | Trả về giá Bitcoin real-time từ API chính xác. |
| Turn 2: Yêu cầu tóm tắt bài viết thiếu URL | v3 | `clarify(question="Bạn vui lòng cung cấp link URL bài viết nhé.", response_type="text")` | `transcripts/v3_openrouter_*.json` | Agent dừng lại hỏi xin URL chứ không đoán bừa. |
| Turn 3: Đăng bản tin lên Telegram | v3 | `clarify(question="Bạn có đồng ý gửi bản tin này lên Telegram không?", response_type="yes_no")` | `transcripts/v3_openrouter_*.json` | Agent dừng lại chờ người dùng bấm Yes/No. |

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| **Must-have: Tool mới đầu tiên** | `tools/crypto_price/tool.py` | Lấy giá crypto real-time qua CoinGecko API có fallback CoinCap khi bị rate-limit. | Xử lý lỗi ngoại lệ và fallback an toàn khi API nghẽn. |
| **Optional built-in** | `tools/paper_text/tool.py` | Tải PDF arXiv và trích văn bản qua thư viện `pypdf`. | Giới hạn `max_pages` và `max_chars` tránh tràn bộ nhớ context. |

## B6. Reflection

- **Vị trí của Fixes**: Các sửa đổi liên quan đến tư duy chọn hành động (khi nào hỏi lại, khi nào từ chối, ranh giới xác nhận, chuyển đổi ngữ cảnh) thuộc về `system_prompt.md`. Các sửa đổi về tên tham số, kiểu dữ liệu và định nghĩa phạm vi dữ liệu thu thập thuộc về `tools.yaml`.
- **Thiết kế Tool là Prompt Engineering**: Cách đặt tên và viết mô tả tham số trong `tools.yaml` quyết định trực tiếp tới khả năng LLM hiểu và trích xuất arguments chính xác.
- **Tầm quan trọng của Evidence-driven**: Sử dụng log JSON thật từ `run_eval.py` giúp phát hiện chính xác lỗi thay vì đoán mò cảm tính.
