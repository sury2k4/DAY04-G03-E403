# Báo cáo eval Research Agent

## Tóm tắt

Provider/model: OpenRouter / `openai/gpt-4o-mini`.

Chuỗi thí nghiệm dùng API thật và cùng bộ `data/eval_base.json`:

| Version | Thay đổi chính | Pass | Accuracy | Provider errors |
|---|---|---:|---:|---:|
| v0 | Baseline starter | 14/20 | 70% | 0 |
| v1 | Scope và routing theo intent | 16/20 | 80% | 0 |
| v2 | Missing info, arguments và multi-turn | 19/20 | 95% | 0 |
| v3 | Confirmation và multi-tool | 20/20 | 100% | 0 |

Mỗi version có hypothesis, artifact hash, metric trước–sau và run file riêng trong
`artifacts/version_log.csv`. `data/eval_base.json` không bị sửa.

## Diễn tiến thí nghiệm

### v0 — Baseline

Baseline đạt 14/20. Sáu lỗi gồm hai lỗi ngoài phạm vi, hai lỗi thiếu thông tin,
một lỗi confirmation và một lỗi routing/argument.

### v1 — Scope và routing

Hypothesis: scope và mapping intent-to-tool rõ ràng sẽ giảm lỗi dùng tool không
cần thiết và chọn sai tool.

Kết quả tăng từ 70% lên 80% (16/20). Các lỗi ngoài phạm vi và routing chính được
loại bỏ. Bốn lỗi còn lại thuộc missing info, confirmation và carry-over argument.

Run: `runs/v1_B_base_openrouter_20260729T105019466534.json`.

### v2 — Missing info, arguments và multi-turn

Hypothesis: cấm đoán handle/URL, giữ nguyên argument người dùng và ưu tiên correction
mới nhất sẽ loại lỗi missing-info và argument.

Kết quả tăng từ 80% lên 95% (19/20). Multi-turn đạt 100%; chỉ còn case xác nhận
trước khi gửi ra ngoài.

Run: `runs/v2_B_base_openrouter_20260729T105230994340.json`.

### v3 — Confirmation và multi-tool

Hypothesis: boundary rõ cho write action và yêu cầu thực hiện đủ các tool độc lập
sẽ loại lỗi cuối cùng mà không gây regression.

Kết quả tăng từ 95% lên 100% (20/20). Routing, argument và multi-turn đều đạt 100%.

Run: `runs/v3_B_base_openrouter_20260729T105452816686.json`.

## Team-authored và extension

Artifact v3 cuối cùng là `v3+pbda7da669697+taf30e6630f44`.

| Bộ eval | Version | Pass | Accuracy | Provider errors | Run |
|---|---:|---:|---:|---:|---|
| Group (5 single-turn + 5 multi-turn) | v3 | 10/10 | 100% | 0 | `runs/v3_B_group_openrouter_20260729T105604629707.json` |
| Extension | v3 | 10/10 | 100% | 0 | `runs/v3_B_extension_openrouter_20260729T105710543908.json` |

Group và extension dùng đúng cùng prompt hash và tools hash với run base của v3.
Chúng là các suite kiểm tra thêm, không được ghi thành version giả.

## Kết luận

Chuỗi `v0 → v1 → v2 → v3` là bốn trạng thái artifact khác nhau và ba thí nghiệm
tăng dần thật. Accuracy base tăng `70% → 80% → 95% → 100%`. Bản v3 cũng đạt
100% trên group và extension, không có provider error.
