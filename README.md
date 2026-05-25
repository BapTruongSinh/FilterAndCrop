# FilterAndCrop

Ứng dụng desktop dùng để lọc ảnh và crop ảnh hàng loạt. App có 2 chức năng chính:

1. Duyệt ảnh trong một folder và chuyển ảnh bị loại sang `Deleted folder`.
2. Crop ảnh bằng chuột, lưu ảnh crop vào `Crop folder` và cập nhật tọa độ vào file CSV.

## Tải Bản Release Để Chạy Luôn

Nếu chỉ muốn dùng app và không cần cài Python:

1. Mở trang Release: <https://github.com/BapTruongSinh/FilterAndCrop/releases/latest>
2. Tải file `FilterAndCrop.exe` trong phần Assets.
3. Chạy trực tiếp file `FilterAndCrop.exe`.

Nếu Windows hiện cảnh báo bảo mật khi mở file tải từ Internet, chọn `More info` rồi `Run anyway` nếu bạn tin tưởng file release này.

## Yêu Cầu Khi Chạy Từ Source

- Windows
- Python 3.10 trở lên
- pip

## Cài Đặt Để Chạy Từ Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## Build File Exe

Chạy PyInstaller bằng file spec có sẵn:

```powershell
python -m PyInstaller --noconfirm FilterAndCrop.spec
```

Sau khi build xong, file chạy nằm tại:

```text
dist\FilterAndCrop.exe
```

## Cách Sử Dụng

Mở app, nhập 4 đường dẫn:

- `Image folder`: folder ảnh gốc cần duyệt.
- `Deleted folder`: folder nhận ảnh bị loại.
- `Crop folder`: folder lưu ảnh đã crop.
- `CSV file`: file CSV lưu tọa độ crop. Có thể chọn file CSV đã có hoặc nhập đường dẫn file mới.

Bấm `Load` để nạp danh sách ảnh. App sẽ tự tạo `Deleted folder`, `Crop folder` và thư mục cha của file CSV nếu chưa tồn tại.

Phím và thao tác:

- `Next` hoặc mũi tên phải: chuyển sang ảnh tiếp theo.
- `Back` hoặc mũi tên trái: quay lại ảnh trước.
- `Delete`, phím `Delete` hoặc `Backspace`: chuyển ảnh hiện tại sang `Deleted folder`.
- Double-click chuột trái trên ảnh, kéo và thả chuột để crop.

## Định Dạng CSV

CSV gồm các cột:

```text
image_name,folder,x1,x2,y1,y2
```

Khi load ảnh, app sẽ tự tạo hoặc cập nhật dòng CSV cho từng ảnh trong `Image folder`. Nếu ảnh đã có tọa độ hợp lệ, app vẽ khung màu xanh lá. Khi crop mới trong app, app lưu ảnh crop vào `Crop folder`, ghi đè ảnh crop cũ nếu trùng tên file và cập nhật tọa độ mới vào CSV.

## Ghi Chú Về Source

- Code chính nằm trong `app.py`.
- `FilterAndCrop.spec` dùng để build exe bằng PyInstaller.
- `requirements.txt` liệt kê thư viện cần cài đặt.
- Các hàm trong `app.py` có docstring tiếng Việt để mô tả nhiệm vụ của từng hàm.
