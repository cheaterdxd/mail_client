import poplib
import smtplib
import time
import os
import getpass
import re
import ssl  # <<< THÊM VÀO: Import thư viện ssl

from email.parser import BytesParser
from email.policy import default
from email.message import Message
from email.header import decode_header, make_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from plyer import notification

from dotenv import load_dotenv


# Sử dụng python-dotenv để tải các biến môi trường từ file .env
load_dotenv()


def get_config():
    """Trả về cấu hình cho mail client đọc từ các biến môi trường."""
    cfg = {}
    cfg["pop3_server"] = os.getenv("MAIL_HOST", "pop3.viettel.com.vn")
    try:
        cfg["pop3_port"] = int(os.getenv("MAIL_PORT", "995") or 995)
    except ValueError:
        cfg["pop3_port"] = 995
    cfg["smtp_server"] = os.getenv("SMTP_SERVER", "smtp.viettel.com.vn")
    try:
        cfg["smtp_port"] = int(os.getenv("SMTP_PORT", "465") or 465)
    except ValueError:
        cfg["smtp_port"] = 465
    cfg["mail_storage_dir"] = os.getenv("MAIL_STORAGE_DIR", "offline_mails")
    try:
        cfg["monitor_interval"] = int(os.getenv("MONITOR_INTERVAL", "300") or 300)
    except ValueError:
        cfg["monitor_interval"] = 300
    return cfg


