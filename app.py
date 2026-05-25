from __future__ import annotations

import csv
import shutil
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
CSV_COLUMNS = ["image_name", "folder", "x1", "x2", "y1", "y2"]
PATH_FIELDS = [
    ("source", "Image folder", "folder"),
    ("deleted", "Deleted folder", "folder"),
    ("crop", "Crop folder", "folder"),
    ("csv", "CSV file", "file"),
]


def is_image(path: Path) -> bool:
    """Kiểm tra đường dẫn có phải file ảnh thuộc định dạng app hỗ trợ hay không."""
    return path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS


def unique_path(path: Path) -> Path:
    """Tạo đường dẫn không trùng tên bằng cách thêm hậu tố số nếu file đã tồn tại."""
    if not path.exists():
        return path

    index = 1
    while True:
        new_path = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not new_path.exists():
            return new_path
        index += 1


def number_text(value: float) -> str:
    """Làm tròn tọa độ và chuyển thành chuỗi gọn để ghi vào CSV."""
    value = round(value, 2)
    return str(int(value)) if value.is_integer() else str(value)


class FilterAndCropApp:
    def __init__(self) -> None:
        """Khởi tạo cửa sổ chính và trạng thái xử lý ảnh."""
        self.root = tk.Tk()
        self.root.title("Filter And Crop")
        self.root.geometry("1180x820")
        self.root.minsize(920, 640)

        self.vars = {key: tk.StringVar() for key, _label, _kind in PATH_FIELDS}
        self.status_var = tk.StringVar(value="Nhap duong dan roi bam Load.")

        self.images: list[Path] = []
        self.index = 0
        self.csv_rows: dict[str, dict[str, str]] = {}
        self.current_pil: Image.Image | None = None
        self.current_photo: ImageTk.PhotoImage | None = None

        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.display_w = 0
        self.display_h = 0

        self.crop_start: tuple[int, int] | None = None
        self.crop_rect: int | None = None

        self.build_ui()

    def build_ui(self) -> None:
        """Tạo giao diện nhập đường dẫn, canvas hiển thị ảnh và các nút điều hướng."""
        root = ttk.Frame(self.root, padding=10)
        root.pack(fill=tk.BOTH, expand=True)

        path_frame = ttk.Frame(root)
        path_frame.pack(fill=tk.X)
        path_frame.columnconfigure(1, weight=1)

        for row, (key, label, kind) in enumerate(PATH_FIELDS):
            ttk.Label(path_frame, text=label, width=14).grid(row=row, column=0, sticky="w", pady=3)
            ttk.Entry(path_frame, textvariable=self.vars[key]).grid(row=row, column=1, sticky="ew", padx=(4, 6), pady=3)
            ttk.Button(path_frame, text="Browse", command=lambda k=key, t=kind: self.browse(k, t)).grid(row=row, column=2, pady=3)

        action_frame = ttk.Frame(root)
        action_frame.pack(fill=tk.X, pady=8)
        ttk.Button(action_frame, text="Load", command=self.load).pack(side=tk.LEFT)
        ttk.Label(action_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=(12, 0), fill=tk.X, expand=True)

        self.canvas = tk.Canvas(root, bg="#1f1f1f", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(root)
        button_frame.pack(fill=tk.X, pady=(8, 0))
        self.back_button = ttk.Button(button_frame, text="Back", command=self.back)
        self.next_button = ttk.Button(button_frame, text="Next", command=self.next)
        self.delete_button = ttk.Button(button_frame, text="Delete", command=self.delete_current)
        for button in (self.back_button, self.next_button, self.delete_button):
            button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.canvas.bind("<Double-Button-1>", self.start_crop)
        self.canvas.bind("<B1-Motion>", self.drag_crop)
        self.canvas.bind("<ButtonRelease-1>", self.finish_crop)
        self.canvas.bind("<Configure>", lambda _event: self.show_current())
        self.root.bind("<Left>", lambda _event: self.back())
        self.root.bind("<Right>", lambda _event: self.next())
        self.root.bind("<Delete>", lambda _event: self.delete_current())
        self.root.bind("<BackSpace>", lambda _event: self.delete_current())
        self.set_buttons()

    def browse(self, key: str, kind: str) -> None:
        """Mở hộp thoại chọn file hoặc thư mục rồi lưu kết quả vào trường tương ứng."""
        value = self.vars[key].get().strip()
        initial = str(Path(value).parent if kind == "file" and value else Path(value or Path.cwd()))
        if kind == "file":
            selected = filedialog.askopenfilename(
                initialdir=initial,
                title="Choose CSV file",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            )
        else:
            selected = filedialog.askdirectory(initialdir=initial)
        if selected:
            self.vars[key].set(selected)

    def get_path(self, key: str, label: str | None = None) -> Path:
        """Lấy đường dẫn từ giao diện, chuẩn hóa thành Path tuyệt đối và báo lỗi nếu rỗng."""
        value = self.vars[key].get().strip().strip('"')
        if not value:
            raise ValueError(f"Chua nhap {label or key}.")
        return Path(value).expanduser().resolve()

    def load(self) -> None:
        """Kiểm tra đường dẫn, nạp ảnh, đồng bộ dữ liệu CSV và hiển thị ảnh đầu tiên."""
        try:
            source = self.get_path("source", "Image folder")
            deleted = self.get_path("deleted", "Deleted folder")
            crop = self.get_path("crop", "Crop folder")
            csv_path = self.get_path("csv", "CSV file")
        except ValueError as error:
            messagebox.showerror("Invalid path", str(error))
            return

        if not source.is_dir():
            messagebox.showerror("Invalid path", f"Image folder khong ton tai:\n{source}")
            return

        deleted.mkdir(parents=True, exist_ok=True)
        crop.mkdir(parents=True, exist_ok=True)
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        self.images = sorted(path for path in source.iterdir() if is_image(path))
        self.index = 0
        self.csv_rows = self.read_csv_rows(csv_path)
        self.ensure_csv_rows(source.name)
        self.save_csv_rows(csv_path)
        self.show_current()

    def current_image(self) -> Path | None:
        """Trả về ảnh hiện tại theo chỉ số đang chọn, hoặc None nếu không có ảnh."""
        return self.images[self.index] if 0 <= self.index < len(self.images) else None

    def read_csv_rows(self, csv_path: Path) -> dict[str, dict[str, str]]:
        """Đọc file CSV hiện có và gom dữ liệu theo tên ảnh."""
        if not csv_path.exists():
            return {}

        rows: dict[str, dict[str, str]] = {}
        with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
            for row in csv.DictReader(file):
                image_name = row.get("image_name", "").strip()
                if image_name:
                    rows[image_name] = {column: row.get(column, "") for column in CSV_COLUMNS}
                    rows[image_name]["image_name"] = image_name
        return rows

    def ensure_csv_rows(self, folder_name: str) -> None:
        """Đảm bảo mỗi ảnh đang nạp đều có một dòng dữ liệu trong CSV."""
        for image_path in self.images:
            row = self.csv_rows.setdefault(image_path.name, {"image_name": image_path.name})
            row["folder"] = folder_name
            for column in ("x1", "x2", "y1", "y2"):
                row.setdefault(column, "")

    def save_csv_rows(self, csv_path: Path | None = None) -> None:
        """Ghi toàn bộ dữ liệu crop hiện tại xuống file CSV."""
        csv_path = csv_path or self.get_path("csv", "CSV file")
        with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for row in sorted(self.csv_rows.values(), key=lambda item: item["image_name"]):
                writer.writerow({column: row.get(column, "") for column in CSV_COLUMNS})

    def show_current(self) -> None:
        """Hiển thị ảnh hiện tại, scale vừa canvas và vẽ khung crop đã lưu nếu có."""
        self.canvas.delete("all")
        self.crop_start = None
        self.crop_rect = None

        image_path = self.current_image()
        if image_path is None:
            self.current_pil = None
            self.current_photo = None
            self.status_var.set("Khong co anh de hien thi.")
            self.set_buttons()
            return

        try:
            self.current_pil = Image.open(image_path).convert("RGB")
        except Exception as error:
            self.current_pil = None
            self.status_var.set(f"Khong doc duoc anh: {image_path.name} | {error}")
            self.set_buttons()
            return

        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        image_w, image_h = self.current_pil.size
        self.scale = min(canvas_w / image_w, canvas_h / image_h, 1.0)
        self.display_w = max(1, int(image_w * self.scale))
        self.display_h = max(1, int(image_h * self.scale))
        self.offset_x = (canvas_w - self.display_w) // 2
        self.offset_y = (canvas_h - self.display_h) // 2

        display = self.current_pil.resize((self.display_w, self.display_h), Image.LANCZOS)
        self.current_photo = ImageTk.PhotoImage(display)
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, image=self.current_photo)

        self.draw_saved_rect(image_path)
        self.status_var.set(f"{self.index + 1}/{len(self.images)} | {image_path.name}")
        self.set_buttons()

    def set_buttons(self) -> None:
        """Bật hoặc tắt các nút điều hướng theo vị trí ảnh hiện tại."""
        has_image = self.current_image() is not None
        self.back_button.config(state=tk.NORMAL if self.index > 0 else tk.DISABLED)
        self.next_button.config(state=tk.NORMAL if has_image and self.index < len(self.images) - 1 else tk.DISABLED)
        self.delete_button.config(state=tk.NORMAL if has_image else tk.DISABLED)

    def draw_saved_rect(self, image_path: Path) -> None:
        """Vẽ khung crop màu xanh từ tọa độ đã lưu trong CSV."""
        coords = self.row_to_coords(self.csv_rows.get(image_path.name, {}))
        if coords is None:
            return

        x1, y1, x2, y2 = coords
        self.canvas.create_rectangle(
            self.offset_x + x1 * self.scale,
            self.offset_y + y1 * self.scale,
            self.offset_x + x2 * self.scale,
            self.offset_y + y2 * self.scale,
            outline="#00ff00",
            width=3,
        )

    def row_to_coords(self, row: dict[str, str]) -> tuple[float, float, float, float] | None:
        """Chuyển một dòng CSV thành tọa độ crop hợp lệ, hoặc None nếu dữ liệu sai."""
        try:
            x1, y1, x2, y2 = [float(str(row.get(key, "")).strip()) for key in ("x1", "y1", "x2", "y2")]
        except ValueError:
            return None
        return (x1, y1, x2, y2) if x2 > x1 and y2 > y1 else None

    def to_image_point(self, x: int, y: int) -> tuple[float, float] | None:
        """Đổi tọa độ chuột trên canvas sang tọa độ ảnh gốc nếu điểm nằm trong ảnh."""
        if self.current_pil is None:
            return None
        if not (self.offset_x <= x <= self.offset_x + self.display_w):
            return None
        if not (self.offset_y <= y <= self.offset_y + self.display_h):
            return None

        image_w, image_h = self.current_pil.size
        image_x = min(max(0.0, (x - self.offset_x) / self.scale), float(image_w - 1))
        image_y = min(max(0.0, (y - self.offset_y) / self.scale), float(image_h - 1))
        return image_x, image_y

    def clamp_canvas_point(self, x: int, y: int) -> tuple[int, int]:
        """Giới hạn tọa độ canvas để vùng crop không vượt khỏi ảnh đang hiển thị."""
        x = min(max(x, self.offset_x), self.offset_x + self.display_w)
        y = min(max(y, self.offset_y), self.offset_y + self.display_h)
        return x, y

    def start_crop(self, event: tk.Event) -> None:
        """Bắt đầu tạo khung crop khi người dùng double-click trong vùng ảnh."""
        if self.to_image_point(event.x, event.y) is None:
            return

        self.crop_start = (event.x, event.y)
        self.crop_rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="red", width=3)

    def drag_crop(self, event: tk.Event) -> None:
        """Cập nhật kích thước khung crop theo vị trí chuột khi đang kéo."""
        if self.crop_start is None or self.crop_rect is None:
            return

        x, y = self.clamp_canvas_point(event.x, event.y)
        x0, y0 = self.crop_start
        self.canvas.coords(self.crop_rect, x0, y0, x, y)

    def finish_crop(self, event: tk.Event) -> None:
        """Kết thúc thao tác crop, kiểm tra vùng chọn và lưu crop nếu đủ lớn."""
        if self.crop_start is None:
            return

        end_canvas = self.clamp_canvas_point(event.x, event.y)
        start = self.to_image_point(*self.crop_start)
        end = self.to_image_point(*end_canvas)
        self.crop_start = None
        if start is None or end is None:
            return

        x1, x2 = sorted([start[0], end[0]])
        y1, y2 = sorted([start[1], end[1]])
        if x2 - x1 >= 3 and y2 - y1 >= 3:
            self.save_crop(x1, y1, x2, y2)

    def save_crop(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Cắt ảnh theo tọa độ đã chọn, lưu file crop và cập nhật CSV."""
        image_path = self.current_image()
        if image_path is None or self.current_pil is None:
            return

        crop_dir = self.get_path("crop", "Crop folder")
        output_path = crop_dir / image_path.name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.current_pil.crop((round(x1), round(y1), round(x2), round(y2))).save(output_path)

        self.csv_rows[image_path.name] = {
            "image_name": image_path.name,
            "folder": self.get_path("source", "Image folder").name,
            "x1": number_text(x1),
            "x2": number_text(x2),
            "y1": number_text(y1),
            "y2": number_text(y2),
        }
        self.save_csv_rows()
        self.show_current()
        self.status_var.set(f"Saved crop: {output_path}")

    def next(self) -> None:
        """Chuyển sang ảnh kế tiếp nếu chưa ở ảnh cuối."""
        if self.index < len(self.images) - 1:
            self.index += 1
            self.show_current()

    def back(self) -> None:
        """Quay lại ảnh trước đó nếu chưa ở ảnh đầu."""
        if self.index > 0:
            self.index -= 1
            self.show_current()

    def delete_current(self) -> None:
        """Chuyển ảnh hiện tại sang thư mục deleted và xóa dữ liệu CSV của ảnh đó."""
        image_path = self.current_image()
        if image_path is None:
            return

        destination = unique_path(self.get_path("deleted", "Deleted folder") / image_path.name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(image_path), str(destination))
        except Exception as error:
            messagebox.showerror("Delete failed", str(error))
            return

        self.csv_rows.pop(image_path.name, None)
        self.save_csv_rows()
        self.images.pop(self.index)
        self.index = min(self.index, max(0, len(self.images) - 1))
        self.show_current()
        self.status_var.set(f"Moved to deleted folder: {destination}")

    def run(self) -> None:
        """Chạy vòng lặp giao diện Tkinter."""
        self.root.mainloop()


if __name__ == "__main__":
    FilterAndCropApp().run()
