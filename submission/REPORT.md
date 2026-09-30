# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Lê Minh Sang
- **MSSV:** 2A202602864
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/minhsangmr/K4-L3-DAY13-LeMinhSang-2A202602864-Monitoring-LLMOps
- **Commit SHA cuối:** `10b96d3c3a0de33b8f5e8b18226f502340c58711`
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602864`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Vượt ngưỡng yêu cầu (≥ 80/100), đạt điểm tuyệt đối 100/100 với đầy đủ JSON schema, context enrichment, correlation ID và zero PII leaks. |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Hợp lệ toàn bộ 6/6 panel theo dashboard contract trong `config/dashboard.yaml`. |
| `pytest` | 22 passed | 25 passed | 100% tests vượt qua, đã bổ sung test case cho CCCD 12 số, thẻ tín dụng và kiểm thử tính toàn vẹn của audit log (SHA-256 tamper-evident). |
| Số traces hợp lệ | 0 | ≥ 10 traces | Đầy đủ quan hệ cây quan sát phân cấp: `lab-agent-run` ➔ `retrieval` và `generation`. |
| Số PII leak | 0 | 0 | Không còn rò rỉ PII thô (email, số điện thoại, CCCD, thẻ thanh toán đều được thay thế bằng token `[REDACTED_*]`). |
| Latency P95 / TTFT P95 | 158.0ms / 54.0ms | 156.0ms / 53.0ms | Độ trễ hệ thống ở trạng thái bình thường ổn định, cách xa ngưỡng SLO 3000ms. |
| Retrieval success rate | 100% | 100% | RAG vector store tìm kiếm context thành công 10/10 truy vấn thử nghiệm. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:**
  Trong `CorrelationIdMiddleware` (`app/middleware.py`), trước khi xử lý mỗi request, gọi `clear_contextvars()` để dọn sạch context của request trước đó, tránh hiện tượng context leakage giữa các coroutine bất đồng bộ. Middleware kiểm tra header `x-request-id`: nếu client truyền vào và không rỗng thì sử dụng, ngược lại tự động sinh một mã định danh ngẫu nhiên chuẩn `req-<8-hex>` thông qua `f"req-{uuid.uuid4().hex[:8]}"`. Mã này được gán vào `request.state.correlation_id` và đồng thời bind vào contextvars thông qua `bind_contextvars(correlation_id=correlation_id)`. Kết thúc request, middleware tính toán thời gian phản hồi thực tế và gắn hai header `x-request-id` và `x-response-time-ms` vào HTTP response trả về cho client.
- **Các metadata được ghi vào structured log:**
  Tại hàm xử lý `/chat` (`app/main.py`), trước khi gọi log `request_received`, toàn bộ metadata ngữ cảnh của request được đưa vào contextvars bằng `bind_contextvars`:
  - `user_id_hash`: băm SHA-256 mã hóa 1 chiều lấy 12 ký tự đầu `hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]`, bảo đảm không lưu user_id thô.
  - `session_id`: mã phiên hội thoại của người dùng.
  - `feature`: tên chức năng nghiệp vụ (ví dụ `qa`, `summary`, `refund`).
  - `model`: mã định danh mô hình AI (`claude-sonnet-4-5`).
  - `env`: môi trường hoạt động lấy từ biến môi trường (`dev`).
  Nhờ cơ chế contextvars của structlog, toàn bộ các metadata này sẽ tự động xuất hiện ở mọi event log tiếp theo (`request_received`, `response_sent`, `request_failed`) trong cùng một vòng đời request.
- **Cách bảo đảm PII được scrub trước khi ghi:**
  Cấu hình hàm `scrub_event` trong `app/logging_config.py` và đăng ký trực tiếp vào mảng processors của structlog, đứng trước `JsonlFileProcessor()` và `JSONRenderer()`. Hàm `_scrub_value` duyệt đệ quy qua toàn bộ các trường trong `event_dict` (cả payload, event name và các trường lồng nhau), áp dụng các biểu thức chính quy (regular expressions) từ `PII_PATTERNS` trong `app/pii.py` để che chắn:
  - Email: `[\w\.-]+@[\w\.-]+\.\w+` ➔ `[REDACTED_EMAIL]`
  - Số điện thoại VN: `(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)` ➔ `[REDACTED_PHONE_VN]`
  - CCCD 12 số: `\b\d{12}\b` ➔ `[REDACTED_CCCD]`
  - Thẻ tín dụng/ghi nợ: `\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b` ➔ `[REDACTED_CREDIT_CARD]`
- **Cách kiểm chứng kết quả:**
  - Chạy `python scripts/validate_logs.py` đạt điểm số tối đa 100/100, xác nhận 0 PII leak detected và 10/10 unique correlation IDs.
  - Gửi request thử nghiệm với ID `req-1a2b3c4d` và in log JSON: kiểm tra đầy đủ các trường `ts`, `level`, `service`, `event`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, `latency_ms`.
  - Gửi request chứa cả 4 loại PII thô (`a@b.vn 0901234567 001099012345 4111 1111 1111 1111`): kiểm tra log đầu ra xác nhận 100% các chuỗi PII đã được thay bằng các thẻ token `[REDACTED_*]`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:**
  Tạo project riêng tên `day13-k4-l3b-2A202602864` trên Langfuse Cloud, thiết lập các biến môi trường `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL` trong `.env`. Mọi trace sinh ra từ ứng dụng đều mang các thẻ tag `["lab", feature, model]` và metadata mang đúng `correlation_id` khớp từng ký tự với log local.
- **Cấu trúc root/retrieval/generation observations:**
  Cây quan sát phân cấp tuân thủ đúng kiến trúc:
  ```text
  day13-agent-request (trace)
  └── lab-agent-run (agent root span)
      ├── retrieval (retriever child span - tìm kiếm context RAG)
      └── generation (generation child span - gọi LLM sinh câu trả lời)
  ```
  - `retrieval`: được đánh dấu bằng decorator `@observe(name="retrieval", as_type="retriever", capture_input=False, capture_output=False)` trên hàm `retrieve()` trong `app/mock_rag.py`.
  - `generation`: được đánh dấu bằng decorator `@observe(name="generation", as_type="generation", capture_input=False, capture_output=False)` trên hàm `FakeLLM.generate()` trong `app/mock_llm.py`. Trong hàm này, thông tin chi tiết về `model`, `usage_details` (input_tokens, output_tokens, total), `cost_details` và prompt link được cập nhật qua `update_current_generation`.
- **Cách nối trace với log:**
  Cả structured log và Langfuse trace đều chia sẻ cùng một `correlation_id`. Trong structured log, trường này được gắn cố định vào mọi record. Trong trace, `correlation_id` được truyền vào `propagate_attributes(metadata={"correlation_id": correlation_id})`. Nhờ đó, khi một dòng log có dấu hiệu chậm hoặc lỗi, ta chỉ cần copy `correlation_id` và tìm kiếm trên giao diện Langfuse để mở đúng trace tương ứng.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1 mang labels `baseline` và `production`.
- **Version/label candidate:** Version 2 mang label `candidate` (bổ sung chỉ dẫn trả lời súc tích).
- **Trace ID của mỗi version:**
  - Version 1 baseline trace ID: `5dfa26be7c1395a3edc9ebfbaa3489fb`
  - Version 2 candidate trace ID: `8ced5be4e381e6dfdbdde1a810140d25`
  - Version 1 rollback trace ID: `52b685ad14d137ec16c9f8138c33b2d0`
- **Cách promote và rollback `production`:**
  - *Promote*: Trên giao diện Langfuse Prompts, mở prompt `day13-chat`, dời nhãn `production` sang Version 2. Khởi động lại API (hoặc đợi cache TTL 60s hết hạn), ứng dụng sẽ tự động tải Version 2 để phục vụ người dùng mà không cần chỉnh sửa code.
  - *Rollback*: Khi phát hiện phiên bản mới gây regression (tăng token, tăng độ trễ), lập tức vào lại giao diện Langfuse, chuyển nhãn `production` quay trở lại Version 1 và khởi động lại API. Ứng dụng khôi phục ngay lập tức về trạng thái ổn định ban đầu.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:**
  Dashboard giám sát toàn diện được xây dựng từ nguồn dữ liệu `data/logs.jsonl` theo chuẩn `config/dashboard.yaml`, bao gồm 6 panel:
  1. *Latency percentiles and TTFT*: Vẽ biểu đồ thời gian phản hồi P50, P95, P99 và TTFT P95 (ms); có đường ngưỡng cảnh báo Threshold P95 <= 3000ms.
  2. *Request traffic*: Biểu đồ cột thể hiện lưu lượng request theo từng phút và tổng request nhận được (requests_per_minute); có ngưỡng Threshold >= 1 req/min.
  3. *Error rate and retrieval success*: Giám sát tỉ lệ lỗi HTTP 500 (ngưỡng Max 2%) và tỉ lệ truy vấn RAG context thành công (ngưỡng Min 90%).
  4. *Cost over time*: Theo dõi chi phí tích lũy theo thời gian tính bằng USD; có đường giới hạn ngân sách hàng ngày Threshold <= $2.50.
  5. *Input and output tokens*: Thống kê tổng số lượng token đầu vào (Tokens In) và token đầu ra (Tokens Out); có ngưỡng trần Threshold <= 50,000 tokens.
  6. *Quality proxy*: Đo lường điểm chất lượng trung bình của câu trả lời tự động; có đường sàn chất lượng tối thiểu Threshold >= 0.75.
- **SLO và lý do chọn:**
  Primary SLO được định nghĩa là `fast_successful_requests`: Trong khoảng thời gian rolling 28 ngày, tối thiểu **99.5%** tổng số request nhận vào (`request_received`) phải phản hồi thành công (`response_sent`) với thời gian phản hồi `latency_ms <= 3000ms`.
  *Lý do chọn:* Baseline của hệ thống trong điều kiện bình thường đạt P95 latency ~158ms và TTFT P95 ~54ms. Ngưỡng 3000ms là đủ rộng để dung nạp các câu hỏi dài hoặc tác vụ suy luận phức tạp, nhưng sẽ lập tức kích hoạt cảnh báo khi xuất hiện tắc nghẽn nghiêm trọng (ví dụ sự cố RAG vector store bị trễ 2500ms làm latency vượt ngưỡng 2700-3100ms).
- **Cách tính error budget:**
  Mục tiêu SLO là 99.5%, do đó Error Budget cho phép là `100% - 99.5% = 0.5%`.
  Nếu hệ thống tiếp nhận khoảng **10,000 requests** trong cửa sổ 28 ngày, thì Error Budget tương ứng là:
  $$\text{Error Budget} = 10,000 \times 0.5\% = 50 \text{ requests}$$
  Nghĩa là trong suốt 28 ngày, tối đa chỉ có 50 request được phép bị lỗi (HTTP 500) hoặc có thời gian phản hồi vượt quá 3000ms.
- **Ba alert và runbook tương ứng:**
  Ba cảnh báo dựa trên triệu chứng (symptom-based alerts) đã được cấu hình trong `config/alert_rules.yaml` và viết runbook chi tiết tại `docs/alerts.md`:
  1. `HighLatencyTailP95`: P95 latency vượt quá 3000ms liên tục trong 5 phút (Severity: `warning`, Kênh: Slack `#k4-l3b-alerts`, Runbook: `docs/alerts.md#alert-1`).
  2. `HighApiErrorRate`: Tỉ lệ lỗi toàn hệ thống vượt quá 2% liên tục trong 3 phút (Severity: `critical`, Kênh: Slack `#k4-l3b-alerts`, Runbook: `docs/alerts.md#alert-2`).
  3. `LowRetrievalSuccessRate`: Tỉ lệ tìm kiếm tài liệu RAG thành công giảm dưới 90% liên tục trong 5 phút (Severity: `warning`, Kênh: Slack `#k4-l3b-alerts`, Runbook: `docs/alerts.md#alert-3`).

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** `2026-09-30 04:28:00 UTC` đến `2026-09-30 04:29:35 UTC` (tương ứng `11:28:00` đến `11:29:35 GMT+7`).
- **Triệu chứng từ metrics:**
  - Theo dõi trên biểu đồ runtime metric (`evidence/12-incident-metric.png`), độ trễ P95 ở trạng thái bình thường ổn định ở mức ~176ms.
  - Khi bắt đầu kích hoạt sự cố và chạy tải challenge gồm 5 queries đồng thời (`--challenge --concurrency 5`), P95 Latency tăng vọt lên đỉnh điểm **2660ms**, vượt xa ngưỡng cảnh báo sự cố của challenge (`latency_threshold_ms: 2000`) và vi phạm ngưỡng cảnh báo SLO hệ thống (3000ms).
  - Chỉ số TTFT (Time to First Token) duy trì ổn định ở mức ~51–53ms (không tăng so với baseline ~50–54ms), chứng minh kết nối ASGI và chunk đầu tiên không bị nghẽn mạng hay nghẽn tầng gateway.
  - Tỉ lệ thành công của API vẫn giữ vững 100%, không phát sinh lỗi HTTP 500 hay exception bị rò rỉ ra client.
