# YouTube Subtitle API - Tài liệu Kỹ thuật

## Tổng quan

Hệ thống xử lý phụ đề YouTube, hỗ trợ phiên âm chuẩn IPA/Pinyin/Hiragana và dịch thuật đa ngôn ngữ.

**Base URL (Public):** `https://simple-emu-vocal.ngrok-free.app`  
**Base URL (Local):** `http://localhost:8002`

> **Lưu ý Ngrok:** Khi sử dụng URL Ngrok, cần thêm header `ngrok-skip-browser-warning: true` vào mỗi request để bỏ qua màn hình cảnh báo.

---

## Ngôn ngữ hỗ trợ

| Mã ngôn ngữ | Ngôn ngữ | Phiên âm trả về |
|---|---|---|
| `en` | Tiếng Anh | IPA (ví dụ: `həˈloʊ`) |
| `ja` | Tiếng Nhật | Hiragana (ví dụ: `こんにちは`) |
| `zh` | Tiếng Trung | Pinyin có dấu (ví dụ: `nǐ hǎo`) |
| `vi` | Tiếng Việt | Giữ nguyên văn bản gốc |

---

## Endpoints

### 1. Xử lý video YouTube

Gửi yêu cầu xử lý phụ đề cho một video YouTube. Hệ thống sẽ xử lý ở chế độ nền và trả về `job_id` ngay lập tức.

**Endpoint:** `POST /youtube`

**Headers:**
```
Content-Type: application/json
ngrok-skip-browser-warning: true
```

**Request Body:**
```json
{
    "sourceurl": "https://www.youtube.com/watch?v=VIDEO_ID",
    "termlanguagecode": "en",
    "definitionlanguagecode": "vi"
}
```

| Trường | Kiểu | Bắt buộc | Mô tả |
|---|---|---|---|
| `sourceurl` | `string` | ✅ | URL đầy đủ của video YouTube |
| `termlanguagecode` | `string` | ❌ | Mã ngôn ngữ **gốc** của video. Mặc định: `"ja"` |
| `definitionlanguagecode` | `string` | ❌ | Mã ngôn ngữ **dịch sang**. Mặc định: `"vi"` |

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Job started",
    "data": {
        "job_id": "5fbbddd7-19f3-45ab-a52a-10730ac65746"
    }
}
```

---

### 2. Kiểm tra tiến trình & Lấy kết quả

Dùng `job_id` nhận được ở bước trên để kiểm tra trạng thái xử lý và nhận kết quả cuối cùng.

**Endpoint:** `GET /progress/{job_id}`

**Ví dụ:** `GET /progress/5fbbddd7-19f3-45ab-a52a-10730ac65746`

**Headers:**
```
ngrok-skip-browser-warning: true
```

**Response - Đang xử lý (Status: `processing`):**
```json
{
    "success": true,
    "status": "processing",
    "progress": 45,
    "message": null,
    "data": []
}
```

**Response - Hoàn thành (Status: `completed`):**
```json
{
    "success": true,
    "status": "completed",
    "progress": 100,
    "message": null,
    "data": [
        {
            "stt": 1,
            "starttime": "00:00:00,000",
            "endtime": "00:00:03,500",
            "content": "Hello everyone",
            "pronunciation": "həˈloʊ ˈɛvrɪˌwʌn",
            "translation": "Xin chào mọi người"
        },
        {
            "stt": 2,
            "starttime": "00:00:03,500",
            "endtime": "00:00:07,200",
            "content": "Welcome to our channel",
            "pronunciation": "ˈwɛlkəm tɪ ˈaʊər ˈtʃænəl",
            "translation": "Chào mừng đến với kênh của chúng tôi"
        }
    ]
}
```

**Response - Thất bại (Status: `failed`):**
```json
{
    "success": true,
    "status": "failed",
    "progress": 0,
    "message": "No subtitles could be generated",
    "data": []
}
```

---

## Cấu trúc dữ liệu `data[]`

Mỗi phần tử trong mảng `data` đại diện cho **một đoạn phụ đề**:

| Trường | Kiểu | Mô tả |
|---|---|---|
| `stt` | `number` | Số thứ tự (bắt đầu từ 1) |
| `starttime` | `string` | Thời điểm bắt đầu, định dạng `HH:MM:SS,mmm` |
| `endtime` | `string` | Thời điểm kết thúc, định dạng `HH:MM:SS,mmm` |
| `content` | `string` | Nội dung gốc của đoạn phụ đề |
| `pronunciation` | `string` | Phiên âm theo chuẩn tương ứng với ngôn ngữ gốc |
| `translation` | `string` | Bản dịch sang ngôn ngữ đích |

> **Lưu ý:** Các đoạn phụ đề chứa chú thích âm thanh như `[Music]`, `[Applause]` sẽ tự động bị lọc bỏ.

---

## Trạng thái Job (`status`)

| Giá trị | Ý nghĩa |
|---|---|
| `pending` | Đã nhận yêu cầu, chờ xử lý |
| `processing` | Đang xử lý |
| `completed` | Hoàn thành, `data` đã có kết quả |
| `failed` | Thất bại, xem `message` để biết nguyên nhân |

---

## Giá trị `progress` (% tiến trình)

Hệ thống cập nhật tiến trình theo giai đoạn:

| % | Giai đoạn |
|---|---|
| `0 - 5%` | Đang khởi động, xác thực URL |
| `5 - 15%` | Đang tải phụ đề từ YouTube |
| `15 - 90%` | Đang dịch thuật song song |
| `90 - 100%` | Hoàn thiện và xuất kết quả |

---

## Luồng hoạt động đề xuất (Client)

```
1. POST /youtube  ->  nhận job_id
2. Loop polling GET /progress/{job_id} mỗi 2-3 giây
3. Nếu status == "completed"  ->  đọc data[]
4. Nếu status == "failed"     ->  hiển thị message lỗi
5. Dừng polling
```

---

## Ví dụ đầy đủ

### Ví dụ với video Tiếng Anh:
```json
// POST /youtube
{
    "sourceurl": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "termlanguagecode": "en",
    "definitionlanguagecode": "vi"
}
```

### Ví dụ với video Tiếng Nhật:
```json
// POST /youtube
{
    "sourceurl": "https://www.youtube.com/watch?v=JAPAN_VIDEO_ID",
    "termlanguagecode": "ja",
    "definitionlanguagecode": "vi"
}
```

### Ví dụ với video Tiếng Trung:
```json
// POST /youtube
{
    "sourceurl": "https://www.youtube.com/watch?v=CHINA_VIDEO_ID",
    "termlanguagecode": "zh",
    "definitionlanguagecode": "vi"
}
```
