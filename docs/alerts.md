# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert mẫu để tham khảo

Ví dụ dưới đây minh họa mức độ cụ thể cần có. Học viên không cần copy nguyên, nhưng ba alert trong bài nộp nên rõ ràng tương tự: điều kiện là gì, kéo dài bao lâu, ảnh hưởng tới user ra sao và người trực cần kiểm tra gì trước.

- Tên: `HighLatencyP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: latency P95 của `response_sent.latency_ms`
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` trong 5 phút
- Ảnh hưởng tới người dùng: người dùng phải chờ lâu hơn trước khi nhận câu trả lời
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard latency để xác nhận P95/P99 và khoảng thời gian tăng.
  2. Lọc `data/logs.jsonl` trong khoảng đó, lấy một `correlation_id` có `latency_ms` cao.
  3. Mở trace cùng `correlation_id` trên Langfuse, so sánh các span chính để xác định bước nào bất thường.
- Mitigation tạm thời: dựa trên evidence thực tế để rollback prompt, khôi phục cấu hình liên quan, tắt practice scenario hoặc giảm tải khi demo.
- Owner: `student-<MSSV>`

## Alert 1

- Tên: `HighLatencyTailP95`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Primary SLO `fast_successful_requests` (latency P95 của `response_sent.latency_ms`)
- Điều kiện và thời gian duy trì: `p95(latency_ms) > 3000ms` duy trì liên tục trong 5 phút
- Ảnh hưởng tới người dùng: Người dùng phải chờ lâu hơn để nhận phản hồi từ AI API, trải nghiệm tương tác bị gián đoạn, nguy cơ client timeout.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở panel *Latency percentiles and TTFT* trên dashboard để kiểm tra P95/P99 và TTFT P95 xem độ trễ bắt đầu tăng từ lúc nào và TTFT có bị tăng theo hay không.
  2. **Logs**: Lọc file `data/logs.jsonl` trong khoảng thời gian bị chậm, tìm các event `response_sent` có `latency_ms > 3000` để lấy một `correlation_id` đại diện.
  3. **Traces**: Mở trace có cùng `correlation_id` trên Langfuse, so sánh thời lượng của span `retrieval` và span `generation` để xác định bước nào là điểm nghẽn (ví dụ RAG vector store chậm hay LLM sinh token chậm).
- Mitigation tạm thời:
  - Nếu do prompt mới làm mô hình suy nghĩ lâu: Rollback prompt label `production` về phiên bản ổn định trước đó trên Langfuse.
  - Nếu do retrieval quá tải: Kích hoạt fallback cache hoặc hạ bớt số lượng tài liệu context.
  - Tắt scenario injection nếu đang chạy diễn tập: `python scripts/inject_incident.py --scenario rag_slow --disable`.
- Owner: `student-2A202602864`

## Alert 2

- Tên: `HighApiErrorRate`
- Severity: `critical`
- Duration: `3m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Guardrail `error_rate_pct_max: 2` (tỉ lệ lỗi request API)
- Điều kiện và thời gian duy trì: `error_rate_pct > 2%` duy trì liên tục trong 3 phút
- Ảnh hưởng tới người dùng: Người dùng nhận mã lỗi HTTP 500 khi gọi API `/chat`, dịch vụ bị gián đoạn hoặc từ chối xử lý.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở panel *Error rate and retrieval success* trên dashboard để quan sát tỉ lệ lỗi và breakdown các loại lỗi (`error_type`).
  2. **Logs**: Lọc `data/logs.jsonl` theo `event == "request_failed"`, lấy `correlation_id`, `error_type` và thông tin chi tiết trong `payload.detail`.
  3. **Traces**: Mở trace tương ứng trên Langfuse bằng `correlation_id`, kiểm tra span nào bị status `ERROR` và ngoại lệ ném ra tại span đó.
- Mitigation tạm thời:
  - Nếu xảy ra lỗi downstream vector store / tool: kích hoạt fallback response an toàn thay vì crash 500.
  - Kiểm tra trạng thái mạng và tài nguyên máy chủ API.
  - Tắt scenario lỗi nếu đang diễn tập: `python scripts/inject_incident.py --scenario tool_fail --disable`.
- Owner: `student-2A202602864`

## Alert 3

- Tên: `LowRetrievalSuccessRate`
- Severity: `warning`
- Duration: `5m`
- Kênh thông báo: Slack `#k4-l3b-alerts`
- SLI/SLO liên quan: Guardrail `retrieval_success_rate_pct_min: 90` (tỉ lệ tìm kiếm context RAG thành công)
- Điều kiện và thời gian duy trì: `retrieval_success_rate_pct < 90%` duy trì liên tục trong 5 phút
- Ảnh hưởng tới người dùng: AI không nhận được context tài liệu từ vector store, dẫn đến câu trả lời thiếu chính xác, hallucination hoặc giảm `quality_score`.
- Ba bước kiểm tra đầu tiên:
  1. **Metrics**: Mở panel *Error rate and retrieval success* và panel *Quality proxy* trên dashboard để đối chiếu tỉ lệ `tool_success` và mức độ suy giảm điểm chất lượng.
  2. **Logs**: Lọc các dòng log có `tool_name == "retrieval"` và `tool_success == false`, ghi nhận `correlation_id`, `session_id`, `feature`.
  3. **Traces**: Mở trace trên Langfuse theo `correlation_id`, kiểm tra child observation `retrieval` (thời gian truy vấn, lỗi timeout, số lượng document trả về `doc_count`).
- Mitigation tạm thời:
  - Chuyển hướng sang retrieval mirror hoặc cache local domain document nếu vector store chính gặp sự cố.
  - Cảnh báo đội ngũ quản trị RAG/Vector Store kiểm tra tính khả dụng của index.
  - Tắt scenario nếu đang diễn tập: `python scripts/inject_incident.py --scenario tool_fail --disable`.
- Owner: `student-2A202602864`