- **Log line và correlation ID liên quan:**
  - Qua rà soát structured log trong file `data/logs.jsonl` tại thời điểm xảy ra sự cố (`evidence/13-incident-log.png`), phát hiện chuỗi request mang correlation ID bất thường. Tiêu biểu là request:
    - **Correlation ID:** `req-62659a98`
    - **Session ID:** `k4-l3b-challenge-s04`
    - **User ID Hash:** `c3a24a72d92a` (thuộc user `k4-l3b-u04`)
    - **Feature:** `monitoring`
    - **Latency:** `latency_ms: 2654` | **TTFT:** `ttft_ms: 52`
  - Dòng log trích xuất nguyên văn:
    ```json
    {"service": "api", "latency_ms": 2654, "ttft_ms": 52, "tokens_in": 36, "tokens_out": 131, "cost_usd": 0.002073, "quality_score": 0.9, "tool_name": "retrieval", "tool_success": true, "payload": {"answer_preview": "Starter answer. You should improve this output logic and add better quality chec..."}, "event": "response_sent", "correlation_id": "req-62659a98", "feature": "monitoring", "model": "claude-sonnet-4-5", "user_id_hash": "c3a24a72d92a", "env": "dev", "session_id": "k4-l3b-challenge-s04", "level": "info", "ts": "2026-09-30T04:29:07.719708Z"}
    ```
  - Nhận xét từ log: `ttft_ms` chỉ 52ms nhưng `latency_ms` lên tới 2654ms, xác nhận độ trễ xảy ra hoàn toàn trong nội bộ quá trình xử lý của backend.
