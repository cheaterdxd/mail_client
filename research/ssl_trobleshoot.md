# 📚 SSL Troubleshooting - Case Studies Thực tế

## 🎯 Giới thiệu

Tài liệu này tổng hợp các trường hợp thực tế về lỗi SSL Handshake Failure và cách xử lý cụ thể cho từng nhà cung cấp email phổ biến.

---

## 📧 Case Study 1: Gmail / Google Workspace

### Triệu chứng
```
[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure
```

### Nguyên nhân
- Gmail yêu cầu TLS 1.2+ với cipher suite hiện đại
- Python 3.10+ với SECLEVEL=2 mặc định có thể không tương thích với một số cipher cũ

### Giải pháp
```bash
# Thử theo thứ tự:
python mail_client.py auto      # ✅ Thường hoạt động
python mail_client.py strict    # ✅ Nếu auto không được
```

### Cấu hình .env
```env
MAIL_HOST=pop.gmail.com
MAIL_PORT=995
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
MAIL_USER=your_email@gmail.com
MAIL_PASS=your_16_digit_app_password
```

### ⚠️ Lưu ý quan trọng
1. **BẮT BUỘC dùng App Password**, không phải mật khẩu thường
2. Tạo App Password tại: https://myaccount.google.com/apppasswords
3. Phải bật 2-Step Verification trước
4. App Password có dạng: `xxxx xxxx xxxx xxxx` (16 ký tự)

### Cipher Suite hoạt động
```python
# Gmail hỗ trợ tốt
ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
# Hoặc cụ thể hơn
ctx.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384')
```

### Test
```bash
python ssl_test.py pop.gmail.com 995
```

**Kết quả mong đợi:**
- ✅ TLS 1.2, 1.3
- ✅ Modern cipher suites (ECDHE-RSA-AES-GCM)
- ✅ Valid certificate từ Google Trust Services

---

## 📧 Case Study 2: Microsoft Outlook / Office 365

### Triệu chứng
```
[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure
hoặc
[SSL: WRONG_VERSION_NUMBER] wrong version number
```

### Nguyên nhân
- Outlook có thể yêu cầu cipher suite cụ thể
- Một số server Outlook cũ chỉ hỗ trợ TLS 1.0/1.1

### Giải pháp
```bash
# Thử theo thứ tự:
python mail_client.py legacy    # ✅ Thường hoạt động
python mail_client.py auto      # ✅ Thử nếu legacy không cần
```

### Cấu hình .env

**POP3/SMTP:**
```env
MAIL_HOST=outlook.office365.com
MAIL_PORT=995
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
MAIL_USER=your_email@outlook.com
MAIL_PASS=your_password
```

**Hoặc cho personal Outlook:**
```env
MAIL_HOST=pop-mail.outlook.com
MAIL_PORT=995
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
```

### Cipher Suite hoạt động
```python
# Outlook thường cần legacy
ctx.set_ciphers('ALL:@SECLEVEL=0')
# Hoặc cụ thể
ctx.set_ciphers('AES128-SHA:AES256-SHA:DES-CBC3-SHA')
```

### ⚠️ Vấn đề đặc biệt
**SMTP Port 587 (STARTTLS):** Outlook SMTP thường dùng port 587 với STARTTLS, không phải SSL trực tiếp. Nếu gặp lỗi, thử:

```python
# Cho SMTP với STARTTLS
server = smtplib.SMTP('smtp.office365.com', 587)
server.starttls(context=ssl_context)
server.login(user, password)
```

---

## 📧 Case Study 3: Yahoo Mail

