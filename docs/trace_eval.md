# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyen Hoang Duy
> **Mã Sinh Viên / Mã Học viên:** 2A202602751
> **Chủ đề Lựa chọn:** Gợi ý 4.2 — Trợ lý Dịch vụ Khách hàng VinBus: tra cứu lộ trình xe buýt điện và đăng ký vé tháng.

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | **5 / 5** | Với yêu cầu đi từ điểm A đến B rồi đăng ký vé tháng, Agent phải nhận diện điểm đi/đến, tra các tuyến phù hợp, đối chiếu tuyến với phạm vi vé, xác nhận thông tin hành khách và mới tạo đăng ký. Các bước có thứ tự; một FAQ tĩnh không đáp ứng được luồng này. |
| **2. Tool Interaction** | **5 / 5** | Cần tối thiểu hai Tool qua MCP: `route_lookup` để truy vấn dữ liệu tuyến/trạm và `monthly_pass_register` để tạo đăng ký vé tháng. Dữ liệu lộ trình và trạng thái đăng ký là dữ liệu có cấu trúc, không nên để LLM tự nhớ hoặc tự tạo. |
| **3. Dynamic Decision** | **4 / 5** | Agent chỉ đề xuất hoặc đăng ký loại vé sau khi quan sát kết quả tra tuyến: ví dụ, OCP2 chỉ phục vụ nội khu Ocean Park 2,3; yêu cầu qua Royal City cần OCT1. Trường hợp không có tuyến/thiếu thông tin phải hỏi lại thay vì gọi Tool đăng ký. Điểm chưa là 5 vì phạm vi lab dùng snapshot mock, chưa có dữ liệu vị trí xe và thanh toán thời gian thực. |
| **4. Long Horizon Goal** | **4 / 5** | Mục tiêu “đi được tuyến phù hợp và có vé tháng hợp lệ” được giữ qua nhiều lượt: tra cứu, làm rõ lựa chọn, thu thập dữ liệu đăng ký, tạo mã đăng ký, rồi thông báo kết quả. Tuy nhiên đây là tác vụ ngắn theo phiên, chưa phải Agent tự chủ theo dõi dài ngày hay tự gia hạn vé. |
| **TỔNG ĐIỂM AGENTIC FIT** | **18 / 20** | *18 > 12, nên bài toán phù hợp triển khai ReAct Agent System. Các câu hỏi giới thiệu/FAQ thuần túy vẫn nên dùng Chatbot Baseline để phản hồi nhanh và tiết kiệm token.* |

---

### Ghi chú dữ liệu giả lập cho lab

- Dataset offline tại `config/mock_vinbus_data.json` chỉ là snapshot phục vụ kiểm thử; Agent **không** được khẳng định đây là dữ liệu vận hành thời gian thực hoặc đăng ký vé thật.
- Tám tuyến được mô phỏng là OCP1, OCP2, OCT1, OCT2, E01, E02, E03 và E05. OCP/OCT mô phỏng tuyến miễn phí để tra cứu; chỉ E01/E02/E03/E05 có luồng đăng ký vé tháng giả lập. Thông tin tuyến được đối chiếu từ website/bản đồ VinBus chính thức ngày 13/09/2026; nguồn URL và mốc hiệu lực được giữ ngay trong dataset.
- Trước khi tư vấn cho khách thật, cần tra lại trên [bản đồ VinBus](https://maps.vinbus.vn/hn) hoặc ứng dụng VinBus vì lộ trình, giờ chạy và giá vé có thể thay đổi.

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
[
  {
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "tool_name": "academic_query",
    "arguments": {
      "student_id": "SV2026001"
    },
    "observation": {
      "status": "SUCCESS",
      "student_id": "SV2026001",
      "data": {
        "full_name": "Nguyễn Văn An",
        "gpa": 3.85
      }
    },
    "latency_ms": 120.5
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [ ] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** ___ / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** ___ lượt.
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