- **Trace ID và span gây ảnh hưởng:**
  - Sử dụng correlation ID `req-62659a98` tra cứu trên dashboard Langfuse (`evidence/14-incident-trace.png`):
    - **Trace ID:** `d0e1f84ca008a3cd00c2641ac988c6b6`
    - **Root span (`lab-agent-run`):** Tổng thời gian thực thi là **2.655s**.
    - **Retriever span con (`retrieval`):** Mất tới **2.501s** (chiếm tới **94.2%** tổng thời gian xử lý toàn bộ request).
    - **Generation span con (`generation`):** Chỉ mất **153ms**, số lượng token và chi phí sinh câu trả lời hoàn toàn ở mức bình thường.
- **Root cause:**
  - Nguyên nhân gốc rễ bắt nguồn từ độ trễ truy vấn downstream của kho lưu trữ vector (Vector Database / Document Retrieval Service). Khi sự cố `rag_slow` được kích hoạt (mô phỏng trong `app/mock_rag.py`), module `retrieve()` bị nghẽn kết nối / chờ đợi phản hồi trong 2500ms, khiến toàn bộ tiến trình RAG pipeline bị kéo dài, dẫn tới vi phạm độ trễ SLO.
- **Fix action:**
  - Vô hiệu hóa cờ sự cố lập tức bằng cách gọi API điều khiển quản trị: `POST /incidents/rag_slow/disable`.
  - Khôi phục downstream service: Tái cấu hình connection pool cho vector database, kiểm tra tình trạng tải CPU/Memory trên cụm vector nodes, tối ưu hóa chỉ mục tìm kiếm tương đồng (HNSW / IVF-PQ index) và khởi động thêm read-replica để chia sẻ tải truy vấn vector.
