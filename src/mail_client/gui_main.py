"""
Mail Client GUI Application
Phiên bản: 3.0.0 - GUI Edition
Font: K2D (Google Fonts)
Phong cách: Modern, Clean, Rounded
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import os
import sys
import traceback
from pathlib import Path
from datetime import datetime
from email import policy
from email.parser import BytesParser
import threading
import queue

# Import mail client backend
try:
    from mail_client import MailClient, log_error

    BACKEND_AVAILABLE = True
except ImportError:
    BACKEND_AVAILABLE = False
    print("⚠️  Backend mail_client.py không tìm thấy")


# ============================================================
# COLOR SCHEMES - Modern Email Client Colors
# ============================================================
class ColorScheme:
    """
    Bảng màu hiện đại cho email client
    Tham khảo: Gmail, Outlook, Apple Mail
    """

    # Light Mode (Default)
    LIGHT = {
        "bg_primary": "#FFFFFF",  # Nền chính
        "bg_secondary": "#F8F9FA",  # Nền phụ (sidebar)
        "bg_hover": "#E8EAED",  # Hover state
        "bg_selected": "#C2E7FF",  # Selected item
        "text_primary": "#202124",  # Text chính
        "text_secondary": "#5F6368",  # Text phụ
        "accent_primary": "#1A73E8",  # Màu chủ đạo (xanh dương)
        "accent_secondary": "#34A853",  # Màu phụ (xanh lá)
        "border": "#DADCE0",  # Viền
        "tag_bg": "#E8F0FE",  # Background tag
        "tag_text": "#1967D2",  # Text tag
        "unread_bg": "#F1F3F4",  # Email chưa đọc
        "error": "#D93025",  # Màu lỗi
        "warning": "#F9AB00",  # Màu cảnh báo
        "success": "#34A853",  # Màu thành công
    }

    # Dark Mode (Optional)
    DARK = {
        "bg_primary": "#202124",
        "bg_secondary": "#292A2D",
        "bg_hover": "#3C4043",
        "bg_selected": "#1A3A52",
        "text_primary": "#E8EAED",
        "text_secondary": "#9AA0A6",
        "accent_primary": "#8AB4F8",
        "accent_secondary": "#81C995",
        "border": "#3C4043",
        "tag_bg": "#1A3A52",
        "tag_text": "#8AB4F8",
        "unread_bg": "#292A2D",
        "error": "#F28B82",
        "warning": "#FDD663",
        "success": "#81C995",
    }


# ============================================================
# CONFIGURATION MANAGER
# ============================================================
class ConfigManager:
    """Quản lý cấu hình ứng dụng"""

    CONFIG_FILE = "gui_config.json"

    DEFAULT_CONFIG = {
        "font_size": 10,
        "theme": "light",
        "window_width": 1200,
        "window_height": 700,
        "show_preview": True,
        "auto_fetch_interval": 300,  # seconds
    }

    @staticmethod
    def load():
        """Load cấu hình"""
        try:
            if os.path.exists(ConfigManager.CONFIG_FILE):
                with open(ConfigManager.CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # Merge với default để đảm bảo có đủ keys
                    return {**ConfigManager.DEFAULT_CONFIG, **config}
            return ConfigManager.DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"⚠️  Lỗi load config: {e}")
            return ConfigManager.DEFAULT_CONFIG.copy()

    @staticmethod
    def save(config):
        """Lưu cấu hình"""
        try:
            with open(ConfigManager.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Lỗi save config: {e}")


# ============================================================
# TAGS MANAGER
# ============================================================
class TagsManager:
    """Quản lý tags cho emails"""

    TAGS_FILE = "email_tags.json"

    def __init__(self):
        self.tags_data = self.load()

    def load(self):
        """Load tags từ file"""
        try:
            if os.path.exists(self.TAGS_FILE):
                with open(self.TAGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"⚠️  Lỗi load tags: {e}")
            return {}

    def save(self):
        """Lưu tags"""
        try:
            with open(self.TAGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tags_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Lỗi save tags: {e}")

    def get_tags(self, email_id):
        """Lấy tags của email"""
        return self.tags_data.get(email_id, [])

    def add_tag(self, email_id, tag):
        """Thêm tag cho email"""
        if email_id not in self.tags_data:
            self.tags_data[email_id] = []
        if tag not in self.tags_data[email_id]:
            self.tags_data[email_id].append(tag)
            self.save()

    def remove_tag(self, email_id, tag):
        """Xóa tag"""
        if email_id in self.tags_data and tag in self.tags_data[email_id]:
            self.tags_data[email_id].remove(tag)
            self.save()

    def get_all_tags(self):
        """Lấy tất cả tags đã dùng"""
        all_tags = set()
        for tags in self.tags_data.values():
            all_tags.update(tags)
        return sorted(list(all_tags))


# ============================================================
# EMAIL DATA MODEL
# ============================================================
class EmailData:
    """Model cho một email"""

    def __init__(self, folder_path):
        self.folder_path = Path(folder_path)
        self.folder_name = self.folder_path.name

        # Parse email ID và subject từ folder name
        parts = self.folder_name.split("_", 1)
        self.email_id = parts[0]
        self.subject = parts[1] if len(parts) > 1 else "No Subject"

        # Load email content
        self.eml_file = self.folder_path / "full_email.eml"
        self.msg = None
        self.from_addr = ""
        self.to_addr = ""
        self.cc_addr = ""
        self.bcc_addr = ""
        self.date = ""
        self.body = ""
        self.attachments = []

        self._load_email()

    def _load_email(self):
        """Load và parse email từ file .eml"""
        try:
            if self.eml_file.exists():
                with open(self.eml_file, "rb") as f:
                    self.msg = BytesParser(policy=policy.default).parse(f)

                # Extract headers
                self.from_addr = self._decode_header(self.msg.get("From", ""))
                self.to_addr = self._decode_header(self.msg.get("To", ""))
                self.cc_addr = self._decode_header(self.msg.get("Cc", ""))
                self.bcc_addr = self._decode_header(self.msg.get("Bcc", ""))
                self.date = self.msg.get("Date", "")

                # Extract body
                self.body = self._get_body()

                # List attachments
                self.attachments = [
                    f.name
                    for f in self.folder_path.iterdir()
                    if f.name != "full_email.eml"
                ]

        except Exception as e:
            print(f"⚠️  Lỗi load email {self.folder_name}: {e}")
            traceback.print_exc()

    def _decode_header(self, header_value):
        """Decode email header có Unicode"""
        if not header_value:
            return ""
        try:
            from email.header import decode_header

            decoded_parts = decode_header(str(header_value))
            result = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result.append(part.decode(encoding or "utf-8", errors="replace"))
                else:
                    result.append(str(part))
            return "".join(result)
        except:
            return str(header_value)

    def _get_body(self):
        """Extract body text từ email"""
        if not self.msg:
            return ""

        try:
            if self.msg.is_multipart():
                for part in self.msg.walk():
                    content_type = part.get_content_type()
                    disposition = str(part.get("Content-Disposition"))

                    if "attachment" in disposition:
                        continue

                    if content_type == "text/plain":
                        return part.get_payload(decode=True).decode(errors="replace")
                    elif content_type == "text/html" and not hasattr(
                        self, "_body_found"
                    ):
                        self._body_found = True
                        # Strip HTML tags (basic)
                        html_body = part.get_payload(decode=True).decode(
                            errors="replace"
                        )
                        return self._strip_html(html_body)
            else:
                return self.msg.get_payload(decode=True).decode(errors="replace")
        except:
            return "Error loading email body"

        return ""

    def _strip_html(self, html):
        """Strip HTML tags (basic)"""
        import re

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", html)
        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")
        return text.strip()


# ============================================================
# MAIN GUI APPLICATION
# ============================================================
class MailClientGUI:
    """Main GUI Application"""

    def __init__(self, root):
        self.root = root
        self.root.title("📧 Mail Client - Modern Edition")

        # Load configuration
        self.config = ConfigManager.load()
        self.colors = ColorScheme.LIGHT  # Mặc định light mode
        self.tags_manager = TagsManager()

        # State
        self.emails = []
        self.filtered_emails = []
        self.selected_email = None
        self.current_filter_tag = None

        # Backend
        self.mail_client = None
        self.fetch_queue = queue.Queue()

        # Setup window
        self._setup_window()

        # Setup font
        self._setup_fonts()

        # Build UI
        self._build_ui()

        # Load emails
        self.load_emails()

        # Bind shortcuts
        self._setup_shortcuts()

    def _setup_window(self):
        """Cấu hình cửa sổ chính"""
        # Size
        width = self.config["window_width"]
        height = self.config["window_height"]

        # Center on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(900, 600)

        # Colors
        self.root.configure(bg=self.colors["bg_primary"])

        # Icon (nếu có)
        try:
            # self.root.iconbitmap('icon.ico')
            pass
        except:
            pass

    def _setup_fonts(self):
        """Setup fonts - K2D"""
        try:
            # Try to use K2D font if available
            import tkinter.font as tkfont

            self.font_family = "K2D"
            # Fallback fonts
            available_fonts = list(tkfont.families())
            if "K2D" not in available_fonts:
                # Fallback to similar fonts
                for fallback in ["Segoe UI", "Arial", "Helvetica"]:
                    if fallback in available_fonts:
                        self.font_family = fallback
                        break

            size = self.config["font_size"]

            self.fonts = {
                "default": (self.font_family, size),
                "bold": (self.font_family, size, "bold"),
                "heading": (self.font_family, size + 2, "bold"),
                "large": (self.font_family, size + 4, "bold"),
                "small": (self.font_family, size - 1),
            }

        except Exception as e:
            print(f"⚠️  Lỗi setup font: {e}")
            # Fallback to default
            self.fonts = {
                "default": ("Arial", 10),
                "bold": ("Arial", 10, "bold"),
                "heading": ("Arial", 12, "bold"),
                "large": ("Arial", 14, "bold"),
                "small": ("Arial", 9),
            }

    def _build_ui(self):
        """Xây dựng giao diện"""
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # ====== TOOLBAR ======
        self._build_toolbar(main_container)

        # ====== MAIN CONTENT ======
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Left Panel - Sidebar (Tags + Filters)
        self._build_sidebar(content_frame)

        # Right Panel - Email List + Preview
        self._build_email_panel(content_frame)

        # ====== STATUSBAR ======
        self._build_statusbar(main_container)

    def _build_toolbar(self, parent):
        """Build toolbar"""
        toolbar = tk.Frame(parent, bg=self.colors["bg_secondary"], height=50)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        toolbar.pack_propagate(False)

        # Left side buttons
        left_frame = tk.Frame(toolbar, bg=self.colors["bg_secondary"])
        left_frame.pack(side=tk.LEFT, padx=10, pady=5)

        # Fetch button
        fetch_btn = tk.Button(
            left_frame,
            text="📥 Fetch New",
            command=self.fetch_emails,
            font=self.fonts["bold"],
            bg=self.colors["accent_primary"],
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2",
        )
        fetch_btn.pack(side=tk.LEFT, padx=5)
        self._apply_rounded_style(fetch_btn)

        # Compose button
        compose_btn = tk.Button(
            left_frame,
            text="✏️  Compose",
            command=self.compose_email,
            font=self.fonts["bold"],
            bg=self.colors["accent_secondary"],
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2",
        )
        compose_btn.pack(side=tk.LEFT, padx=5)
        self._apply_rounded_style(compose_btn)

        # Right side buttons
        right_frame = tk.Frame(toolbar, bg=self.colors["bg_secondary"])
        right_frame.pack(side=tk.RIGHT, padx=10, pady=5)

        # Settings button
        settings_btn = tk.Button(
            right_frame,
            text="⚙️  Settings",
            command=self.open_settings,
            font=self.fonts["default"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            relief=tk.FLAT,
            padx=12,
            pady=8,
            cursor="hand2",
        )
        settings_btn.pack(side=tk.RIGHT, padx=5)
        self._apply_rounded_style(settings_btn)

        # Refresh button
        refresh_btn = tk.Button(
            right_frame,
            text="🔄 Refresh",
            command=self.load_emails,
            font=self.fonts["default"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            relief=tk.FLAT,
            padx=12,
            pady=8,
            cursor="hand2",
        )
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        self._apply_rounded_style(refresh_btn)

    def _build_sidebar(self, parent):
        """Build sidebar với tags và filters"""
        sidebar = tk.Frame(parent, bg=self.colors["bg_secondary"], width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        sidebar.pack_propagate(False)

        # Title
        title = tk.Label(
            sidebar,
            text="📂 Tags & Filters",
            font=self.fonts["heading"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            anchor="w",
        )
        title.pack(fill=tk.X, padx=10, pady=10)

        # All emails button
        all_btn = tk.Button(
            sidebar,
            text="📧 All Emails",
            command=lambda: self.filter_by_tag(None),
            font=self.fonts["default"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            relief=tk.FLAT,
            anchor="w",
            padx=15,
            pady=8,
            cursor="hand2",
        )
        all_btn.pack(fill=tk.X, padx=10, pady=2)
        self._apply_rounded_style(all_btn)

        # Tags list frame
        tags_frame = tk.Frame(sidebar, bg=self.colors["bg_secondary"])
        tags_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Scrollable tags
        tags_canvas = tk.Canvas(
            tags_frame, bg=self.colors["bg_secondary"], highlightthickness=0
        )
        tags_scrollbar = ttk.Scrollbar(
            tags_frame, orient="vertical", command=tags_canvas.yview
        )

        self.tags_container = tk.Frame(tags_canvas, bg=self.colors["bg_secondary"])

        tags_canvas.create_window((0, 0), window=self.tags_container, anchor="nw")
        tags_canvas.configure(yscrollcommand=tags_scrollbar.set)

        tags_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tags_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tags_container.bind(
            "<Configure>",
            lambda e: tags_canvas.configure(scrollregion=tags_canvas.bbox("all")),
        )

        # Update tags list
        self.update_tags_list()

    def _build_email_panel(self, parent):
        """Build panel hiển thị danh sách email"""
        email_panel = tk.Frame(parent, bg=self.colors["bg_primary"])
        email_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(email_panel, bg=self.colors["bg_secondary"], height=40)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        self.email_count_label = tk.Label(
            header,
            text="📬 0 emails",
            font=self.fonts["heading"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            anchor="w",
        )
        self.email_count_label.pack(side=tk.LEFT, padx=15, pady=10)

        # Email list với scrollbar
        list_frame = tk.Frame(email_panel, bg=self.colors["bg_primary"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Canvas cho scrolling
        self.email_canvas = tk.Canvas(
            list_frame, bg=self.colors["bg_primary"], highlightthickness=0
        )
        email_scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.email_canvas.yview
        )

        self.email_list_container = tk.Frame(
            self.email_canvas, bg=self.colors["bg_primary"]
        )

        self.email_canvas.create_window(
            (0, 0),
            window=self.email_list_container,
            anchor="nw",
            width=self.email_canvas.winfo_width(),
        )
        self.email_canvas.configure(yscrollcommand=email_scrollbar.set)

        self.email_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        email_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind resize
        self.email_canvas.bind("<Configure>", self._on_canvas_configure)
        self.email_list_container.bind(
            "<Configure>",
            lambda e: self.email_canvas.configure(
                scrollregion=self.email_canvas.bbox("all")
            ),
        )

        # Mouse wheel scrolling
        self.email_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _build_statusbar(self, parent):
        """Build status bar"""
        statusbar = tk.Frame(parent, bg=self.colors["bg_secondary"], height=30)
        statusbar.pack(fill=tk.X, pady=(5, 0))
        statusbar.pack_propagate(False)

        self.status_label = tk.Label(
            statusbar,
            text="Ready",
            font=self.fonts["small"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_secondary"],
            anchor="w",
        )
        self.status_label.pack(side=tk.LEFT, padx=10)

    def _apply_rounded_style(self, widget):
        """Apply rounded corner style (visual effect)"""
        # Tkinter không hỗ trợ border-radius trực tiếp
        # Nhưng ta có thể dùng relief=FLAT và padding để tạo cảm giác rounded
        widget.configure(relief=tk.FLAT)

    def _on_canvas_configure(self, event):
        """Handle canvas resize"""
        canvas_width = event.width
        self.email_canvas.itemconfig(
            self.email_canvas.find_all()[0], width=canvas_width
        )

    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll"""
        self.email_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind("<F5>", lambda e: self.load_emails())
        self.root.bind("<Control-r>", lambda e: self.load_emails())
        self.root.bind("<Control-n>", lambda e: self.compose_email())
        self.root.bind("<Control-f>", lambda e: self.fetch_emails())

    # ============================================================
    # EMAIL OPERATIONS
    # ============================================================

    def load_emails(self):
        """Load emails từ offline storage"""
        try:
            self.status_label.config(text="Loading emails...")
            self.root.update()

            storage_dir = Path("D:\\root_folder\\rieng\\emails_offline")
            if not storage_dir.exists():
                storage_dir.mkdir()
                self.status_label.config(text="No emails found")
                return

            # Get all email folders
            email_folders = sorted(
                [d for d in storage_dir.iterdir() if d.is_dir()],
                key=lambda x: x.stat().st_mtime,
                reverse=True,
            )

            # Load emails
            self.emails = []
            for folder in email_folders:
                try:
                    email = EmailData(folder)
                    self.emails.append(email)
                except Exception as e:
                    print(f"⚠️  Lỗi load {folder.name}: {e}")

            # Apply current filter
            self.filter_by_tag(self.current_filter_tag)

            self.status_label.config(text=f"Loaded {len(self.emails)} emails")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load emails:\n{e}")
            traceback.print_exc()

    def display_emails(self, emails=None):
        """Hiển thị danh sách emails"""
        # Clear current list
        for widget in self.email_list_container.winfo_children():
            widget.destroy()

        if emails is None:
            emails = self.filtered_emails

        # Update count
        self.email_count_label.config(text=f"📬 {len(emails)} emails")

        # Display each email
        for email in emails:
            self._create_email_item(email)

    def _create_email_item(self, email):
        """Tạo một email item trong list"""
        # Container frame
        item_frame = tk.Frame(
            self.email_list_container,
            bg=self.colors["bg_primary"],
            relief=tk.FLAT,
            borderwidth=1,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        item_frame.pack(fill=tk.X, padx=5, pady=3)

        # Make clickable
        item_frame.bind("<Button-1>", lambda e: self.show_email_detail(email))
        item_frame.bind(
            "<Enter>", lambda e: item_frame.config(bg=self.colors["bg_hover"])
        )
        item_frame.bind(
            "<Leave>", lambda e: item_frame.config(bg=self.colors["bg_primary"])
        )

        # Content frame
        content = tk.Frame(item_frame, bg=self.colors["bg_primary"])
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # Top row: From + Date
        top_row = tk.Frame(content, bg=self.colors["bg_primary"])
        top_row.pack(fill=tk.X)

        from_label = tk.Label(
            top_row,
            text=email.from_addr[:50] + ("..." if len(email.from_addr) > 50 else ""),
            font=self.fonts["bold"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            anchor="w",
        )
        from_label.pack(side=tk.LEFT)
        from_label.bind("<Button-1>", lambda e: self.show_email_detail(email))

        date_label = tk.Label(
            top_row,
            text=email.date[:20] if email.date else "",
            font=self.fonts["small"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"],
            anchor="e",
        )
        date_label.pack(side=tk.RIGHT)
        date_label.bind("<Button-1>", lambda e: self.show_email_detail(email))

        # Subject
        subject_label = tk.Label(
            content,
            text=email.subject[:80] + ("..." if len(email.subject) > 80 else ""),
            font=self.fonts["default"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            anchor="w",
            justify=tk.LEFT,
        )
        subject_label.pack(fill=tk.X, pady=(3, 0))
        subject_label.bind("<Button-1>", lambda e: self.show_email_detail(email))

        # Tags row
        tags = self.tags_manager.get_tags(email.email_id)
        if tags:
            tags_row = tk.Frame(content, bg=self.colors["bg_primary"])
            tags_row.pack(fill=tk.X, pady=(5, 0))
            tags_row.bind("<Button-1>", lambda e: self.show_email_detail(email))

            for tag in tags[:3]:  # Show max 3 tags
                tag_label = tk.Label(
                    tags_row,
                    text=f"🏷️ {tag}",
                    font=self.fonts["small"],
                    bg=self.colors["tag_bg"],
                    fg=self.colors["tag_text"],
                    padx=8,
                    pady=2,
                )
                tag_label.pack(side=tk.LEFT, padx=(0, 5))
                tag_label.bind("<Button-1>", lambda e: self.show_email_detail(email))

        # Attachments indicator
        if email.attachments:
            attach_label = tk.Label(
                content,
                text=f"📎 {len(email.attachments)} attachment(s)",
                font=self.fonts["small"],
                bg=self.colors["bg_primary"],
                fg=self.colors["text_secondary"],
                anchor="w",
            )
            attach_label.pack(fill=tk.X, pady=(3, 0))
            attach_label.bind("<Button-1>", lambda e: self.show_email_detail(email))

    def show_email_detail(self, email):
        """Hiển thị chi tiết email trong popup window"""
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"📧 {email.subject}")
        detail_window.geometry("900x700")
        detail_window.configure(bg=self.colors["bg_primary"])

        # Make modal
        detail_window.transient(self.root)
        detail_window.grab_set()

        # Main container
        main_container = tk.Frame(detail_window, bg=self.colors["bg_primary"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ====== HEADER SECTION ======
        header_frame = tk.Frame(main_container, bg=self.colors["bg_secondary"])
        header_frame.pack(fill=tk.X, pady=(0, 10))

        # Subject
        subject_label = tk.Label(
            header_frame,
            text=email.subject,
            font=self.fonts["large"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            wraplength=850,
            justify=tk.LEFT,
            anchor="w",
        )
        subject_label.pack(fill=tk.X, padx=15, pady=(15, 10))

        # From
        from_row = self._create_detail_row(header_frame, "From:", email.from_addr)

        # To
        if email.to_addr:
            to_row = self._create_detail_row(header_frame, "To:", email.to_addr)

        # CC
        if email.cc_addr:
            cc_row = self._create_detail_row(header_frame, "CC:", email.cc_addr)

        # BCC
        if email.bcc_addr:
            bcc_row = self._create_detail_row(header_frame, "BCC:", email.bcc_addr)

        # Date
        date_row = self._create_detail_row(header_frame, "Date:", email.date)

        # Attachments
        if email.attachments:
            attach_frame = tk.Frame(header_frame, bg=self.colors["bg_secondary"])
            attach_frame.pack(fill=tk.X, padx=15, pady=5)

            attach_label = tk.Label(
                attach_frame,
                text="📎 Attachments:",
                font=self.fonts["bold"],
                bg=self.colors["bg_secondary"],
                fg=self.colors["text_primary"],
                width=12,
                anchor="w",
            )
            attach_label.pack(side=tk.LEFT)

            attach_list = tk.Frame(attach_frame, bg=self.colors["bg_secondary"])
            attach_list.pack(side=tk.LEFT, fill=tk.X, expand=True)

            for att in email.attachments:
                att_btn = tk.Button(
                    attach_list,
                    text=f"📄 {att}",
                    command=lambda a=att, e=email: self.open_attachment(e, a),
                    font=self.fonts["small"],
                    bg=self.colors["bg_primary"],
                    fg=self.colors["accent_primary"],
                    relief=tk.FLAT,
                    cursor="hand2",
                    anchor="w",
                )
                att_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Tags section
        tags_frame = tk.Frame(header_frame, bg=self.colors["bg_secondary"])
        tags_frame.pack(fill=tk.X, padx=15, pady=(10, 15))

        tags_label = tk.Label(
            tags_frame,
            text="🏷️  Tags:",
            font=self.fonts["bold"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
        )
        tags_label.pack(side=tk.LEFT, padx=(0, 10))

        # Current tags
        current_tags = self.tags_manager.get_tags(email.email_id)
        for tag in current_tags:
            tag_btn = tk.Button(
                tags_frame,
                text=f"{tag} ✕",
                command=lambda t=tag, e=email: self.remove_tag_from_email(
                    e, t, detail_window
                ),
                font=self.fonts["small"],
                bg=self.colors["tag_bg"],
                fg=self.colors["tag_text"],
                relief=tk.FLAT,
                cursor="hand2",
                padx=8,
                pady=2,
            )
            tag_btn.pack(side=tk.LEFT, padx=2)

        # Add tag button
        add_tag_btn = tk.Button(
            tags_frame,
            text="+ Add Tag",
            command=lambda e=email: self.add_tag_to_email(e, detail_window),
            font=self.fonts["small"],
            bg=self.colors["accent_primary"],
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            pady=2,
        )
        add_tag_btn.pack(side=tk.LEFT, padx=5)

        # ====== BODY SECTION ======
        body_frame = tk.Frame(main_container, bg=self.colors["bg_primary"])
        body_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Body label
        body_label = tk.Label(
            body_frame,
            text="📝 Message:",
            font=self.fonts["heading"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            anchor="w",
        )
        body_label.pack(fill=tk.X, pady=(0, 5))

        # Body text với scrollbar
        body_text = scrolledtext.ScrolledText(
            body_frame,
            font=self.fonts["default"],
            bg="white",
            fg=self.colors["text_primary"],
            wrap=tk.WORD,
            relief=tk.FLAT,
            borderwidth=1,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=10,
            pady=10,
        )
        body_text.pack(fill=tk.BOTH, expand=True)
        body_text.insert("1.0", email.body)
        body_text.config(state=tk.DISABLED)  # Read-only

        # ====== ACTION BUTTONS ======
        actions_frame = tk.Frame(main_container, bg=self.colors["bg_primary"])
        actions_frame.pack(fill=tk.X)

        # Delete button
        delete_btn = tk.Button(
            actions_frame,
            text="🗑️  Delete",
            command=lambda e=email: self.delete_email(e, detail_window),
            font=self.fonts["bold"],
            bg=self.colors["error"],
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2",
        )
        delete_btn.pack(side=tk.LEFT, padx=5)

        # Reply button
        reply_btn = tk.Button(
            actions_frame,
            text="↩️  Reply",
            command=lambda e=email: self.reply_email(e, reply_all=False),
            font=self.fonts["bold"],
            bg=self.colors["accent_primary"],
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2",
        )
        reply_btn.pack(side=tk.LEFT, padx=5)

        # Reply All button
        reply_all_btn = tk.Button(
            actions_frame,
            text="↩️  Reply All",
            command=lambda e=email: self.reply_email(e, reply_all=True),
            font=self.fonts["bold"],
            bg=self.colors["accent_primary"],
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2",
        )
        reply_all_btn.pack(side=tk.LEFT, padx=5)

        # Forward button
        forward_btn = tk.Button(
            actions_frame,
            text="➡️  Forward",
            command=lambda e=email: self.forward_email(e),
            font=self.fonts["bold"],
            bg=self.colors["accent_secondary"],
            fg="white",
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2",
        )
        forward_btn.pack(side=tk.LEFT, padx=5)

        # Close button
        close_btn = tk.Button(
            actions_frame,
            text="❌ Close",
            command=detail_window.destroy,
            font=self.fonts["default"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2",
        )
        close_btn.pack(side=tk.RIGHT, padx=5)

    def _create_detail_row(self, parent, label_text, value_text):
        """Tạo một row trong detail view"""
        row = tk.Frame(parent, bg=self.colors["bg_secondary"])
        row.pack(fill=tk.X, padx=15, pady=3)

        label = tk.Label(
            row,
            text=label_text,
            font=self.fonts["bold"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            width=12,
            anchor="w",
        )
        label.pack(side=tk.LEFT)

        value = tk.Label(
            row,
            text=value_text,
            font=self.fonts["default"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_secondary"],
            anchor="w",
            wraplength=700,
            justify=tk.LEFT,
        )
        value.pack(side=tk.LEFT, fill=tk.X, expand=True)

        return row

    def open_attachment(self, email, attachment_name):
        """Mở attachment"""
        try:
            attachment_path = email.folder_path / attachment_name

            if not attachment_path.exists():
                messagebox.showerror(
                    "Error", f"Attachment not found: {attachment_name}"
                )
                return

            # Open with default application
            import subprocess
            import platform

            if platform.system() == "Windows":
                os.startfile(str(attachment_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", str(attachment_path)])
            else:  # Linux
                subprocess.call(["xdg-open", str(attachment_path)])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open attachment:\n{e}")
            traceback.print_exc()

    def delete_email(self, email, detail_window=None):
        """Xóa email"""
        if messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this email?\n\n{email.subject}",
        ):
            try:
                # Xóa thư mục email
                import shutil

                shutil.rmtree(email.folder_path)

                # Xóa tags
                if email.email_id in self.tags_manager.tags_data:
                    del self.tags_manager.tags_data[email.email_id]
                    self.tags_manager.save()

                # Reload
                self.load_emails()

                # Close detail window
                if detail_window:
                    detail_window.destroy()

                self.status_label.config(text="Email deleted")
                messagebox.showinfo("Success", "Email deleted successfully")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete email:\n{e}")
                traceback.print_exc()

    def reply_email(self, email, reply_all=False):
        """Reply to email"""
        self.compose_email(
            to=(
                email.from_addr
                if not reply_all
                else f"{email.from_addr}, {email.to_addr}"
            ),
            subject=f"Re: {email.subject}",
            body=f"\n\n--- Original Message ---\nFrom: {email.from_addr}\nDate: {email.date}\n\n{email.body}",
        )

    def forward_email(self, email):
        """Forward email"""
        self.compose_email(
            subject=f"Fwd: {email.subject}",
            body=f"\n\n--- Forwarded Message ---\nFrom: {email.from_addr}\nTo: {email.to_addr}\nDate: {email.date}\nSubject: {email.subject}\n\n{email.body}",
        )

    def compose_email(self, to="", subject="", body=""):
        """Mở compose window"""
        compose_window = tk.Toplevel(self.root)
        compose_window.title("✏️  Compose Email")
        compose_window.geometry("800x600")
        compose_window.configure(bg=self.colors["bg_primary"])

        # Make modal
        compose_window.transient(self.root)
        compose_window.grab_set()

        # Main container
        container = tk.Frame(compose_window, bg=self.colors["bg_primary"])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # To field
        to_frame = tk.Frame(container, bg=self.colors["bg_primary"])
        to_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            to_frame,
            text="To:",
            font=self.fonts["bold"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            width=10,
            anchor="w",
        ).pack(side=tk.LEFT)

        to_entry = tk.Entry(
            to_frame,
            font=self.fonts["default"],
            relief=tk.FLAT,
            borderwidth=1,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        to_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        to_entry.insert(0, to)

        # Subject field
        subject_frame = tk.Frame(container, bg=self.colors["bg_primary"])
        subject_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            subject_frame,
            text="Subject:",
            font=self.fonts["bold"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            width=10,
            anchor="w",
        ).pack(side=tk.LEFT)

        subject_entry = tk.Entry(
            subject_frame,
            font=self.fonts["default"],
            relief=tk.FLAT,
            borderwidth=1,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        subject_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        subject_entry.insert(0, subject)

        # Attachments
        attachments_frame = tk.Frame(container, bg=self.colors["bg_primary"])
        attachments_frame.pack(fill=tk.X, pady=5)

        tk.Label(
            attachments_frame,
            text="Attachments:",
            font=self.fonts["bold"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            width=10,
            anchor="w",
        ).pack(side=tk.LEFT)

        attachments_list = []
        attachments_label = tk.Label(
            attachments_frame,
            text="No attachments",
            font=self.fonts["small"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_secondary"],
            anchor="w",
        )
        attachments_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def add_attachment():
            files = filedialog.askopenfilenames(title="Select files to attach")
            if files:
                attachments_list.extend(files)
                attachments_label.config(
                    text=f"{len(attachments_list)} file(s): "
                    + ", ".join([os.path.basename(f) for f in attachments_list[:3]])
                    + ("..." if len(attachments_list) > 3 else "")
                )

        attach_btn = tk.Button(
            attachments_frame,
            text="📎 Add",
            command=add_attachment,
            font=self.fonts["small"],
            bg=self.colors["accent_primary"],
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=4,
        )
        attach_btn.pack(side=tk.RIGHT, padx=5)

        # Body
        body_label = tk.Label(
            container,
            text="Message:",
            font=self.fonts["bold"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            anchor="w",
        )
        body_label.pack(fill=tk.X, pady=(10, 5))

        body_text = scrolledtext.ScrolledText(
            container,
            font=self.fonts["default"],
            bg="white",
            fg=self.colors["text_primary"],
            wrap=tk.WORD,
            relief=tk.FLAT,
            borderwidth=1,
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=10,
            pady=10,
        )
        body_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        body_text.insert("1.0", body)

        # Buttons
        buttons_frame = tk.Frame(container, bg=self.colors["bg_primary"])
        buttons_frame.pack(fill=tk.X)

        def send_email():
            try:
                to_addr = to_entry.get().strip()
                subj = subject_entry.get().strip()
                msg_body = body_text.get("1.0", tk.END).strip()

                if not to_addr:
                    messagebox.showwarning("Warning", "Please enter recipient address")
                    return

                # Initialize backend if needed
                if not self.mail_client:
                    try:
                        self.mail_client = MailClient()
                    except Exception as e:
                        messagebox.showerror(
                            "Error", f"Failed to initialize mail client:\n{e}"
                        )
                        return

                # Send
                self.status_label.config(text="Sending email...")
                self.root.update()

                self.mail_client.send_email(
                    to_addr=to_addr,
                    subject=subj,
                    body=msg_body,
                    attachments=attachments_list if attachments_list else None,
                )

                self.status_label.config(text="Email sent successfully")
                messagebox.showinfo("Success", "Email sent successfully!")
                compose_window.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to send email:\n{e}")
                traceback.print_exc()
                self.status_label.config(text="Failed to send email")

        send_btn = tk.Button(
            buttons_frame,
            text="📤 Send",
            command=send_email,
            font=self.fonts["bold"],
            bg=self.colors["accent_primary"],
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
        )
        send_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = tk.Button(
            buttons_frame,
            text="❌ Cancel",
            command=compose_window.destroy,
            font=self.fonts["default"],
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)

    def fetch_emails(self):
        """Fetch new emails từ server"""

        def fetch_task():
            try:
                self.status_label.config(text="Fetching new emails...")
                self.root.update()

                if not self.mail_client:
                    self.mail_client = MailClient()

                new_count = self.mail_client.fetch_new_emails()

                # Update UI in main thread
                self.root.after(0, lambda: self._after_fetch(new_count))

            except Exception as e:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "Error", f"Failed to fetch emails:\n{e}"
                    ),
                )
                traceback.print_exc()

        # Run in background thread
        thread = threading.Thread(target=fetch_task, daemon=True)
        thread.start()

    def _after_fetch(self, new_count):
        """Called after fetch completes"""
        self.load_emails()
        self.status_label.config(text=f"Fetched {new_count} new email(s)")
        if new_count > 0:
            messagebox.showinfo("Success", f"Fetched {new_count} new email(s)!")

    # ============================================================
    # TAGS OPERATIONS
    # ============================================================

    def update_tags_list(self):
        """Cập nhật danh sách tags trong sidebar"""
        # Clear
        for widget in self.tags_container.winfo_children():
            widget.destroy()

        # Get all tags
        all_tags = self.tags_manager.get_all_tags()

        # Create button for each tag
        for tag in all_tags:
            tag_btn = tk.Button(
                self.tags_container,
                text=f"🏷️  {tag}",
                command=lambda t=tag: self.filter_by_tag(t),
                font=self.fonts["default"],
                bg=self.colors["bg_primary"],
                fg=self.colors["text_primary"],
                relief=tk.FLAT,
                anchor="w",
                padx=15,
                pady=6,
                cursor="hand2",
            )
            tag_btn.pack(fill=tk.X, padx=5, pady=2)
            self._apply_rounded_style(tag_btn)

            # Hover effect
            tag_btn.bind(
                "<Enter>", lambda e, btn=tag_btn: btn.config(bg=self.colors["bg_hover"])
            )
            tag_btn.bind(
                "<Leave>",
                lambda e, btn=tag_btn: btn.config(bg=self.colors["bg_primary"]),
            )

    def filter_by_tag(self, tag):
        """Lọc emails theo tag"""
        self.current_filter_tag = tag

        if tag is None:
            # Show all
            self.filtered_emails = self.emails.copy()
        else:
            # Filter by tag
            self.filtered_emails = [
                email
                for email in self.emails
                if tag in self.tags_manager.get_tags(email.email_id)
            ]

        self.display_emails()

        if tag:
            self.status_label.config(text=f"Filtered by tag: {tag}")
        else:
            self.status_label.config(text="Showing all emails")

    def add_tag_to_email(self, email, parent_window=None):
        """Thêm tag cho email"""
        # Input dialog
        tag_input = tk.simpledialog.askstring(
            "Add Tag", "Enter tag name:", parent=parent_window or self.root
        )

        if tag_input and tag_input.strip():
            tag = tag_input.strip()
            self.tags_manager.add_tag(email.email_id, tag)
            self.update_tags_list()
            self.load_emails()  # Reload to update display
            self.status_label.config(text=f"Added tag: {tag}")

            # Refresh detail window if open
            if parent_window:
                parent_window.destroy()
                self.show_email_detail(email)

    def remove_tag_from_email(self, email, tag, parent_window=None):
        """Xóa tag khỏi email"""
        self.tags_manager.remove_tag(email.email_id, tag)
        self.update_tags_list()
        self.load_emails()
        self.status_label.config(text=f"Removed tag: {tag}")

        # Refresh detail window
        if parent_window:
            parent_window.destroy()
            self.show_email_detail(email)

    # ============================================================
    # SETTINGS
    # ============================================================

    def open_settings(self):
        """Mở settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("⚙️  Settings")
        settings_window.geometry("500x400")
        settings_window.configure(bg=self.colors["bg_primary"])
        settings_window.transient(self.root)
        settings_window.grab_set()

        container = tk.Frame(settings_window, bg=self.colors["bg_primary"])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title = tk.Label(
            container,
            text="Settings",
            font=self.fonts["large"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            anchor="w",
        )
        title.pack(fill=tk.X, pady=(0, 20))

        # Font size
        font_frame = tk.Frame(container, bg=self.colors["bg_primary"])
        font_frame.pack(fill=tk.X, pady=10)

        tk.Label(
            font_frame,
            text="Font Size:",
            font=self.fonts["bold"],
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            width=15,
            anchor="w",
        ).pack(side=tk.LEFT)

        font_size_var = tk.IntVar(value=self.config["font_size"])
        font_spinbox = tk.Spinbox(
            font_frame,
            from_=8,
            to=16,
            textvariable=font_size_var,
            font=self.fonts["default"],
            width=10,
        )
        font_spinbox.pack(side=tk.LEFT, padx=10)

        # Save button
        def save_settings():
            self.config["font_size"] = font_size_var.get()
            ConfigManager.save(self.config)
            messagebox.showinfo(
                "Success", "Settings saved!\nRestart the app to apply changes."
            )
            settings_window.destroy()

        save_btn = tk.Button(
            container,
            text="💾 Save",
            command=save_settings,
            font=self.fonts["bold"],
            bg=self.colors["accent_primary"],
            fg="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8,
        )
        save_btn.pack(side=tk.BOTTOM, pady=10)


# ============================================================
# MAIN ENTRY POINT
# ============================================================
def main():
    """Main entry point"""
    try:
        # Check backend
        if not BACKEND_AVAILABLE:
            print("❌ Backend mail_client.py not found!")
            print("   Please ensure mail_client.py is in the same directory")
            return

        # Create root window
        root = tk.Tk()

        # Create app
        app = MailClientGUI(root)

        # Run
        root.mainloop()

    except Exception as e:
        print("=" * 70)
        print("❌ FATAL ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        print("\nTraceback:")
        traceback.print_exc()
        print("=" * 70)


if __name__ == "__main__":
    main()