class MailClient:
    def __init__(
        self,
        email_address,
        password,
        pop3_server=None,
        pop3_port=None,
        smtp_server=None,
        smtp_port=None,
        storage_dir=None,
        monitor_interval=None,
    ):
        self.email_address = email_address
        self.password = password
        self.seen_uids = set()

        # Kết hợp các tham số được truyền vào với cấu hình từ môi trường/mặc định
        cfg = get_config()
        self.pop3_server = pop3_server or cfg["pop3_server"]
        self.pop3_port = pop3_port or cfg["pop3_port"]
        self.smtp_server = smtp_server or cfg["smtp_server"]
        self.smtp_port = smtp_port or cfg["smtp_port"]
        self.mail_storage_dir = storage_dir or cfg["mail_storage_dir"]
        self.monitor_interval = monitor_interval or cfg["monitor_interval"]

        if not os.path.exists(self.mail_storage_dir):
            os.makedirs(self.mail_storage_dir)

        self.seen_uids_file = os.path.join(self.mail_storage_dir, ".seen_uids")

        self._load_seen_uids()

    def _load_seen_uids(self):
        try:
            # <<< SỬA LỖI NHỎ: Đọc từ self.seen_uids_file để nhất quán
            with open(self.seen_uids_file, "r") as f:
                self.seen_uids = set(line.strip() for line in f)
        except FileNotFoundError:
            pass

    def _save_seen_uid(self, uid):
        self.seen_uids.add(uid)
        with open(self.seen_uids_file, "a") as f:
            f.write(f"{uid}\n")

    def _decode_header(self, header_text):
        if not header_text:
            return ""
        return str(make_header(decode_header(header_text)))

    def _save_email(self, msg: Message, uid: str):
        subject = self._decode_header(msg["Subject"])
        safe_subject = re.sub(r'[\\/*?:"<>|]', "", subject)
        if not safe_subject.strip():
            safe_subject = "no_subject"

        email_dir = os.path.join(
            self.mail_storage_dir, f"{uid}_{safe_subject[:50].strip()}"
        )

        if not os.path.exists(email_dir):
            os.makedirs(email_dir)

        with open(os.path.join(email_dir, "full_email.eml"), "wb") as f:
            f.write(msg.as_bytes())

        for part in msg.walk():
            if (
                part.get_content_maintype() == "multipart"
                or part.get("Content-Disposition") is None
            ):
                continue

            filename = part.get_filename()
            if filename:
                decoded_filename = self._decode_header(filename)
                filepath = os.path.join(email_dir, decoded_filename)
                try:
                    with open(filepath, "wb") as f:
                        payload = part.get_payload(decode=True)
                        if payload is not None:
                            if isinstance(payload, str):
                                payload = payload.encode("utf-8")
                            elif not isinstance(payload, bytes):
                                payload = bytes(payload)
                            f.write(payload)
                            print(f"   -> Đã tải về attachment: {decoded_filename}")
                        else:
                            print(
                                f"   -> Không thể giải mã nội dung file đính kèm: {decoded_filename}"
                            )
                except OSError as e:
                    print(f"   -> Lỗi khi lưu file: {filepath}. Lỗi: {e}")

    def send_email(self, recipient, subject, body, attachments=None):
        print(f"\nĐang soạn mail gửi tới: {recipient}...")
        msg = MIMEMultipart()
        msg["From"] = self.email_address
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if attachments:
            for file_path in attachments:
                try:
                    with open(file_path, "rb") as attachment_file:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(attachment_file.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{os.path.basename(file_path)}"',
                    )
                    msg.attach(part)
                    print(f"  -> Đã đính kèm file: {os.path.basename(file_path)}")
                except FileNotFoundError:
                    print(f"  -> Lỗi: Không tìm thấy file đính kèm '{file_path}'")
                    return

        server = None
        try:
            # <<< SỬA LỖI SSL: Tạo context an toàn
            context = ssl.create_default_context()
            # <<< SỬA LỖI SSL: Truyền context vào kết nối
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
            server.login(self.email_address, self.password)
            server.send_message(msg)
            print("✅ Gửi mail thành công!")
        except smtplib.SMTPAuthenticationError:
            print("❌ Lỗi: Sai tên đăng nhập hoặc mật khẩu SMTP.")
        except Exception as e:
            print(f"❌ Đã xảy ra lỗi khi gửi mail: {e}")
        finally:
            if server:
                server.quit()

    def fetch_emails(self):
        print(f"[{time.ctime()}] Đang kiểm tra mail mới...")
        new_mail_count = 0

        pop_server = None
        try:
            # <<< SỬA LỖI SSL: Tạo context an toàn
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            # <<< SỬA LỖI SSL: Truyền context vào kết nối
            pop_server = poplib.POP3_SSL(
                self.pop3_server, self.pop3_port, context=context
            )

            pop_server.user(self.email_address)
            pop_server.pass_(self.password)

            messages_uids = [item.split()[1].decode() for item in pop_server.uidl()[1]]

            for i, uid in enumerate(messages_uids):
                if uid not in self.seen_uids:
                    new_mail_count += 1
                    print(f"  -> Phát hiện mail mới (UID: {uid}). Đang tải về...")

                    resp, lines, octets = pop_server.retr(i + 1)
                    msg_content = b"\r\n".join(lines)
                    msg = BytesParser(policy=default).parsebytes(msg_content)

                    self._save_email(msg, uid)
                    self._save_seen_uid(uid)

                    if hasattr(notification, "notify") and callable(
                        notification.notify
                    ):
                        try:
                            notification.notify(
                                title=f"Mail mới từ: {self._decode_header(msg['From'])}",
                                message=f"Chủ đề: {self._decode_header(msg['Subject'])}",
                                app_name="Mail Client",
                                timeout=10,
                            )
                        except Exception as e:
                            print(f"   -> Không thể hiển thị thông báo: {e}")
                    else:
                        print(
                            "   -> Cảnh báo: Backend thông báo không khả dụng trên hệ thống này."
                        )
            if new_mail_count == 0:
                print("  -> Không có mail mới.")
            else:
                print(f"✅ Hoàn tất! Đã tải về {new_mail_count} mail mới.")
        except poplib.error_proto as e:
            print(
                f"❌ Lỗi xác thực POP3: {e}. Vui lòng kiểm tra lại email và mật khẩu."
            )
        except ssl.SSLError as e:
            print(
                f"❌ Lỗi kết nối SSL: {e}. Vui lòng kiểm tra lại cấu hình mạng hoặc server."
            )
        except Exception as e:
            print(f"❌ Đã xảy ra lỗi khi kết nối hoặc tải mail: {e}")
        finally:
            if pop_server:
                pop_server.quit()

    def load_offline_emails(self):
        """Đọc và hiển thị các email đã được lưu trữ offline."""
        print("\n--- Hộp thư Offline ---")
        try:
            email_dirs = sorted(
                os.listdir(self.mail_storage_dir),
                key=lambda d: int(d.split("_")[0]) if d.split("_")[0].isdigit() else 0,
            )

            if not any(
                os.path.isdir(os.path.join(self.mail_storage_dir, d))
                for d in email_dirs
            ):
                print("Chưa có email nào được lưu trữ.")
                return

            for dirname in email_dirs:
                email_path = os.path.join(
                    self.mail_storage_dir, dirname, "full_email.eml"
                )
                if os.path.exists(email_path):
                    with open(email_path, "rb") as f:
                        msg = BytesParser(policy=default).parse(f)
                        print("-" * 20)
                        print(f"Thư mục: {dirname}")
                        print(f"  Từ: {self._decode_header(msg['From'])}")
                        print(f"  Tới: {self._decode_header(msg['To'])}")
                        print(f"  Chủ đề: {self._decode_header(msg['Subject'])}")

                        attachments = [
                            f
                            for f in os.listdir(
                                os.path.join(self.mail_storage_dir, dirname)
                            )
                            if f != "full_email.eml"
                        ]
                        if attachments:
                            print(f"  Attachments: {', '.join(attachments)}")
        except FileNotFoundError:
            print(
                "Thư mục lưu trữ offline chưa được tạo. Hãy kiểm tra mail lần đầu tiên."
            )
        except Exception as e:
            print(f"Lỗi khi đọc mail offline: {e}")

    def start_monitoring(self):
        """Bắt đầu vòng lặp kiểm tra mail mỗi 5 phút."""
        print(
            "\n*** Bắt đầu chế độ giám sát email mỗi 5 phút. Nhấn Ctrl+C để dừng. ***"
        )
        try:
            while True:
                self.fetch_emails()
                time.sleep(self.monitor_interval)
        except KeyboardInterrupt:
            print("\n*** Đã dừng chế độ giám sát. ***")