- **Preventive measure:**
  - *Retrieval Timeout & Circuit Breaker:* Thiết lập hard timeout cho lệnh gọi retrieval (ví dụ: tối đa 1000ms). Nếu retrieval vượt quá 1000ms hoặc gặp lỗi liên tiếp, kích hoạt circuit breaker chuyển sang fallback mechanism (trả lời trực tiếp dựa trên LLM parametric knowledge hoặc báo người dùng thử lại).
  - *Multi-tier Caching:* Áp dụng semantic cache (Redis) lưu trữ kết quả tìm kiếm ngữ cảnh cho các truy vấn tương đồng nhằm giảm số lần truy vấn trực tiếp vào vector database.
  - *Phân rã Alert theo Span:* Thiết lập rule cảnh báo sớm dựa trên độ trễ của riêng tầng retriever (`RetrieverLatencyP95 > 1000ms` trong 3 phút) thay vì chỉ chờ đợi alert độ trễ tổng của API (`HighLatencyTailP95`), giúp đội ngũ SRE phát hiện tắc nghẽn downstream trước khi gây ảnh hưởng tới trải nghiệm người dùng cuối.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:**
  Quyết định thiết kế bộ lọc PII scrubbing theo mô hình đệ quy ở cấp độ Structlog Processor (ngay trước khi ghi file/serialize JSON). Lý do: Thay vì bắt buộc từng lập trình viên phải nhớ gọi hàm làm sạch dữ liệu tại tầng controller/service (rất dễ quên và gây rò rỉ khi mở rộng tính năng), việc đặt scrubber tại processor đảm bảo 100% dữ liệu xuất ra log file luôn được bảo vệ tuyệt đối theo nguyên tắc Zero-trust PII.
