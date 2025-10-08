import ssl
import poplib

ctx = ssl.create_default_context()
ctx.set_ciphers("DEFAULT:@SECLEVEL=1")

# Xem các cipher khả dụng
print([c["name"] for c in ctx.get_ciphers()])

# Test kết nối
try:
    conn = poplib.POP3_SSL("pop3.viettel.com.vn", 995, context=ctx)
    print("✅ Kết nối thành công!")
    conn.quit()
except Exception as e:
    print(f"❌ Lỗi: {e}")