def main_menu(client):
    """Hàm chạy giao diện chính của chương trình."""
    while True:
        print("\n====================")
        print("  MAIL CLIENT CLI   ")
        print("====================")
        print("1. Gửi email mới")
        print("2. Kiểm tra và tải mail mới ngay lập tức")
        print("3. Đọc lại các mail đã lưu (Offline)")
        print("4. Bắt đầu chế độ giám sát (kiểm tra mỗi 5 phút)")
        print("5. Thoát")
        choice = input("Vui lòng chọn chức năng: ")

        if choice == "1":
            recipient = input("Nhập email người nhận: ")
            subject = input("Nhập chủ đề: ")
            print(
                "Nhập nội dung email (nhấn Ctrl+D hoặc Ctrl+Z trên Windows khi xong):"
            )
            body_lines = []
            try:
                while True:
                    body_lines.append(input())
            except EOFError:
                pass
            body = "\n".join(body_lines)

            attachments_str = input(
                "Nhập đường dẫn file đính kèm (cách nhau bởi dấu phẩy nếu nhiều file): "
            )
            attachments = [p.strip() for p in attachments_str.split(",") if p.strip()]

            client.send_email(recipient, subject, body, attachments)

        elif choice == "2":
            client.fetch_emails()
        elif choice == "3":
            client.load_offline_emails()
        elif choice == "4":
            client.start_monitoring()
        elif choice == "5":
            print("Tạm biệt!")
            break
        else:
            print("Lựa chọn không hợp lệ, vui lòng thử lại.")


if __name__ == "__main__":
    print("--- Đăng nhập vào Mail Client ---")
    # Ưu tiên đọc thông tin đăng nhập từ môi trường (.env) trước khi hỏi người dùng
    email_address = os.getenv("MAIL_USER")
    if not email_address:
        email_address = input("Nhập địa chỉ email Viettel của bạn: ")

    password = os.getenv("MAIL_PASS")
    if not password:
        password = getpass.getpass("Nhập mật khẩu: ")

    client = MailClient(email_address, password)
    main_menu(client)
