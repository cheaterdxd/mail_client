# 🚀 SSL Handshake Failure - Quick Reference

## ⚡ Xử lý Nhanh (2 phút)

```bash
# 1. Chạy test tự động
python ssl_test.py your.server.com 995

# 2. Thử các mode
python mail_client.py auto      # Thử đầu tiên
python mail_client.py legacy    # Nếu auto fail

# 3. Nếu vẫn lỗi, chạy chẩn đoán
python mail_client.py
# Chọn option 6: Test kết nối chi tiết
```

---

## 🔧 Fix Phổ biến

### Gmail
```bash
python mail_client.py auto
# + Phải dùng App Password (16 chữ số)
# + Bật 2FA trước
```

### Outlook/Office365
```bash
python mail_client.py legacy
# + Có thể cần port 587 STARTTLS
```

### cPanel/Shared Hosting
```bash
python mail_client.py legacy
# + Thường cần TLS 1.0/1.1
```

### Yahoo
```bash
python mail_client.py auto
# + Bật "Less secure apps"
# + Hoặc dùng App Password
```

---

## 📋 Troubleshooting Flowchart

```
Lỗi SSL Handshake?
    ↓
[1] Test TCP: python ssl_test.py <host> <port>
    ↓
TCP OK?
    ├─ NO → Kiểm tra firewall/port/hostname
    └─ YES → Tiếp tục
        ↓
[2] Thử auto mode
    ↓
Hoạt động?
    ├─ YES → ✅ Done!
    └─ NO → Thử legacy mode
        ↓
Hoạt động?
    ├─ YES → ✅ Done!
    └─ NO → Chạy chẩn đoán chi tiết (option 6)
        ↓
Xem kết quả → Cấu hình tùy chỉnh
```

---

## 🎯 Code Fix Nhanh

### Fix 1: Thêm vào __init__
```python
# Thêm sau dòng self.ssl_context = ...
self.ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')
```

### Fix 2: Cho server RẤT cũ
```python
self.ssl_context.set_ciphers('ALL:@SECLEVEL=0')
self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1
```

### Fix 3: Localhost (ProtonMail Bridge)
```python
self.ssl_context.check_hostname = False
self.ssl_context.verify_mode = ssl.CERT_NONE
```

---

## 🐛 Debug Commands

```bash
# Test OpenSSL
openssl s_client -connect pop.gmail.com:995

# Test TLS 1.2
openssl s_client -connect pop.gmail.com:995 -tls1_2

# Scan ciphers
nmap --script ssl-enum-ciphers -p 995 pop.gmail.com
```

---

## 📊 Bảng Nhanh

| Lỗi | Nguyên nhân | Fix |
|-----|-------------|-----|
| HANDSHAKE_FAILURE | Cipher không match | Thử legacy mode |
| WRONG_VERSION | TLS version | Hạ TLS version |
| CERTIFICATE_VERIFY | Cert không hợp lệ | Check hostname |
| TIMEOUT | Firewall/Network | Check port/firewall |
| AUTH_FAILED | Sai password | Check credentials |

---

## 💡 3 Điều Nhớ

1. **Luôn thử `auto` trước** ✅
2. **Dùng `ssl_test.py` để chẩn đoán** 🔍
3. **Đọc error message kỹ** 📖

---

## 🆘 Khi Cần Giúp

1. Chạy: `python ssl_test.py <host> <port> > debug.txt`
2. Gửi file `debug.txt`
3. Kèm info: OS, Python version, provider

---

**Quick Help**: Chọn option 5 hoặc 6 trong menu để tự động chẩn đoán!