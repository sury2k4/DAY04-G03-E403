# Tool: crypto_price

Tra cứu giá tiền điện tử (Cryptocurrency) theo thời gian thực.

## Parameters
- `symbol` (string, required): Mã hoặc tên đồng tiền điện tử (ví dụ: `btc`, `eth`, `sol`, `bitcoin`, `ethereum`). Mặc định: `"btc"`.
- `currency` (string, optional): Loại tiền tệ quy đổi (ví dụ: `usd`, `eur`, `vnd`). Mặc định: `"usd"`.

## Output
Returns a JSON object:
```json
{
  "tool": "get_crypto_price",
  "symbol": "btc",
  "currency": "usd",
  "price": 95000.0,
  "error": null
}
```
