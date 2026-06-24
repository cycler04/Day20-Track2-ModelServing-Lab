# Reflection — Lab 20 (Personal Report)

> **Đây là báo cáo cá nhân.** Mỗi học viên chạy lab trên laptop của mình, với spec của mình. Số liệu của bạn không so sánh được với bạn cùng lớp — chỉ so sánh **before vs after trên chính máy bạn**. Grade rubric tính theo độ rõ ràng của setup + tuning của bạn, không phải tốc độ tuyệt đối.

---

**Họ Tên:** Nguyễn Tiến Dũng
**Cohort:** A20-K1
**Ngày submit:** 2026-06-24

---

## 1. Hardware spec (từ `00-setup/detect-hardware.py`)

- **OS:** Windows 11 (AMD64)
- **CPU:** 11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz
- **Cores:** 4 physical / 8 logical
- **CPU extensions:** AVX2 / AVX-512 / FMA / F16C / OPENMP
- **RAM:** 15.7 GB
- **Accelerator:** CPU only (NVIDIA GeForce MX350 2GB present but build fell back to CPU)
- **llama.cpp backend đã chọn:** CPU (AVX2/AVX-512)
- **Recommended model tier:** Qwen2.5-1.5B-Instruct

**Setup story** (≤ 80 chữ):
Thiết lập trên Windows native. Do máy thiếu `cmake` trong PATH nên cài đặt `llama-cpp-python` bản CPU-only từ prebuilt wheel. Model 1.5B tự động tải về và chạy mượt mà. Port 8080 bị chiếm bởi EnterpriseDB (Apache httpd) nên đổi cổng server sang 8089.

---

## 2. Track 01 — Quickstart numbers (từ `benchmarks/01-quickstart-results.md`)

| Model | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode rate (tok/s) |
|---|--:|--:|--:|--:|--:|
| qwen2.5-1.5b-instruct-q4_k_m.gguf | 3065 | 334 / 403 | 108.2 / 117.1 | 7025 / 7743 / 7768 | 9.2 |
| qwen2.5-1.5b-instruct-q2_k.gguf | 1599 | 417 / 528 | 97.5 / 128.8 | 6582 / 8519 / 8582 | 10.3 |

**Một quan sát** (≤ 50 chữ):
Q4_K_M chỉ chậm hơn Q2_K khoảng 10% (9.2 vs 10.3 tok/s) nhưng chất lượng câu trả lời tốt hơn vượt trội. Rất đáng đánh đổi sự suy giảm tốc độ nhỏ này để lấy độ chính xác cao.

---

## 3. Track 02 — llama-server load test

| Concurrency | Total RPS | TTFB P50 (ms) | E2E P95 (ms) | E2E P99 (ms) | Failures |
|---|---|---|---|---|---|
| 10 | 0.22 | 29000 | 50000 | 50000 | 0 (0.00%) |
| 50 | 0.23 | 25000 | 39000 | 39000 | 0 (0.00%) |

**Batching observation** (từ `record-metrics.py`):
peak `llamacpp:n_busy_slots_per_decode` / `requests_processing` ở concurrency 50 = `3.76` / `4`, nghĩa là server native `llama-server` đã kích hoạt continuous batching (xử lý đồng thời tối đa 4 slots). Dưới tải concurrency 50, độ trễ P50 là 25s, tốt hơn so với 29s ở concurrency 10 nhờ cơ chế ghép lô song song và tối ưu hàng đợi (deferred requests lên tới 46 yêu cầu mà không bị crash).

---

## 4. Track 03 — Milestone integration

- **N16 (Cloud/IaC):** stub: localhost only
- **N17 (Data pipeline):** stub: in-memory dict
- **N18 (Lakehouse):** stub: SQLite
- **N19 (Vector + Feature Store):** stub: TOY_DOCS

**Nơi tốn nhiều ms nhất** trong pipeline (đo bằng `time.perf_counter` trong `pipeline.py`):

- embed: 0.0 ms (stub)
- retrieve: 0.1 ms
- llama-server: 8385.5 ms (trung bình 3 truy vấn)

**Reflection** (≤ 60 chữ):
Bottleneck chính xác nằm ở `llama-server` (chiếm >99.9% thời gian). Thời gian truy xuất thông tin (retrieve) là không đáng kể. Điều này khớp với kỳ vọng vì xử lý LLM trên CPU rất tốn tài nguyên.

---

## 5. Bonus — The single change that mattered most

**Change:** Tối ưu hóa số luồng thực thi (`n_threads`) bằng cách giới hạn ở số luồng logic tối đa (8 luồng), tránh việc oversubscribe lên 16 luồng ảo.

**Before vs after** (paste 2-3 dòng từ sweep output):

```
before: t=16  -> 15.1 tok/s
after:  t=8   -> 21.1 tok/s
speedup: ~1.40×
```

**Tại sao nó work** (1–2 đoạn ngắn — đây là phần grader đọc kỹ nhất):

Tốc độ giải mã (decode) của LLM bị giới hạn bởi băng thông bộ nhớ (memory-bandwidth bound) hơn là năng lực tính toán thuần túy (compute bound). Khi oversubscribe lên 16 luồng (vượt quá 8 luồng logic của CPU), các luồng ảo phải tranh chấp các kênh truyền tải dữ liệu của bộ nhớ RAM và bộ đệm cache, dẫn đến hiện tượng trễ cổ chai bộ nhớ và làm chậm tiến trình giải mã.

Bằng cách giới hạn số luồng tối đa bằng đúng số nhân logic (t=8), CPU hoạt động ở hiệu suất tối đa mà không bị phân mảnh hay tranh chấp tài nguyên, giúp tối ưu hóa băng thông truyền tải dữ liệu từ RAM vào CPU, tăng tốc độ giải mã lên 40% (từ 15.1 lên 21.1 tok/s).

---

## 6. (Optional) Điều ngạc nhiên nhất

Sự chênh lệch tốc độ giải mã giữa Q4_K_M và Q2_K trên CPU là rất nhỏ (khoảng 5%). Việc giảm lượng tử hóa xuống Q2_K hầu như không đem lại lợi thế về tốc độ trên CPU Gen 11 này, chỉ giúp tiết kiệm RAM và ổ đĩa.

---

## 7. Self-graded checklist

- [x] `hardware.json` đã commit
- [x] `models/active.json` đã commit (hoặc paste path snapshot vào section 1)
- [x] `benchmarks/01-quickstart-results.md` đã commit
- [x] `benchmarks/02-server-results.md` (hoặc CSV từ `record-metrics.py`) đã commit
- [x] `benchmarks/bonus-*.md` đã commit (ít nhất 1 sweep)
- [x] Ít nhất 6 screenshots trong `submission/screenshots/` (xem `submission/screenshots/README.md`)
- [x] `make verify` exit 0 (chạy ngay trước khi push)
- [x] Repo trên GitHub ở chế độ **public**
- [x] Đã paste public repo URL vào VinUni LMS