- **Một lỗi/blocker đã gặp:**
  Khi chạy `scripts/validate_logs.py` lần đầu sau khi sửa code, validator vẫn tính điểm thấp (chỉ ~30/100) do trong file `data/logs.jsonl` vẫn còn lưu lại các dòng log từ phiên chạy baseline trước khi code được cập nhật.
- **Cách tìm nguyên nhân và xử lý:**
  Nhận ra `validate_logs.py` đọc toàn bộ lịch sử trong `data/logs.jsonl`, tôi đã di chuyển file log baseline ra ngoài thư mục repo (`mv data/logs.jsonl ../logs-cp0-baseline.jsonl`), khởi động lại API server và chạy lại bộ test `scripts/load_test.py`. Kết quả đo đạt điểm tuyệt đối 100/100.
- **Cách hiểu luồng Metrics → Logs → Traces:**
  - **Metrics (Triệu chứng):** Cung cấp bức tranh toàn cảnh cấp cao theo chuỗi thời gian, giúp phát hiện sớm hệ thống đang bất thường ở đâu (độ trễ tăng, lỗi tăng, token vọt) và xác định chính xác khoảng thời gian bắt đầu xảy ra sự cố.
  - **Logs (Ngữ cảnh request):** Thu hẹp phạm vi điều tra vào các request cụ thể trong khoảng thời gian xảy ra sự cố thông qua việc lọc dữ liệu structured log, từ đó thu thập được `correlation_id`, tham số đầu vào và mã lỗi.
  - **Traces (Căn nguyên):** Dùng `correlation_id` để tra cứu trace tương ứng trên hệ thống quan sát phân tán, bóc tách thời gian thực thi của từng span con (`retrieval` vs `generation`), chỉ ra chính xác dòng code, câu truy vấn database hay lệnh gọi mô hình là nguyên nhân gốc rễ (Root Cause).
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:**
  Trong vận hành hệ thống AI/LLMOps, prompt đóng vai trò quyết định tới hành vi của mô hình. Việc quản lý phiên bản prompt và thiết lập cơ chế rollback nhanh cho phép đội ngũ kỹ thuật can thiệp tức thời khi một prompt mới gây bùng nổ token/cost hoặc làm suy giảm chất lượng câu trả lời mà không phải chờ đợi quy trình build/deploy mã nguồn kéo dài. Kết hợp với SLO và Error Budget, đội ngũ có căn cứ định lượng rõ ràng để quyết định khi nào cần đóng băng cập nhật prompt nhằm bảo vệ trải nghiệm của người dùng.
- **Điều quan trọng nhất đã học:**
  Nắm vững quy trình quan sát chuẩn 3 trụ cột (Metrics, Logs, Traces) và tư duy gán nhãn tương quan `correlation_id` xuyên suốt từ lúc HTTP request vào middleware đến khi gọi LLM và xuất log.
- **Tính năng mở rộng (Bonus +10 điểm):**
  1. *Automation (+5 điểm):*
     - `scripts/scan_secrets_pii.py`: Script quét mã nguồn tự động trước khi commit nhằm phát hiện rò rỉ secret key (Langfuse key, API key) và PII thô (CCCD, Credit Card).
     - `scripts/generate_dashboard.py`: Công cụ tự động sinh báo cáo dashboard từ structured log sang định dạng HTML tương tác và render ảnh PNG chất lượng cao.
  2. *Tamper-evident Audit Logging (+5 điểm):*
     - `app/audit.py` & `scripts/query_audit.py`: Hệ thống audit log chuyên dụng ghi lại mọi thao tác quản trị can thiệp hệ thống (enable/disable incidents) với schema đầy đủ (`ts`, `actor`, `action`, `target`, `details`, `retention_days`), chuỗi băm mật mã SHA-256 chống sửa đổi dữ liệu (tamper-evident checksums), kiểm tra retention (90 ngày) và công cụ CLI truy vấn/xác minh tính toàn vẹn dữ liệu. Đã bổ sung unit test `tests/test_audit.py` pass 100%.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:**
  Toàn bộ các Checkpoint từ CP1 đến CP4 cùng các tính năng Bonus đều đã hoàn thành xuất sắc 100%, vượt qua tất cả các bài kiểm tra kỹ thuật (25/25 pytest passed, 100/100 log validator, 6/6 dashboard validator, 0 secret/PII leaks).

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA của chính học viên.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối trong `submission/evidence/`.
- [x] Incident evidence nối đúng metric → log → trace (Đã hoàn thiện ở CP3).
- [x] Không commit secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] Repository chạy lại được theo README bằng môi trường `uv`.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
