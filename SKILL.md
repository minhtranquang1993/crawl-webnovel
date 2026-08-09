---
name: crawl-webnovel
description: >-
  Cào dữ liệu truyện từ webnovel.vn: vào từng URL truyện, tải ảnh bìa (đặt tên theo slug URL),
  lấy tên truyện + danh mục (thể loại), rồi gom/merge vào file truyen-data.json.
  Tự tìm thư mục Downloads của máy đang chạy (cross-platform Windows/macOS/Linux) — để ở máy nào thì lưu vào Downloads máy đó.
  Trigger: "/crawl-webnovel", "crawl webnovel", "cào data webnovel", "cào ảnh + danh mục webnovel",
  hoặc khi user gửi danh sách URL webnovel.vn kèm yêu cầu tải ảnh + lấy thể loại + ghi JSON.
argument-hint: "<url> [<url> ...] | --file urls.txt"
---

# /crawl-webnovel — Cào ảnh + danh mục truyện Webnovel.vn

Tự động cào dữ liệu từ [webnovel.vn](https://webnovel.vn/): mỗi URL truyện → tải **ảnh bìa** + lấy **tên truyện** + **danh mục** → ghi vào **1 file JSON**.

## Output (cấu trúc thư mục)

Mặc định lưu vào thư mục Downloads của máy đang chạy (tự detect):

```
<Downloads>/webnovel/
├── hinh-anh-ten-truyen/          # ảnh bìa, tên file = slug URL (vd huyen-giam-tien-toc.webp)
└── truyen-data.json              # mảng dữ liệu tất cả truyện
```

- **Windows:** `C:\Users\<tên>\Downloads\webnovel\`
- **macOS:** `/Users/<tên>/Downloads/webnovel/`

> Skill dùng `~/Downloads` nên **để trên máy nào thì tự lấy Downloads của máy đó** — không cần sửa đường dẫn khi chuyển giữa Windows và MacBook.

Mỗi truyện là 1 object trong JSON:

```json
{
  "tu_khoa": "Mạnh Lên Từ Huyện Lệnh Bắt Đầu",
  "slug": "manh-len-tu-huyen-lenh-bat-dau",
  "link_truyen": "https://webnovel.vn/manh-len-tu-huyen-lenh-bat-dau/",
  "anh_local": "hinh-anh-ten-truyen/manh-len-tu-huyen-lenh-bat-dau.webp",
  "anh_url": "https://cdn.webnovel.vn/img/052026/manh-len-tu-huyen-lenh-bat-dau.webp?t=1777981236",
  "danh_muc": ["Tiên Hiệp", "Xuyên Không", "Huyền Huyễn", "Hệ Thống"],
  "tac_gia": "Dã Hỏa Đông Vọng",
  "lo": "01"
}
```

> **`lo`** = nhãn lô truyện của đợt crawl (do `--lo` truyền vào). Dùng để `/content-webnovel` chỉ bốc truyện của lô đang active. 1 slug = 1 record; crawl lại slug cũ với `--lo` khác sẽ cập nhật `lo` sang lô mới.

## When to Use

- User gửi 1 hoặc nhiều URL truyện webnovel.vn, muốn tải ảnh bìa + lấy thể loại + ghi JSON.
- User đã có file danh sách URL, muốn cào hàng loạt.
- Bổ sung thêm truyện vào bộ dữ liệu đã cào trước đó (skill tự merge, không tải lại ảnh đã có).

## How to Run

Chạy script Python (cross-platform). Có thể truyền URL trực tiếp hoặc qua file:

```bash
# 1 hoặc nhiều URL trực tiếp (--lo BẮT BUỘC)
python "<skill_dir>/scripts/crawl.py" "https://webnovel.vn/tien-nghich/" "https://webnovel.vn/pham-nhan-tu-tien/" --lo 01

# Nhiều URL từ file (mỗi dòng 1 URL)
python "<skill_dir>/scripts/crawl.py" --file urls.txt --lo 02

# Đổi thư mục gốc (mặc định ~/Downloads/webnovel)
python "<skill_dir>/scripts/crawl.py" --file urls.txt --lo 02 --out "/duong/dan/khac"
```

> **`--lo <nhãn>` bắt buộc** — gắn nhãn lô cho mọi truyện crawl trong lần chạy đó (vd `01`, `02`, `2026-08`). Thiếu `--lo` script dừng và báo lỗi, KHÔNG tự đoán. Dữ liệu lô cũ trong JSON không bị đụng; chỉ record cùng slug được cập nhật `lo` mới.

`<skill_dir>`:
- macOS: `~/.claude/skills/crawl-webnovel`
- Windows: `%USERPROFILE%\.commandcode\skills\crawl-webnovel`

> **Windows:** nếu console báo lỗi in tiếng Việt (`UnicodeEncodeError`), đặt `PYTHONIOENCODING=utf-8` trước lệnh. File JSON vẫn luôn ghi đúng UTF-8 dù console không in được.

## Workflow cho Agent

Khi user yêu cầu cào data webnovel:

1. **Thu thập URL** từ prompt (hoặc file user chỉ). Nếu nhiều URL → ghi ra file tạm rồi chạy `--file` cho gọn.
2. **Chạy** `scripts/crawl.py` với danh sách URL. Không cần chỉ định `--out` trừ khi user muốn lưu chỗ khác — mặc định đã là `~/Downloads/webnovel`.
3. **Đọc output** của script (in ra từng dòng trạng thái + dòng tổng kết cuối).
4. **Báo lại** cho user: tổng số truyện trong JSON, số mới/cập nhật, số bỏ qua/lỗi, và đường dẫn file JSON.

Trạng thái mỗi dòng:
- `IMG` = tải ảnh mới thành công · `HAVE` = ảnh đã có sẵn (bỏ qua tải)
- `-> mới` = thêm truyện mới vào JSON · `-> cập nhật` = truyện đã có, cập nhật lại field
- `SKIP` = trang danh mục/thể loại (không có ảnh bìa riêng) → bỏ qua, đúng dự kiến
- `FAIL` = tải trang hoặc tải ảnh lỗi → báo user URL đó

## Cơ chế cào (kỹ thuật)

- **Ảnh bìa** lấy từ thẻ `<meta property="og:image">`. Tên file trên CDN thường trùng slug URL.
- **Tên truyện** lấy từ `<meta property="og:title">`.
- **Tác giả** lấy từ thẻ `<a>` đầu tiên trong `<p class="book-detail__author">`.
- **Danh mục** lấy từ các thẻ `<a class="genre" title="...">` trong khối `book-detail__genres`.
- **Slug** = path đầu tiên sau `webnovel.vn/` (URL chương con như `/…/chuong-11/` tự quy về truyện cha).
- **Trang danh mục/thể loại** (vd `/truyen-duoc-xem-nhieu-nhat/`, `/vong-du/`) không có `og:image` → tự bỏ qua.

## Đặc điểm an toàn khi chạy lại

- Ảnh đã tồn tại trên đĩa → **không tải lại**.
- Truyện đã có trong JSON (theo `slug`) → **cập nhật** thay vì tạo trùng.
- URL trùng slug trong cùng lần chạy → chỉ xử lý 1 lần.
- Chạy bổ sung nhiều đợt: gọi lại script với URL mới, dữ liệu cũ được giữ nguyên và merge thêm.

## Đồng bộ sang skill content-webnovel

Sau khi ghi `~/Downloads/webnovel/truyen-data.json`, script **tự copy 1 bản** sang mọi nơi skill content-webnovel được cài (bỏ qua nơi chưa cài):

```
~/.commandcode/skills/content-webnovel/data/truyen-data.json
~/.claude/skills/content-webnovel/data/truyen-data.json
~/.gemini/antigravity/skills/content-webnovel/data/truyen-data.json
```

Skill `/content-webnovel` đọc file này để chọn đúng truyện theo thể loại khi viết `pbn toplist` và lấy `slug` ghép URL ảnh PBN. Chạy crawl xong là content-webnovel có data mới ngay — không cần sync tay. Nếu copy fail (thư mục skill không tồn tại), script in `WARN` nhưng vẫn giữ bản Downloads.

## Rules

- **`--lo` bắt buộc** — thiếu thì dừng, không đoán nhãn lô. Mọi record crawl trong lần chạy được gắn `lo` đó.
- Chỉ cào webnovel.vn. URL không thuộc site này → slug rỗng, bỏ qua.
- **Không bịa** danh mục/tên truyện — chỉ lấy từ HTML thật. Trang không bóc được ảnh bìa thì SKIP (coi như trang danh mục).
- Giữ nguyên tiếng Việt có dấu trong JSON (UTF-8).
- Không tải lại ảnh/không tạo bản ghi trùng khi chạy lại.

## Scripts

- `scripts/crawl.py` — script chính. Fetch bằng urllib (browser UA), trích og:image/og:title/genres, tải ảnh theo slug, merge vào `truyen-data.json`. Tự tìm `~/Downloads/webnovel`. Chỉ dùng thư viện chuẩn Python (không cần cài thêm gì).

## Category
data-crawl