### Triệu chứng
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
hoặc
[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE]
```

### Nguyên nhân
- Yahoo có chính sách bảo mật khác biệt
- Cần bật "Allow apps that use less secure sign in"
- Yahoo đôi khi yêu cầu App Password

### Giải pháp
```bash
python mail_client.py auto      # ✅ Thường hoạt động
```

### Cấu hình .env
```env
MAIL_HOST=pop.mail.yahoo.com
MAIL_PORT=995
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=465
MAIL_USER=your_email@yahoo.com
MAIL_PASS=your_app_password
```

### Các bước cấu hình Yahoo
1. Đăng nhập Yahoo Mail
2. Vào Account Settings → Security
3. Bật "Allow apps that use less secure sign in"
4. Hoặc tạo App Password (khuyến nghị)

### Cipher Suite
```python
ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
```

---

## 📧 Case Study 4: Server cPanel / Hosting Shared

### Triệu chứng
```
[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure
[SSL: TLSV1_ALERT_PROTOCOL_VERSION] tlsv1 alert protocol version
```

### Nguyên nhân
- Server hosting thường dùng cấu hình SSL cũ
- cPanel có thể chạy OpenSSL version cũ
- Một số hosting chỉ hỗ trợ TLS 1.0

### Giải pháp
```bash
# Gần như chắc chắn cần legacy
python mail_client.py legacy
```

### Cấu hình .env
```env
MAIL_HOST=mail.yourdomain.com
MAIL_PORT=995
SMTP_SERVER=mail.yourdomain.com
SMTP_PORT=465
MAIL_USER=user@yourdomain.com
MAIL_PASS=your_password
```

### Cipher Suite
```python
# cPanel thường cần SECLEVEL=0
ctx.set_ciphers('ALL:@SECLEVEL=0')
ctx.minimum_version = ssl.TLSVersion.TLSv1  # Có thể cần TLS 1.0
```

### ⚠️ Lưu ý
- Hỏi hosting provider về TLS version được hỗ trợ
- Xem xét nâng cấp hosting nếu chỉ có TLS 1.0
- Một số hosting có option "Enable TLS 1.2" trong cPanel

---

## 📧 Case Study 5: ProtonMail Bridge

### Triệu chứng
```
[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate
```

### Nguyên nhân
- ProtonMail Bridge dùng self-signed certificate local
- Chạy trên localhost (127.0.0.1)
- Cần tắt certificate verification

### Giải pháp đặc biệt
```python
# Cho ProtonMail Bridge - cần tắt verify
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE  # ⚠️ Chỉ cho localhost
```

### Cấu hình .env
```env
MAIL_HOST=127.0.0.1
MAIL_PORT=1143  # IMAP port của Bridge
SMTP_SERVER=127.0.0.1
SMTP_PORT=1025  # SMTP port của Bridge
MAIL_USER=your_protonmail@proton.me
MAIL_PASS=bridge_password
```

### ⚠️ An toàn
- Chỉ tắt verify khi kết nối localhost
- Không tắt verify cho server bên ngoài

---

## 📧 Case Study 6: Zoho Mail

### Triệu chứng
```
[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE]
```

### Nguyên nhân
- Zoho yêu cầu cipher suite cụ thể
- Không hỗ trợ một số cipher yếu

### Giải pháp
```bash
python mail_client.py auto      # ✅ Hoạt động tốt
```

### Cấu hình .env
```env
MAIL_HOST=pop.zoho.com
MAIL_PORT=995
SMTP_SERVER=smtp.zoho.com
SMTP_PORT=465
MAIL_USER=your_email@zoho.com
MAIL_PASS=your_password
```

### Cipher Suite
```python
ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
```

---

## 📧 Case Study 7: iCloud Mail

### Triệu chứng
```
[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE]
```

### Nguyên nhân
- iCloud yêu cầu App-Specific Password
- TLS configuration khá nghiêm ngặt

### Giải pháp
```bash
python mail_client.py strict    # ✅ iCloud hỗ trợ TLS hiện đại
```

### Cấu hình .env
```env
MAIL_HOST=imap.mail.me.com
MAIL_PORT=993  # iCloud dùng IMAP, không có POP3
SMTP_SERVER=smtp.mail.me.com
SMTP_PORT=587
MAIL_USER=your_apple_id@icloud.com
MAIL_PASS=app_specific_password
```

### Tạo App-Specific Password
1. Đăng nhập appleid.apple.com
2. Security → App-Specific Passwords
3. Generate new password

---

## 🔧 Quy trình Troubleshooting Chung

### Bước 1: Chẩn đoán ban đầu
```bash
# Chạy test script độc lập
python ssl_test.py your.mail.server 995

# Hoặc dùng công cụ tích hợp
python mail_client.py
# Chọn option 5 hoặc 6
```

### Bước 2: Phân tích kết quả

**Nếu TCP không kết nối được:**
- ❌ Firewall chặn
- ❌ Port sai
- ❌ Hostname sai
- ❌ Server down

**Nếu SSL handshake thất bại:**
- ⚠️ Thử các cipher level khác nhau
- ⚠️ Kiểm tra TLS version
- ⚠️ Xem certificate có hợp lệ

**Nếu authentication thất bại:**
- ❌ Username/password sai
- ❌ Cần App Password
- ❌ Account bị khóa

### Bước 3: Thử các mode

```bash
# Thử theo thứ tự này:
python mail_client.py auto      # 1. Thử đầu tiên
python mail_client.py strict    # 2. Nếu server hiện đại
python mail_client.py legacy    # 3. Nếu server cũ
```

### Bước 4: Tùy chỉnh nâng cao

Nếu tất cả đều thất bại, sửa code trực tiếp:

```python
# Trong __init__ của MailClient
self.ssl_context = ssl.create_default_context()

# Thử các cấu hình này lần lượt:

# Config 1: Cho server rất cũ
self.ssl_context.set_ciphers('ALL:@SECLEVEL=0')
self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1
self.ssl_context.maximum_version = ssl.TLSVersion.TLSv1_2

# Config 2: Cho server yêu cầu cipher cụ thể
self.ssl_context.set_ciphers('ECDHE-RSA-AES128-SHA:AES128-SHA:DES-CBC3-SHA')

# Config 3: Tắt verify (CHỈ cho localhost/dev)
self.ssl_context.check_hostname = False
self.ssl_context.verify_mode = ssl.CERT_NONE
```

---

## 📊 Bảng So sánh Nhà cung cấp

| Provider | TLS Version | Cipher Level | App Password | Đặc biệt |
|----------|-------------|--------------|--------------|----------|
| Gmail | 1.2, 1.3 | Auto/Strict | ✅ Bắt buộc | 2FA required |
| Outlook | 1.0, 1.2 | Legacy/Auto | ❌ Không cần | Port 587 STARTTLS |
| Yahoo | 1.2 | Auto | ✅ Khuyến nghị | Less secure app |
| cPanel | 1.0, 1.1 | Legacy | ❌ Không cần | Tùy hosting |
| ProtonMail | 1.2, 1.3 | Auto | N/A | Dùng Bridge |
| Zoho | 1.2 | Auto | ❌ Không cần | Standard |
| iCloud | 1.2, 1.3 | Strict | ✅ Bắt buộc | No POP3 |

---

## 🛠️ Tools và Commands Hữu ích

### OpenSSL Commands

```bash
# Test kết nối cơ bản
openssl s_client -connect pop.gmail.com:995

# Test với TLS 1.2
openssl s_client -connect pop.gmail.com:995 -tls1_2

# Test với cipher cụ thể
openssl s_client -connect pop.gmail.com:995 -cipher 'AES128-SHA'

# Xem certificate
openssl s_client -connect pop.gmail.com:995 -showcerts

# Debug chi tiết
openssl s_client -connect pop.gmail.com:995 -debug -msg
```

### Python Debug

```python
# Bật SSL debug
import ssl
ssl._DEFAULT_CIPHERS = 'ALL:@SECLEVEL=0'

# Log chi tiết
import logging
logging.basicConfig(level=logging.DEBUG)

# Xem cipher suites available
ctx = ssl.create_default_context()
print([c['name'] for c in ctx.get_ciphers()])
```

### nmap Commands

```bash
# Scan SSL/TLS
nmap --script ssl-enum-ciphers -p 995 pop.gmail.com

# Kiểm tra certificate
nmap --script ssl-cert -p 995 pop.gmail.com
```

---

## 💡 Best Practices

### ✅ Nên làm

1. **Luôn thử `auto` mode trước** - Cân bằng tốt nhất
2. **Dùng App Password** - An toàn hơn mật khẩu thường
3. **Test trước khi deploy** - Dùng `ssl_test.py`
4. **Log errors** - Để debug sau này
5. **Cập nhật dependencies** - Python, OpenSSL mới nhất
6. **Đọc docs của provider** - Mỗi provider khác nhau

### ❌ Không nên làm

1. **Không tắt verify_mode** - Trừ khi localhost
2. **Không dùng TLS 1.0** - Trừ khi bắt buộc
3. **Không hardcode password** - Dùng .env
4. **Không bỏ qua errors** - Xử lý properly
5. **Không dùng legacy** - Trừ khi cần thiết

---

## 🔍 Advanced Debugging

### Khi mọi thứ đều thất bại

```python
# Ultimate debugging script
import ssl
import socket
import poplib

host = "your.mail.server"
port = 995

print("=== COMPREHENSIVE SSL TEST ===\n")

# 1. Raw socket
print("1. Testing raw socket...")
try:
    sock = socket.create_connection((host, port), timeout=10)
    print(f"✅ TCP connection: {sock.getpeername()}")
    sock.close()
except Exception as e:
    print(f"❌ TCP failed: {e}")
    exit(1)

# 2. Try every TLS version
print("\n2. Testing TLS versions...")
for ver_enum, ver_name in [
    (ssl.TLSVersion.TLSv1, "TLS 1.0"),
    (ssl.TLSVersion.TLSv1_1, "TLS 1.1"),
    (ssl.TLSVersion.TLSv1_2, "TLS 1.2"),
    (ssl.TLSVersion.TLSv1_3, "TLS 1.3"),
]:
    try:
        ctx = ssl.create_default_context()
        ctx.minimum_version = ver_enum
        ctx.maximum_version = ver_enum
        ctx.set_ciphers('ALL:@SECLEVEL=0')
        
        sock = socket.create_connection((host, port), timeout=10)
        ssl_sock = ctx.wrap_socket(sock, server_hostname=host)
        
        print(f"✅ {ver_name}: {ssl_sock.cipher()[0]}")
        ssl_sock.close()
    except Exception as e:
        print(f"❌ {ver_name}: {str(e)[:60]}")

# 3. Try every SECLEVEL
print("\n3. Testing security levels...")
for level in [0, 1, 2]:
    try:
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.set_ciphers(f'ALL:@SECLEVEL={level}')
        
        sock = socket.create_connection((host, port), timeout=10)
        ssl_sock = ctx.wrap_socket(sock, server_hostname=host)
        
        print(f"✅ SECLEVEL={level}: {ssl_sock.cipher()[0]}")
        ssl_sock.close()
    except Exception as e:
        print(f"❌ SECLEVEL={level}: {str(e)[:60]}")

# 4. Try specific ciphers
print("\n4. Testing specific ciphers...")
test_ciphers = [
    'ECDHE-RSA-AES128-GCM-SHA256',
    'ECDHE-RSA-AES256-GCM-SHA384',
    'AES128-SHA',
    'AES256-SHA',
    'DES-CBC3-SHA',
]

for cipher in test_ciphers:
    try:
        ctx = ssl.create_default_context()
        ctx.set_ciphers(cipher)
        
        sock = socket.create_connection((host, port), timeout=10)
        ssl_sock = ctx.wrap_socket(sock, server_hostname=host)
        
        print(f"✅ {cipher}")
        ssl_sock.close()
    except:
        print(f"❌ {cipher}")

print("\n=== TEST COMPLETE ===")
```

---

## 📞 Liên hệ Hỗ trợ

### Khi cần liên hệ Admin/Support

Cung cấp thông tin sau:

```
Subject: SSL/TLS Connection Issue to Mail Server

Thông tin:
- Server: mail.example.com:995
- Client: Python 3.13 on [OS]
- Error: [SSL: SSLV3_ALERT_HANDSHAKE_FAILURE]

Test Results:
- TCP Connection: ✅ Success
- TLS 1.2: ❌ Failed
- TLS 1.0: ✅ Success
- Cipher Test: Only AES128-SHA works

Câu hỏi:
1. Server có hỗ trợ TLS 1.2+ không?
2. Danh sách cipher suites được hỗ trợ?
3. Có kế hoạch nâng cấp SSL/TLS không?

Đính kèm: ssl_test_output.txt
```

---

## 🎓 Tài liệu Tham khảo

- [Python SSL Documentation](https://docs.python.org/3/library/ssl.html)
- [OpenSSL Ciphers](https://www.openssl.org/docs/man1.1.1/man1/ciphers.html)
- [Mozilla SSL Config](https://ssl-config.mozilla.org/)
- [SSL Labs](https://www.ssllabs.com/)
- [TLS 1.2 RFC](https://tools.ietf.org/html/rfc5246)

---

**Phiên bản**: 2.0.0  
**Cập nhật cuối**: October 2025  
**Contributors**: Mail Client Development Team