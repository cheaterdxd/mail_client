# mail_client

Bộ khung dự án Python nhỏ để bắt đầu phát triển ứng dụng `mail_client`.

Yêu cầu tối thiểu:
- Python 3.10+
- pip

Các bước nhanh để bắt đầu (Windows PowerShell):

1. Tạo virtual environment và kích hoạt

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Cài phụ thuộc (nếu có):

```powershell
pip install -r requirements.txt
```

3. Chạy test:

```powershell
pytest -q
```

4. Chạy ứng dụng mẫu:

```powershell
python -m mail_client
```

Cấu trúc chính:
- `src/mail_client/` — mã nguồn
- `tests/` — test pytest
- `.vscode/` — cấu hình phát triển cho VS Code

Ghi chú:
- Tệp `.env.example` chứa biến môi trường mẫu.
- Sử dụng `pre-commit` để chạy format/check trước khi commit (tùy chọn).