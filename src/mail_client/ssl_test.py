#!/usr/bin/env python3
"""
SSL Connection Test Script
Script độc lập để test kết nối SSL/TLS đến mail server

Sử dụng: python ssl_test.py [host] [port]
Ví dụ: python ssl_test.py pop.gmail.com 995
"""

import ssl
import socket
import sys
from datetime import datetime


def print_header(title):
    """In header đẹp"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_tcp_connection(host, port):
    """Test kết nối TCP cơ bản"""
    print_header("1. TEST KẾT NỐI TCP")

    try:
        start = datetime.now()
        sock = socket.create_connection((host, port), timeout=10)
        elapsed = (datetime.now() - start).total_seconds()

        print(f"✅ Kết nối thành công đến {host}:{port}")
        print(f"⏱️  Thời gian: {elapsed:.2f}s")

        # Lấy thông tin địa chỉ
        peer = sock.getpeername()
        print(f"📍 Server IP: {peer[0]}:{peer[1]}")

        sock.close()
        return True

    except socket.timeout:
        print(f"❌ TIMEOUT - Server không phản hồi sau 10s")
        return False
    except socket.gaierror as e:
        print(f"❌ KHÔNG THỂ RESOLVE HOSTNAME")
        print(f"   Lỗi: {e}")
        return False
    except ConnectionRefusedError:
        print(f"❌ KẾT NỐI BỊ TỪ CHỐI")
        print(f"   Port {port} có thể không mở hoặc firewall chặn")
        return False
    except Exception as e:
        print(f"❌ LỖI: {e}")
        return False


def test_ssl_versions(host, port):
    """Test các phiên bản SSL/TLS"""
    print_header("2. TEST CÁC PHIÊN BẢN TLS")

    versions = [
        (ssl.TLSVersion.TLSv1_3, "TLS 1.3", "Mới nhất, bảo mật cao nhất"),
        (ssl.TLSVersion.TLSv1_2, "TLS 1.2", "Tiêu chuẩn hiện tại"),
        (ssl.TLSVersion.TLSv1_1, "TLS 1.1", "Deprecated - Không nên dùng"),
        (ssl.TLSVersion.TLSv1, "TLS 1.0", "Deprecated - Có lỗ hổng bảo mật"),
    ]

    working_versions = []

    for tls_enum, name, desc in versions:
        try:
            ctx = ssl.create_default_context()
            ctx.minimum_version = tls_enum
            ctx.maximum_version = tls_enum
            ctx.set_ciphers("ALL:@SECLEVEL=0")  # Cho phép tất cả để test

            sock = socket.create_connection((host, port), timeout=10)
            ssl_sock = ctx.wrap_socket(sock, server_hostname=host)

            cipher_info = ssl_sock.cipher()
            cert = ssl_sock.getpeercert()

            print(f"\n✅ {name}")
            print(f"   📝 {desc}")
            print(f"   🔐 Cipher: {cipher_info[0]}")
            print(f"   📊 Bits: {cipher_info[2]}")
            print(f"   📜 Protocol: {ssl_sock.version()}")

            if cert:
                subject = dict(x[0] for x in cert["subject"])
                print(f"   📄 Cert CN: {subject.get('commonName', 'N/A')}")

            working_versions.append(name)
            ssl_sock.close()

        except ssl.SSLError as e:
            print(f"\n❌ {name}")
            print(f"   📝 {desc}")
            print(f"   ⚠️  Lỗi: {str(e)[:70]}")
        except Exception as e:
            print(f"\n⚠️  {name}: {str(e)[:70]}")

    if working_versions:
        print(f"\n💡 Server hỗ trợ: {', '.join(working_versions)}")
        return working_versions
    else:
        print("\n❌ Server không hỗ trợ bất kỳ TLS version nào")
        return []


def test_cipher_suites(host, port):
    """Test các cipher suite"""
    print_header("3. TEST CIPHER SUITES")

    cipher_configs = [
        (
            "DEFAULT:@SECLEVEL=2",
            "Modern (SECLEVEL=2)",
            "Chỉ cipher mạnh: RSA 2048+, No SHA1",
        ),
        (
            "DEFAULT:@SECLEVEL=1",
            "Balanced (SECLEVEL=1)",
            "Cân bằng: RSA 1024+, SHA1 trong signatures",
        ),
        ("ALL:@SECLEVEL=0", "Legacy (SECLEVEL=0)", "Tất cả cipher, kể cả yếu"),
        (
            "ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-GCM-SHA256",
            "ECDHE Only",
            "Chỉ Elliptic Curve",
        ),
        ("AES128-SHA:AES256-SHA", "AES-SHA Only", "RSA với AES-SHA (cũ)"),
    ]

    working_configs = []

    for cipher_str, name, desc in cipher_configs:
        try:
            ctx = ssl.create_default_context()
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.set_ciphers(cipher_str)

            sock = socket.create_connection((host, port), timeout=10)
            ssl_sock = ctx.wrap_socket(sock, server_hostname=host)

            cipher_info = ssl_sock.cipher()

            print(f"\n✅ {name}")
            print(f"   📝 {desc}")
            print(f"   🔐 Cipher được chọn: {cipher_info[0]}")
            print(f"   📊 Bits: {cipher_info[2]}")
            print(f"   🔧 Config: {cipher_str[:50]}...")

            working_configs.append((name, cipher_str))
            ssl_sock.close()

        except ssl.SSLError as e:
            print(f"\n❌ {name}")
            print(f"   📝 {desc}")
            error_msg = str(e)
            if "HANDSHAKE_FAILURE" in error_msg:
                print(f"   ⚠️  Server từ chối cipher suite này")
            else:
                print(f"   ⚠️  Lỗi: {error_msg[:70]}")
        except Exception as e:
            print(f"\n⚠️  {name}: {str(e)[:70]}")

    return working_configs


def test_certificate(host, port):
    """Kiểm tra thông tin certificate"""
    print_header("4. THÔNG TIN CERTIFICATE")

    try:
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")

        sock = socket.create_connection((host, port), timeout=10)
        ssl_sock = ctx.wrap_socket(sock, server_hostname=host)

        cert = ssl_sock.getpeercert()

        if cert:
            print(f"\n📜 Certificate Info:")

            # Subject
            subject = dict(x[0] for x in cert.get("subject", []))
            print(f"\n   Common Name (CN): {subject.get('commonName', 'N/A')}")
            print(f"   Organization: {subject.get('organizationName', 'N/A')}")

            # Issuer
            issuer = dict(x[0] for x in cert.get("issuer", []))
            print(f"\n   Issuer: {issuer.get('commonName', 'N/A')}")
            print(f"   Issuer Org: {issuer.get('organizationName', 'N/A')}")

            # Validity
            print(f"\n   Valid From: {cert.get('notBefore', 'N/A')}")
            print(f"   Valid To: {cert.get('notAfter', 'N/A')}")

            # Subject Alternative Names
            san = cert.get("subjectAltName", [])
            if san:
                print(f"\n   Subject Alternative Names:")
                for typ, val in san[:5]:  # Chỉ hiện 5 đầu
                    print(f"      • {val}")
                if len(san) > 5:
                    print(f"      ... và {len(san)-5} nữa")
        else:
            print("⚠️  Không lấy được thông tin certificate")

        ssl_sock.close()
        return True

    except Exception as e:
        print(f"❌ Lỗi khi lấy certificate: {e}")
        return False


def generate_recommendations(working_versions, working_ciphers):
    """Đưa ra khuyến nghị"""
    print_header("5. KHUYẾN NGHỊ")

    if not working_versions:
        print("\n❌ KHÔNG THỂ KẾT NỐI")
        print("\n🔧 Các bước kiểm tra:")
        print("   1. Kiểm tra firewall/antivirus")
        print("   2. Thử từ mạng khác")
        print("   3. Xác nhận host và port đúng")
        print("   4. Liên hệ admin server")
        return

    print("\n✅ KẾT NỐI THÀNH CÔNG")

    # Khuyến nghị TLS version
    print("\n📌 TLS Version:")
    if "TLS 1.3" in working_versions or "TLS 1.2" in working_versions:
        print("   ✅ Server hỗ trợ TLS hiện đại")
        print("   💡 Sử dụng: ctx.minimum_version = ssl.TLSVersion.TLSv1_2")
    else:
        print("   ⚠️  Server chỉ hỗ trợ TLS cũ (1.0/1.1)")
        print("   💡 Cân nhắc nâng cấp server")

    # Khuyến nghị Cipher Suite
    if working_ciphers:
        print("\n📌 Cipher Suite:")

        best_config = working_ciphers[0]
        print(f"   ✅ Khuyến nghị: {best_config[0]}")
        print(f"   🔧 Code Python:")
        print(f"      ctx.set_ciphers('{best_config[1]}')")

        if len(working_ciphers) > 1:
            print(f"\n   📋 Các lựa chọn khác ({len(working_ciphers)-1}):")
            for name, _ in working_ciphers[1:3]:
                print(f"      • {name}")

    # Khuyến nghị cho Mail Client
    print("\n📌 Cho Mail Client App:")

    if any("Modern" in c[0] or "Balanced" in c[0] for c in working_ciphers):
        print("   ✅ python mail_client.py auto")
        print("      (Hoặc strict nếu muốn bảo mật cao hơn)")
    elif any("Legacy" in c[0] for c in working_ciphers):
        print("   ⚠️  python mail_client.py legacy")
        print("      (Server yêu cầu cipher cũ)")
    else:
        print("   🔧 Có thể cần cấu hình tùy chỉnh")


def main():
    """Main function"""
    print("=" * 70)
    print(" SSL/TLS CONNECTION TEST TOOL")
    print(" Version 1.0.0")
    print("=" * 70)

    # Lấy tham số
    if len(sys.argv) >= 3:
        host = sys.argv[1]
        port = int(sys.argv[2])
    else:
        print("\nSử dụng: python ssl_test.py [host] [port]")
        print("\nVí dụ:")
        print("  python ssl_test.py pop.gmail.com 995")
        print("  python ssl_test.py smtp.gmail.com 465")
        print("  python ssl_test.py outlook.office365.com 995")

        host = input("\nNhập hostname: ").strip()
        if not host:
            print("❌ Hostname không được để trống")
            return

        port_input = input("Nhập port (995 cho POP3-SSL): ").strip()
        try:
            port = int(port_input) if port_input else 995
        except ValueError:
            print("❌ Port phải là số")
            return

    print(f"\n🎯 Target: {host}:{port}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Chạy các test
    tcp_ok = test_tcp_connection(host, port)

    if not tcp_ok:
        print("\n❌ Không thể kết nối TCP. Dừng test.")
        return

    working_versions = test_ssl_versions(host, port)
    working_ciphers = test_cipher_suites(host, port)
    test_certificate(host, port)
    generate_recommendations(working_versions, working_ciphers)

    print("\n" + "=" * 70)
    print(f" ⏰ Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test bị dừng bởi người dùng")
    except Exception as e:
        print(f"\n\n❌ Lỗi không mong đợi: {e}")
        import traceback

        traceback.print_exc()
