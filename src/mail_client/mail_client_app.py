"""
Mail Client Application - Ứng dụng quản lý email chuyên dụng
Tác giả: Python Senior Software Engineer
Phiên bản: 1.0.0
"""

import poplib
import smtplib
import ssl
import os
import re
import time
from email import message_from_bytes, policy
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import decode_header
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional
from dotenv import load_dotenv

try:
    from plyer import notification

    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False
    print("⚠️  Thư viện 'plyer' chưa được cài đặt. Thông báo desktop sẽ không khả dụng.")
    print("   Cài đặt bằng lệnh: pip install plyer")


class MailClient:
    """
    Lớp quản lý email client với các chức năng:
    - Gửi email với đính kèm
    - Nhận và lưu email offline
    - Đọc email đã lưu
    - Giám sát tự động với thông báo
    """

    def __init__(self, cipher_level: str = "auto"):
        """
        Khởi tạo Mail Client và load cấu hình từ file .env

        Args:
            cipher_level: Mức độ bảo mật cipher
                - 'auto': Tự động (mặc định, SECLEVEL=1)
                - 'strict': Nghiêm ngặt (SECLEVEL=2, an toàn nhất)
                - 'legacy': Tương thích cũ (cho server rất cũ)
        """
        load_dotenv()
        self.cipher_level = cipher_level

        # Đọc cấu hình từ biến môi trường
        self.mail_host = os.getenv("MAIL_HOST")
        self.mail_port = int(os.getenv("MAIL_PORT", 995))
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", 465))
        self.mail_user = os.getenv("MAIL_USER")
        self.mail_pass = os.getenv("MAIL_PASS")

        # Kiểm tra cấu hình
        if not all([self.mail_host, self.smtp_server, self.mail_user, self.mail_pass]):
            raise ValueError("❌ Thiếu thông tin cấu hình trong file .env")

        # Thiết lập thư mục lưu trữ
        self.storage_dir = Path("emails_offline")
        self.storage_dir.mkdir(exist_ok=True)

        # File theo dõi UID đã tải
        self.seen_uids_file = self.storage_dir / ".seen_uids"
        self.seen_uids = self._load_seen_uids()

        # Cấu hình SSL với cipher suite tương thích rộng
        # Giải quyết lỗi handshake failure với server cũ
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Cấu hình cipher suite dựa trên mức độ yêu cầu
        cipher_configs = {
            "strict": "DEFAULT:@SECLEVEL=2",  # Bảo mật cao nhất
            "auto": "DEFAULT:@SECLEVEL=1",  # Cân bằng (khuyến nghị)
            "legacy": "ALL:@SECLEVEL=0",  # Tương thích tối đa
        }

        cipher_string = cipher_configs.get(self.cipher_level, cipher_configs["auto"])

        try:
            self.ssl_context.set_ciphers(cipher_string)
            print(f"🔐 SSL Context: {self.cipher_level} mode")
        except ssl.SSLError as e:
            print(f"⚠️  Cảnh báo cấu hình cipher: {e}")
            print("   Sử dụng cấu hình mặc định")

        print("✅ Mail Client đã sẵn sàng!")

    def _load_seen_uids(self) -> set:
        """Đọc danh sách UID đã tải từ file"""
        if self.seen_uids_file.exists():
            with open(self.seen_uids_file, "r") as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def _save_seen_uid(self, uid: str):
        """Lưu UID mới vào file tracking"""
        self.seen_uids.add(uid)
        with open(self.seen_uids_file, "a") as f:
            f.write(f"{uid}\n")

    def _decode_header_value(self, header_value: str) -> str:
        """
        Giải mã header email có thể chứa ký tự Unicode
        Ví dụ: =?UTF-8?B?...?= -> text thông thường
        """
        if not header_value:
            return ""

        decoded_parts = decode_header(header_value)
        result = []

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                result.append(str(part))

        return "".join(result)

    def _sanitize_filename(self, filename: str, max_length: int = 50) -> str:
        """
        Làm sạch tên file/folder, loại bỏ ký tự đặc biệt
        """
        # Loại bỏ ký tự không hợp lệ cho tên file
        filename = re.sub(r'[<>:"/\\|?*]', "", filename)
        filename = filename.strip()

        # Giới hạn độ dài
        if len(filename) > max_length:
            filename = filename[:max_length]

        return filename or "no_subject"

    def _extract_attachments(self, msg, folder: Path) -> int:
        """
        Trích xuất và lưu tất cả file đính kèm
        Trả về số lượng file đã lưu
        """
        count = 0

        for part in msg.walk():
            # Bỏ qua phần không phải attachment
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue

            filename = part.get_filename()
            if filename:
                # Giải mã tên file nếu cần
                filename = self._decode_header_value(filename)
                filename = self._sanitize_filename(filename, max_length=100)

                filepath = folder / filename

                # Xử lý trường hợp trùng tên file
                counter = 1
                original_filepath = filepath
                while filepath.exists():
                    name, ext = os.path.splitext(original_filepath.name)
                    filepath = folder / f"{name}_{counter}{ext}"
                    counter += 1

                # Lưu file
                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))

                count += 1
                print(f"   📎 Đính kèm: {filename}")

        return count

    def _get_email_body(self, msg) -> str:
        """
        Trích xuất nội dung text từ email
        Ưu tiên text/plain, fallback sang text/html
        """
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                # Bỏ qua attachment
                if "attachment" in content_disposition:
                    continue

                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
                    except:
                        pass
                elif content_type == "text/html" and not body:
                    try:
                        body = part.get_payload(decode=True).decode(errors="replace")
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode(errors="replace")
            except:
                body = str(msg.get_payload())

        return body.strip()

    def send_email(
        self,
        to_addr: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
    ):
        """
        Gửi email với khả năng đính kèm nhiều file

        Args:
            to_addr: Địa chỉ email người nhận
            subject: Tiêu đề email
            body: Nội dung email
            attachments: Danh sách đường dẫn file đính kèm
        """
        try:
            # Tạo message
            msg = MIMEMultipart()
            msg["From"] = self.mail_user
            msg["To"] = to_addr
            msg["Subject"] = subject

            # Thêm nội dung
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # Xử lý đính kèm
            if attachments:
                for filepath in attachments:
                    if not os.path.exists(filepath):
                        print(f"⚠️  File không tồn tại: {filepath}")
                        continue

                    filename = os.path.basename(filepath)

                    with open(filepath, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())

                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition", f"attachment; filename= {filename}"
                    )
                    msg.attach(part)
                    print(f"   📎 Đã đính kèm: {filename}")

            # Kết nối và gửi qua SMTP với SSL
            with smtplib.SMTP_SSL(
                self.smtp_server, self.smtp_port, context=self.ssl_context
            ) as server:
                server.login(self.mail_user, self.mail_pass)
                server.send_message(msg)

            print(f"✅ Email đã được gửi thành công đến {to_addr}")

        except smtplib.SMTPAuthenticationError:
            print("❌ Lỗi xác thực: Kiểm tra lại email và mật khẩu")
        except smtplib.SMTPException as e:
            print(f"❌ Lỗi SMTP: {e}")
        except Exception as e:
            print(f"❌ Lỗi không xác định: {e}")

    def diagnose_ssl_connection(self):
        """
        Công cụ chẩn đoán kết nối SSL/TLS
        Kiểm tra cipher suite và protocol được hỗ trợ
        """
        print("\n🔍 CHẨN ĐOÁN KẾT NỐI SSL")
        print("=" * 60)

        # Thông tin SSL context hiện tại
        print(f"\n📋 Cấu hình hiện tại:")
        print(f"   Cipher level: {self.cipher_level}")
        print(f"   Min TLS version: {self.ssl_context.minimum_version}")
        print(f"   Cipher suites: {len(self.ssl_context.get_ciphers())} available")

        # Test kết nối POP3
        print(f"\n🔌 Đang test kết nối POP3 tới {self.mail_host}:{self.mail_port}...")

        test_results = []
        cipher_modes = ["strict", "auto", "legacy"]

        for mode in cipher_modes:
            try:
                ctx = ssl.create_default_context()
                ctx.minimum_version = ssl.TLSVersion.TLSv1_2

                cipher_configs = {
                    "strict": "DEFAULT:@SECLEVEL=2",
                    "auto": "DEFAULT:@SECLEVEL=1",
                    "legacy": "ALL:@SECLEVEL=0",
                }
                ctx.set_ciphers(cipher_configs[mode])

                with poplib.POP3_SSL(
                    self.mail_host, self.mail_port, context=ctx, timeout=10
                ) as conn:
                    conn.user(self.mail_user)
                    conn.pass_(self.mail_pass)
                    test_results.append((mode, "✅ Thành công"))
                    print(f"   [{mode}] ✅ Kết nối thành công")

            except ssl.SSLError as e:
                test_results.append((mode, f"❌ SSL Error: {str(e)[:50]}"))
                print(f"   [{mode}] ❌ Lỗi SSL")
            except poplib.error_proto as e:
                test_results.append((mode, f"❌ Auth Error: {str(e)[:50]}"))
                print(f"   [{mode}] ⚠️  Kết nối OK nhưng lỗi xác thực")
            except Exception as e:
                test_results.append((mode, f"❌ {str(e)[:50]}"))
                print(f"   [{mode}] ❌ Lỗi khác")

        # Tổng kết
        print("\n📊 KẾT QUẢ:")
        print("-" * 60)
        for mode, result in test_results:
            print(f"   {mode:8} : {result}")

        # Khuyến nghị
        print("\n💡 KHUYẾN NGHỊ:")
        successful_modes = [
            m for m, r in test_results if "Thành công" in r or "OK" in r
        ]

        if successful_modes:
            print(f"   ✅ Sử dụng mode: {successful_modes[0]}")
            print(
                f"   Khởi động: client = MailClient(cipher_level='{successful_modes[0]}')"
            )
        else:
            print("   ❌ Không có mode nào hoạt động")
            print("   🔧 Kiểm tra:")
            print("      - Server có hỗ trợ TLS 1.2+?")
            print("      - Firewall có chặn port?")
            print("      - Email/password có đúng?")

        print("=" * 60)

    def fetch_new_emails(self) -> int:
        """
        Kết nối đến server POP3, tải về và lưu các email mới

        Returns:
            Số lượng email mới đã tải
        """
        new_count = 0

        try:
            # Kết nối POP3 với SSL
            with poplib.POP3_SSL(
                self.mail_host, self.mail_port, context=self.ssl_context
            ) as pop_conn:
                pop_conn.user(self.mail_user)
                pop_conn.pass_(self.mail_pass)

                # Lấy danh sách email
                num_messages = len(pop_conn.list()[1])

                if num_messages == 0:
                    print("📭 Không có email nào trên server")
                    return 0

                print(f"📬 Tìm thấy {num_messages} email trên server")

                # Duyệt qua từng email
                for i in range(1, num_messages + 1):
                    # Lấy UID
                    uid_response = pop_conn.uidl(i)
                    uid = uid_response.decode().split()[1]

                    # Kiểm tra đã tải chưa
                    if uid in self.seen_uids:
                        continue

                    # Tải email
                    raw_email = b"\n".join(pop_conn.retr(i)[1])
                    msg = message_from_bytes(raw_email, policy=policy.default)

                    # Giải mã thông tin
                    from_addr = self._decode_header_value(msg.get("From", ""))
                    subject = self._decode_header_value(
                        msg.get("Subject", "No Subject")
                    )
                    date = msg.get("Date", "")

                    print(f"\n📧 Email mới #{i}")
                    print(f"   Từ: {from_addr}")
                    print(f"   Tiêu đề: {subject}")
                    print(f"   Ngày: {date}")

                    # Tạo thư mục lưu trữ
                    folder_name = f"{uid}_{self._sanitize_filename(subject)}"
                    email_folder = self.storage_dir / folder_name
                    email_folder.mkdir(exist_ok=True)

                    # Lưu file .eml gốc
                    eml_file = email_folder / "full_email.eml"
                    with open(eml_file, "wb") as f:
                        f.write(raw_email)

                    # Trích xuất đính kèm
                    attachment_count = self._extract_attachments(msg, email_folder)

                    # Đánh dấu đã tải
                    self._save_seen_uid(uid)
                    new_count += 1

                    # Hiển thị thông báo desktop
                    if PLYER_AVAILABLE:
                        try:
                            notification.notify(
                                title=f"📧 Email mới từ {from_addr[:30]}",
                                message=subject[:100],
                                app_name="Mail Client",
                                timeout=10,
                            )
                        except:
                            pass  # Bỏ qua nếu thông báo thất bại

                print(f"\n✅ Đã tải về {new_count} email mới")

        except poplib.error_proto as e:
            print(f"❌ Lỗi POP3: {e}")
        except ssl.SSLError as e:
            print(f"❌ Lỗi SSL: {e}")
            print("\n🔧 GỢI Ý KHẮC PHỤC:")
            print("1. Server có thể yêu cầu cipher suite cũ")
            print(
                "2. Thử khởi động lại với: client = MailClient(cipher_level='legacy')"
            )
            print("3. Kiểm tra server có hỗ trợ TLS 1.2 trở lên")
            print("4. Xem log chi tiết: openssl s_client -connect <host>:<port>")
        except Exception as e:
            print(f"❌ Lỗi không xác định: {e}")

        return new_count

    def read_saved_emails(self):
        """
        Hiển thị danh sách email đã lưu và cho phép đọc chi tiết
        """
        # Lấy danh sách thư mục email
        email_folders = sorted([d for d in self.storage_dir.iterdir() if d.is_dir()])

        if not email_folders:
            print("\n📭 Chưa có email nào được lưu offline")
            return

        print(f"\n📚 Danh sách {len(email_folders)} email đã lưu:")
        print("=" * 80)

        # Hiển thị danh sách
        for idx, folder in enumerate(email_folders, 1):
            eml_file = folder / "full_email.eml"

            if eml_file.exists():
                try:
                    with open(eml_file, "rb") as f:
                        msg = message_from_bytes(f.read(), policy=policy.default)

                    from_addr = self._decode_header_value(msg.get("From", "Unknown"))
                    subject = self._decode_header_value(
                        msg.get("Subject", "No Subject")
                    )
                    date = msg.get("Date", "")

                    print(f"\n[{idx}] {subject}")
                    print(f"    Từ: {from_addr}")
                    print(f"    Ngày: {date}")

                except Exception as e:
                    print(f"\n[{idx}] {folder.name}")
                    print(f"    ⚠️  Lỗi đọc file: {e}")

        print("\n" + "=" * 80)

        # Cho phép chọn email để đọc chi tiết
        while True:
            choice = input("\nNhập số thứ tự email muốn đọc (0 để quay lại): ").strip()

            if choice == "0":
                break

            try:
                idx = int(choice)
                if 1 <= idx <= len(email_folders):
                    self._display_email_detail(email_folders[idx - 1])
                else:
                    print("❌ Số thứ tự không hợp lệ")
            except ValueError:
                print("❌ Vui lòng nhập số")

    def _display_email_detail(self, folder: Path):
        """
        Hiển thị chi tiết nội dung một email
        """
        eml_file = folder / "full_email.eml"

        try:
            with open(eml_file, "rb") as f:
                msg = message_from_bytes(f.read(), policy=policy.default)

            from_addr = self._decode_header_value(msg.get("From", ""))
            to_addr = self._decode_header_value(msg.get("To", ""))
            subject = self._decode_header_value(msg.get("Subject", ""))
            date = msg.get("Date", "")
            body = self._get_email_body(msg)

            print("\n" + "=" * 80)
            print("📧 CHI TIẾT EMAIL")
            print("=" * 80)
            print(f"Từ: {from_addr}")
            print(f"Đến: {to_addr}")
            print(f"Tiêu đề: {subject}")
            print(f"Ngày: {date}")
            print("-" * 80)
            print("NỘI DUNG:")
            print("-" * 80)
            print(body)

            # Liệt kê file đính kèm
            attachments = [f for f in folder.iterdir() if f.name != "full_email.eml"]

            if attachments:
                print("-" * 80)
                print(f"📎 FILE ĐÍNH KÈM ({len(attachments)}):")
                for att in attachments:
                    size_kb = att.stat().st_size / 1024
                    print(f"   • {att.name} ({size_kb:.1f} KB)")

            print("=" * 80)

        except Exception as e:
            print(f"❌ Lỗi đọc email: {e}")

    def auto_monitor(self, interval: int = 300):
        """
        Chế độ giám sát tự động, kiểm tra email mới theo chu kỳ

        Args:
            interval: Thời gian giữa các lần kiểm tra (giây), mặc định 5 phút
        """
        print(f"\n🔄 Bắt đầu giám sát tự động (kiểm tra mỗi {interval//60} phút)")
        print("   Nhấn Ctrl+C để dừng\n")

        try:
            while True:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{current_time}] Đang kiểm tra email mới...")

                new_count = self.fetch_new_emails()

                if new_count == 0:
                    print(
                        f"   Không có email mới. Kiểm tra lại sau {interval//60} phút."
                    )

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n⏹️  Đã dừng giám sát tự động")

    def run(self):
        """
        Chạy ứng dụng với menu CLI tương tác
        """
        while True:
            print("\n" + "=" * 60)
            print("📮 MAIL CLIENT - MENU CHÍNH")
            print("=" * 60)
            print("1. 📤 Gửi email mới")
            print("2. 📥 Kiểm tra và tải email mới")
            print("3. 📖 Đọc email đã lưu (Offline)")
            print("4. 🔄 Bắt đầu giám sát tự động")
            print("5. 🚪 Thoát")
            print("=" * 60)

            choice = input("\nChọn chức năng (1-5): ").strip()

            if choice == "1":
                self._send_email_interactive()
            elif choice == "2":
                print("\n📥 Đang kiểm tra email mới...")
                self.fetch_new_emails()
            elif choice == "3":
                self.read_saved_emails()
            elif choice == "4":
                self.auto_monitor()
            elif choice == "5":
                print("\n👋 Cảm ơn bạn đã sử dụng Mail Client!")
                break
            else:
                print("❌ Lựa chọn không hợp lệ")

    def _send_email_interactive(self):
        """
        Giao diện tương tác để gửi email
        """
        print("\n📤 SOẠN EMAIL MỚI")
        print("-" * 60)

        to_addr = input("Đến (email): ").strip()
        if not to_addr:
            print("❌ Địa chỉ email không được để trống")
            return

        subject = input("Tiêu đề: ").strip()

        print("Nội dung (nhập dòng trống để kết thúc):")
        body_lines = []
        while True:
            line = input()
            if line == "":
                break
            body_lines.append(line)
        body = "\n".join(body_lines)

        # Xử lý đính kèm
        attachments = []
        while True:
            att = input("Đường dẫn file đính kèm (Enter để bỏ qua): ").strip()
            if not att:
                break
            attachments.append(att)

        # Gửi email
        self.send_email(to_addr, subject, body, attachments if attachments else None)


def main():
    """
    Hàm main để khởi chạy ứng dụng
    """
    print("=" * 60)
    print("🚀 MAIL CLIENT APPLICATION v1.0.0")
    print("=" * 60)

    # Kiểm tra file .env
    if not os.path.exists(".env"):
        print("\n❌ Không tìm thấy file .env")
        print("\nVui lòng tạo file .env với nội dung:")
        print("-" * 60)
        print("MAIL_HOST=your.pop3.server.com")
        print("MAIL_PORT=995")
        print("SMTP_SERVER=your.smtp.server.com")
        print("SMTP_PORT=465")
        print("MAIL_USER=your_email@example.com")
        print("MAIL_PASS=your_password")
        print("-" * 60)
        return

    try:
        client = MailClient()
        client.run()
    except ValueError as e:
        print(f"\n{e}")
        print("\nVui lòng kiểm tra lại file .env")
    except Exception as e:
        print(f"\n❌ Lỗi khởi động ứng dụng: {e}")


if __name__ == "__main__":
    main()
