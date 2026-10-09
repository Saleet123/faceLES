#!/usr/bin/env python3
"""FaceLES employee monitor — Ubuntu / Linux entry point."""
import json
import os
import tkinter as tk
from tkinter import ttk
import atexit
import numpy as np
from PIL import Image, ImageTk, ImageDraw
from datetime import datetime, timedelta
import threading
import time
import cv2
import csv
import socket
import platform
import getpass
import urllib.request
import sys

# Ensure relative assets resolve from the script directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)

CRASH_FLAG_FILE = "crash_flag.tmp"
MODEL_FILE = "lbph_model.yml"
LABEL_MAP_FILE = "label_map.txt"
CASCADE_FILE = "haarcascade_frontalface_default.xml"

# Globals
last_user_input_time = time.time()
last_person_seen_time = time.time()
login_time = None
total_break_time = timedelta()
break_start_time = None
break_window = None
manual_break_type = None
preview_cap = None

is_user_visible = True
break_triggered = False
break_reason = None
break_log_entries = []
video_label = None
video_stream_active = False
internet_was_connected = True
last_break_end_time = None
BREAK_COOLDOWN_SECONDS = 60  # Cooldown to prevent immediate re-trigger

INACTIVITY_THRESHOLD = 5 * 60  # 5 minutes of idle / absence before auto-break
VALID_USERNAME = "saleet"
VALID_PASSWORD = "123"
MANUAL_BREAK_OPTIONS = ["Meeting", "Lunch", "Prayer", "Tea", "Call"]

# Brand blue used across login, biometric, and dashboard
BRAND_BLUE = "#3774B8"
BRAND_BLUE_HOVER = "#2d5f96"
BRAND_BLUE_DEEP = "#2b5c94"  # pressed / darker companion

# Login / dashboard palette
UI = {
    "bg": "#ffffff",
    "panel": BRAND_BLUE,
    "panel_mid": BRAND_BLUE_HOVER,
    "accent": BRAND_BLUE,
    "accent_hover": BRAND_BLUE_HOVER,
    "text": "#1c2b30",
    "muted": "#5a6d74",
    "field_bg": "#ffffff",
    "field_border": "#e5eaf0",
    "camera_bg": "#0a1f24",
}

# Biometric modal (FaceGate-style enrollment / login)
BIO = {
    "scrim": "#1a1b1e",
    "card": "#2a2b2f",
    "text": "#f2f2f4",
    "muted": "#9a9ba1",
    "warn": "#e85d5d",
    "ok": "#5dcf7a",
    "accent": BRAND_BLUE,
    "accent_hover": BRAND_BLUE_HOVER,
    "track": "#3a3b40",
    "preview": "#111214",
}
ENROLL_TARGET = 9
BIO_PREVIEW_W = 420
BIO_PREVIEW_H = 280


class EmployeeMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.title("FaceLES")
        self.root.geometry("920x560")
        self.root.configure(bg=UI["bg"])
        self.root.resizable(False, False)

        self.shift_values = {}
        self.inactivity_log = None
        self.video_label = None
        self._login_shell = None
        self._bio = None  # active biometric modal state

        self._configure_styles()
        self.setup_login_screen()
        self.bind_activity_events()

        try:
            with open(CRASH_FLAG_FILE, "w") as f:
                f.write("crash marker")
        except OSError:
            pass

    def _configure_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Primary.TButton",
            font=("Ubuntu", 12, "bold"),
            background=UI["accent"],
            foreground="#ffffff",
            borderwidth=0,
            focuscolor=UI["accent"],
            padding=(18, 10),
        )
        style.map(
            "Primary.TButton",
            background=[("active", UI["accent_hover"]), ("pressed", UI["panel"])],
            foreground=[("disabled", "#d0d0d0")],
        )
        style.configure(
            "Ghost.TButton",
            font=("Ubuntu", 11),
            background=UI["bg"],
            foreground=UI["panel"],
            borderwidth=1,
            padding=(14, 9),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#d5dee2")],
            foreground=[("active", UI["panel"])],
        )

    def _make_field(self, parent, show=None):
        wrap = tk.Frame(parent, bg=UI["field_border"], bd=0)
        entry = tk.Entry(
            wrap,
            font=("Ubuntu", 13),
            bg=UI["field_bg"],
            fg=UI["text"],
            relief="flat",
            insertbackground=UI["text"],
            highlightthickness=0,
            bd=0,
            show=show or "",
        )
        entry.pack(fill="x", ipady=9, ipadx=10, padx=1, pady=1)

        def on_focus_in(_e):
            wrap.configure(bg="#b8cce3")

        def on_focus_out(_e):
            wrap.configure(bg=UI["field_border"])

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        return wrap, entry

    def setup_login_screen(self):
        shell = tk.Frame(self.root, bg=UI["bg"])
        shell.pack(fill="both", expand=True)
        self._login_shell = shell

        # Brand column
        brand = tk.Frame(shell, bg=UI["panel"], width=340)
        brand.pack(side="left", fill="y")
        brand.pack_propagate(False)

        brand_inner = tk.Frame(brand, bg=UI["panel"])
        brand_inner.place(relx=0.5, rely=0.42, anchor="center")

        tk.Label(
            brand_inner,
            text="FaceLES",
            bg=UI["panel"],
            fg="#ffffff",
            font=("Ubuntu", 36, "bold"),
        ).pack()
        tk.Label(
            brand_inner,
            text="Face login & attendance",
            bg=UI["panel"],
            fg="#d7e6f6",
            font=("Ubuntu", 12),
        ).pack(pady=(6, 28))

        accent_bar = tk.Frame(brand_inner, bg="#ffffff", height=3, width=72)
        accent_bar.pack()

        tk.Label(
            brand,
            text="Position your face in the\ncamera before signing in",
            bg=UI["panel"],
            fg="#e3eef9",
            font=("Ubuntu", 10),
            justify="center",
        ).place(relx=0.5, rely=0.88, anchor="center")

        # Form column
        form_col = tk.Frame(shell, bg=UI["bg"])
        form_col.pack(side="left", fill="both", expand=True)

        form = tk.Frame(form_col, bg=UI["bg"])
        form.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            form,
            text="Sign in",
            bg=UI["bg"],
            fg=UI["text"],
            font=("Ubuntu", 22, "bold"),
        ).pack(anchor="w")
        tk.Label(
            form,
            text="Use your work credentials and face check.",
            bg=UI["bg"],
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(anchor="w", pady=(4, 18))

        tk.Label(
            form,
            text="Official email / username",
            bg=UI["bg"],
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(anchor="w")
        user_wrap, self.username_entry = self._make_field(form)
        user_wrap.pack(fill="x", pady=(4, 12))

        tk.Label(
            form,
            text="Password",
            bg=UI["bg"],
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(anchor="w")
        pass_wrap, self.password_entry = self._make_field(form, show="*")
        pass_wrap.pack(fill="x", pady=(4, 16))

        actions = tk.Frame(form, bg=UI["bg"])
        actions.pack(fill="x")
        self.login_button = tk.Button(
            actions,
            text="Sign in",
            font=("Ubuntu", 12, "bold"),
            bg=UI["accent"],
            fg="#ffffff",
            activebackground=UI["accent_hover"],
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=22,
            pady=10,
            cursor="hand2",
            command=self.show_login_time,
        )
        self.login_button.pack(side="left")
        self.biometric_button = tk.Button(
            actions,
            text="Biometric login",
            font=("Ubuntu", 11, "bold"),
            bg=BRAND_BLUE_DEEP,
            fg="#ffffff",
            activebackground=BRAND_BLUE_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=14,
            pady=10,
            cursor="hand2",
            command=self.start_biometric_login,
        )
        self.biometric_button.pack(side="left", padx=(10, 0))
        self.register_button = tk.Button(
            actions,
            text="Register face",
            font=("Ubuntu", 11),
            bg="#ffffff",
            fg=BRAND_BLUE,
            activebackground="#eaf1f9",
            activeforeground=BRAND_BLUE,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=UI["field_border"],
            highlightcolor=UI["field_border"],
            padx=14,
            pady=9,
            cursor="hand2",
            command=self.capture_and_train_face,
        )
        self.register_button.pack(side="left", padx=(10, 0))

        # Camera preview
        cam_block = tk.Frame(form, bg=UI["bg"])
        cam_block.pack(fill="x", pady=(22, 0))

        tk.Label(
            cam_block,
            text="Live camera",
            bg=UI["bg"],
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(anchor="w", pady=(0, 6))

        cam_frame = tk.Frame(cam_block, bg=UI["field_border"], bd=0, padx=1, pady=1)
        cam_frame.pack(anchor="w")

        self.video_label = tk.Label(
            cam_frame,
            bg=UI["camera_bg"],
            width=42,
            height=12,
            text="Starting camera…",
            fg="#6a8a90",
            font=("Ubuntu", 10),
            compound="center",
            highlightthickness=0,
        )
        self.video_label.pack()

        self.username_entry.focus_set()
        self.root.bind("<Return>", lambda _e: self.show_login_time())
        self.start_camera_preview()

    def bind_activity_events(self):
        self.root.bind_all("<Motion>", self.update_activity)
        self.root.bind_all("<Button>", self.update_activity)
        self.root.bind_all("<KeyPress>", self.update_activity)

    def update_activity(self, event=None):
        global last_user_input_time
        last_user_input_time = time.time()
        # Moving / typing during countdown cancels the pending auto-break
        if getattr(self, "_countdown_active", False):
            self.root.after(0, self._cancel_break_countdown)

    def on_close(self):
        def do_logout():
            self.save_shift_data_to_json()
            self.root.destroy()

        self._ui_confirm(
            "Logout",
            "Are you sure you want to log out? Your shift data will be saved.",
            confirm_text="Logout",
            on_confirm=do_logout,
            danger=True,
        )

    def check_internet(self):
        global internet_was_connected
        while True:
            try:
                urllib.request.urlopen('http://clients3.google.com/generate_204', timeout=5)
                internet_was_connected = True
            except:
                if internet_was_connected:
                    internet_was_connected = False
                    self.root.after(0, self.log_crash_break)
            time.sleep(10)

    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.abspath(relative_path)

    def log_crash_break(self):
        global login_time, break_log_entries, total_break_time
        if login_time:
            now = datetime.now()
            duration = timedelta(seconds=1)
            total_break_time += duration
            log_entry = [
                now.strftime('%I:%M:%S %p'),
                now.strftime('%I:%M:%S %p'),
                str(duration),
                "Crash"
            ]
            if not break_log_entries or break_log_entries[-1][3] != "Crash":
                break_log_entries.append(log_entry)
                self.log_break(log_entry[0], log_entry[1], f"{log_entry[2]} (Crash)")

    def open_camera(self, index=0):
        """Open webcam with V4L2 first, then default backend fallback."""
        for backend in (cv2.CAP_V4L2, cv2.CAP_ANY):
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                return cap
            cap.release()
        return None

    def start_camera_preview(self):
        global video_stream_active, preview_cap
        video_stream_active = True
        preview_cap = self.open_camera(0)

        if preview_cap is None or not preview_cap.isOpened():
            if self.video_label is not None:
                self.video_label.configure(
                    image="",
                    text="Camera unavailable",
                    fg="#c98989",
                )
            print("Camera could not be opened")
            return

        def update_frame():
            if not video_stream_active or self.video_label is None:
                if preview_cap is not None:
                    preview_cap.release()
                return
            ret, frame = preview_cap.read()
            if ret:
                frame = cv2.resize(frame, (360, 220))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = ImageTk.PhotoImage(Image.fromarray(frame))
                self.video_label.configure(image=img, text="")
                self.video_label.image = img
            self.video_label.after(30, update_frame)

        update_frame()

    def stop_camera_preview(self):
        global video_stream_active, preview_cap
        video_stream_active = False
        if preview_cap is not None:
            preview_cap.release()
            preview_cap = None

    def start_face_recognition_monitoring(self):
        global last_person_seen_time, is_user_visible
        self._face_monitor_alive = False

        if not os.path.exists(MODEL_FILE):
            print("No face model — presence monitoring disabled.")
            return

        face_cascade = cv2.CascadeClassifier(self.resource_path(CASCADE_FILE))
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(MODEL_FILE)

        label_map = {}
        if os.path.exists(LABEL_MAP_FILE):
            with open(LABEL_MAP_FILE, "r") as f:
                for line in f:
                    parts = line.strip().split(":")
                    if len(parts) == 2:
                        label_map[int(parts[0])] = parts[1]

        cap = self.open_camera(0)
        if cap is None or not cap.isOpened():
            print("No camera — presence monitoring disabled.")
            return

        self._face_monitor_alive = True
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.5)
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)

                recognized = False
                for (x, y, w, h) in faces:
                    id_, confidence = recognizer.predict(gray[y:y + h, x:x + w])
                    name = label_map.get(id_, "Unknown")
                    print(f"Detected: {name}, Confidence: {confidence}")
                    if confidence < 48:
                        recognized = True
                        break

                is_user_visible = recognized
                if recognized:
                    last_person_seen_time = time.time()

                time.sleep(1)
        finally:
            self._face_monitor_alive = False
            try:
                cap.release()
            except Exception:
                pass

    def monitor_idle_state(self):
        def idle_check():
            global break_start_time, break_triggered, break_reason, last_break_end_time
            while True:
                now = time.time()
                no_user_input = now - last_user_input_time > INACTIVITY_THRESHOLD
                face_ok = getattr(self, "_face_monitor_alive", False)
                # Absence only counts when camera + face model are actually running
                user_absent = face_ok and (now - last_person_seen_time > INACTIVITY_THRESHOLD)
                cooldown_elapsed = True
                if last_break_end_time:
                    cooldown_elapsed = now - last_break_end_time > BREAK_COOLDOWN_SECONDS

                # Mouse/keyboard activity always wins — do not start break while active
                if not no_user_input:
                    if getattr(self, "_countdown_active", False):
                        self.root.after(0, self._cancel_break_countdown)
                    time.sleep(1)
                    continue

                should_break = no_user_input or user_absent
                if should_break and not break_triggered and cooldown_elapsed:
                    if no_user_input and user_absent:
                        break_reason = "Inactivity + Absence"
                    elif no_user_input:
                        break_reason = "Inactivity Only"
                    else:
                        break_reason = "Absence Only"
                    break_start_time = datetime.now() - timedelta(
                        seconds=now - last_user_input_time
                    )
                    break_triggered = True
                    self.root.after(0, lambda: self.show_break_countdown(10))

                if (
                    break_triggered
                    and not getattr(self, "_countdown_active", False)
                    and not no_user_input
                    and break_window is not None
                ):
                    # User returned during an active auto-break UI
                    pass
                time.sleep(1)

        threading.Thread(target=idle_check, daemon=True).start()

    def show_break_alert_auto(self):
        global break_window
        overlay = tk.Frame(self.root, bg="#0f1720")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        break_window = overlay

        card = tk.Frame(overlay, bg="#ffffff", padx=32, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        display_reason = "Idle Sitting" if break_reason == "Inactivity Only" else (break_reason or "Auto")
        tk.Label(
            card,
            text="Auto break",
            bg="#ffffff",
            fg=UI["text"],
            font=("Ubuntu", 18, "bold"),
        ).pack()
        tk.Label(
            card,
            text=display_reason,
            bg="#ffffff",
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(pady=(4, 12))

        time_label = tk.Label(
            card,
            text="00:00:00",
            bg="#ffffff",
            fg=BRAND_BLUE,
            font=("Ubuntu", 32, "bold"),
        )
        time_label.pack(pady=(4, 18))

        def update_time_label():
            if break_start_time and break_window is not None:
                try:
                    elapsed = datetime.now() - break_start_time
                    time_label.config(text=str(elapsed).split(".")[0])
                    time_label.after(1000, update_time_label)
                except tk.TclError:
                    pass

        def manual_end_auto_break():
            global total_break_time, break_start_time, break_window, break_triggered
            global last_break_end_time, last_user_input_time, last_person_seen_time
            if break_start_time:
                break_end_time = datetime.now()
                break_duration = break_end_time - break_start_time
                total_break_time += break_duration
                log_entry = [
                    break_start_time.strftime("%I:%M:%S %p"),
                    break_end_time.strftime("%I:%M:%S %p"),
                    str(break_duration),
                    break_reason or "Auto",
                ]
                break_log_entries.append(log_entry)
                reason = "Idle Sitting" if break_reason == "Inactivity Only" else break_reason
                self.log_break(log_entry[0], log_entry[1], f"{log_entry[2]} ({reason})")
                break_start_time = None
                last_break_end_time = time.time()

            try:
                overlay.destroy()
            except tk.TclError:
                pass
            break_window = None
            break_triggered = False
            last_user_input_time = time.time()
            last_person_seen_time = time.time()
            self.update_shift_stats()

        update_time_label()
        tk.Button(
            card,
            text="End break",
            font=("Ubuntu", 12, "bold"),
            bg=BRAND_BLUE,
            fg="#ffffff",
            activebackground=BRAND_BLUE_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=22,
            pady=10,
            cursor="hand2",
            command=manual_end_auto_break,
        ).pack()

    def auto_start_break(self):
        global break_start_time, break_triggered
        self._countdown_active = False
        self._countdown_overlay = None
        if not break_start_time:
            inactivity_elapsed = time.time() - last_user_input_time
            break_start_time = datetime.now() - timedelta(seconds=inactivity_elapsed)
        break_triggered = True
        self.show_break_alert_auto()
        display_reason = "Idle Sitting" if break_reason == "Inactivity Only" else break_reason
        self.log_break("AUTO", "Break started", f"0:00:00.00 ({display_reason})")
        self.update_shift_stats()

    def auto_end_break(self):
        global break_start_time, total_break_time, break_reason, last_break_end_time, break_triggered
        if break_start_time:
            break_end_time = datetime.now()
            break_duration = break_end_time - break_start_time
            total_break_time += break_duration
            log_entry = [
                break_start_time.strftime("%I:%M:%S %p"),
                break_end_time.strftime("%I:%M:%S %p"),
                str(break_duration),
                break_reason,
            ]
            break_log_entries.append(log_entry)
            display_reason = "Idle Sitting" if break_reason == "Inactivity Only" else break_reason
            self.log_break(log_entry[0], log_entry[1], f"{log_entry[2]} (Auto: {display_reason})")
            break_start_time = None
            last_break_end_time = time.time()
            break_reason = None
            break_triggered = False
            self.update_shift_stats()

    def _cancel_break_countdown(self):
        global break_triggered, break_start_time, last_user_input_time, last_person_seen_time
        if not getattr(self, "_countdown_active", False):
            return
        self._countdown_active = False
        overlay = getattr(self, "_countdown_overlay", None)
        self._countdown_overlay = None
        break_triggered = False
        break_start_time = None
        last_user_input_time = time.time()
        last_person_seen_time = time.time()
        if overlay is not None:
            try:
                overlay.destroy()
            except tk.TclError:
                pass

    def show_break_countdown(self, seconds=10):
        if getattr(self, "_countdown_active", False):
            return
        self._countdown_active = True

        overlay = tk.Frame(self.root, bg="#0f1720")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._countdown_overlay = overlay

        card = tk.Frame(overlay, bg="#ffffff", padx=32, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="Idle detected",
            bg="#ffffff",
            fg=UI["text"],
            font=("Ubuntu", 18, "bold"),
        ).pack()
        tk.Label(
            card,
            text="Move the mouse or press a key to cancel.",
            bg="#ffffff",
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(pady=(4, 12))

        timer_label = tk.Label(
            card,
            text=f"{seconds}s",
            bg="#ffffff",
            fg=BRAND_BLUE,
            font=("Ubuntu", 36, "bold"),
        )
        timer_label.pack(pady=(4, 16))

        tk.Button(
            card,
            text="I'm here — cancel",
            font=("Ubuntu", 11, "bold"),
            bg=BRAND_BLUE,
            fg="#ffffff",
            activebackground=BRAND_BLUE_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
            command=self._cancel_break_countdown,
        ).pack()

        def countdown(count):
            if not getattr(self, "_countdown_active", False):
                return
            if count > 0:
                try:
                    timer_label.config(text=f"{count}s")
                except tk.TclError:
                    return
                self.root.after(1000, countdown, count - 1)
            else:
                self._countdown_active = False
                try:
                    overlay.destroy()
                except tk.TclError:
                    pass
                self._countdown_overlay = None
                self.auto_start_break()

        countdown(seconds)

    def start_manual_break(self):
        global break_start_time, manual_break_type, break_reason
        if break_start_time:
            self._ui_alert("Break active", "A break is already in progress.")
            return

        selected = {"value": None}
        option_widgets = []

        overlay = tk.Frame(self.root, bg="#1a1b1e")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        # soft dim without blocking paint of card
        overlay.configure(bg="#0f1720")

        card = tk.Frame(overlay, bg="#ffffff", padx=28, pady=24)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="Start a break",
            bg="#ffffff",
            fg=UI["text"],
            font=("Ubuntu", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            card,
            text="Choose why you’re stepping away.",
            bg="#ffffff",
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(anchor="w", pady=(4, 16))

        list_wrap = tk.Frame(card, bg="#ffffff")
        list_wrap.pack(fill="x")

        def paint_options():
            for name, widgets in option_widgets:
                active = selected["value"] == name
                bg = "#eaf1f9" if active else "#f4f6f8"
                for w in widgets[:-2]:
                    w.configure(bg=bg)
                dot, label = widgets[-2], widgets[-1]
                dot.configure(
                    bg=bg,
                    fg=BRAND_BLUE if active else "#c5ced8",
                    text="●" if active else "○",
                )
                label.configure(
                    bg=bg,
                    fg=BRAND_BLUE if active else UI["text"],
                    font=("Ubuntu", 12, "bold" if active else "normal"),
                )

        def choose(name):
            selected["value"] = name
            paint_options()

        for option in MANUAL_BREAK_OPTIONS:
            row = tk.Frame(list_wrap, bg="#f4f6f8", cursor="hand2")
            row.pack(fill="x", pady=4)
            inner = tk.Frame(row, bg="#f4f6f8")
            inner.pack(fill="x", padx=14, pady=12)
            dot = tk.Label(inner, text="○", bg="#f4f6f8", fg="#c5ced8", font=("Ubuntu", 12))
            dot.pack(side="left")
            label = tk.Label(inner, text=option, bg="#f4f6f8", fg=UI["text"], font=("Ubuntu", 12))
            label.pack(side="left", padx=(10, 0))
            widgets = (row, inner, dot, label)
            option_widgets.append((option, widgets))
            for w in widgets:
                w.bind("<Button-1>", lambda _e, n=option: choose(n))

        actions = tk.Frame(card, bg="#ffffff")
        actions.pack(fill="x", pady=(18, 0))

        def close_picker():
            overlay.destroy()

        def start_selected_break():
            global break_reason, manual_break_type
            if not selected["value"]:
                self._ui_alert("Select break", "Please choose a break type.")
                return
            break_reason = selected["value"]
            manual_break_type = selected["value"]
            close_picker()
            self.begin_manual_break()

        tk.Button(
            actions,
            text="Cancel",
            font=("Ubuntu", 11),
            bg="#ffffff",
            fg=UI["muted"],
            activebackground="#f0f2f5",
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2",
            command=close_picker,
        ).pack(side="left")

        tk.Button(
            actions,
            text="Start break",
            font=("Ubuntu", 11, "bold"),
            bg=BRAND_BLUE,
            fg="#ffffff",
            activebackground=BRAND_BLUE_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
            command=start_selected_break,
        ).pack(side="right")

        # default first option selected
        choose(MANUAL_BREAK_OPTIONS[0])

    def begin_manual_break(self):
        global break_start_time, manual_break_type, break_window
        break_start_time = datetime.now()

        overlay = tk.Frame(self.root, bg="#0f1720")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        break_window = overlay

        card = tk.Frame(overlay, bg="#ffffff", padx=32, pady=28)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text=f"{manual_break_type} break",
            bg="#ffffff",
            fg=UI["text"],
            font=("Ubuntu", 18, "bold"),
        ).pack()
        tk.Label(
            card,
            text="Timer is running — return when you’re back.",
            bg="#ffffff",
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(pady=(4, 16))

        time_label = tk.Label(
            card,
            text="00:00:00",
            bg="#ffffff",
            fg=BRAND_BLUE,
            font=("Ubuntu", 32, "bold"),
        )
        time_label.pack(pady=(4, 20))

        def update_time():
            if break_start_time and break_window is not None:
                try:
                    elapsed = datetime.now() - break_start_time
                    time_label.config(text=str(elapsed).split(".")[0])
                    time_label.after(1000, update_time)
                except tk.TclError:
                    pass

        update_time()

        def end_manual_break():
            global total_break_time, break_start_time, break_window
            if break_start_time:
                break_end_time = datetime.now()
                break_duration = break_end_time - break_start_time
                total_break_time += break_duration
                log_entry = [
                    break_start_time.strftime("%I:%M:%S %p"),
                    break_end_time.strftime("%I:%M:%S %p"),
                    str(break_duration),
                    manual_break_type,
                ]
                break_log_entries.append(log_entry)
                self.log_break(log_entry[0], log_entry[1], f"{log_entry[2]} ({manual_break_type})")
                break_start_time = None
            global last_user_input_time, last_person_seen_time
            last_user_input_time = time.time()
            last_person_seen_time = time.time()
            try:
                overlay.destroy()
            except tk.TclError:
                pass
            break_window = None
            self.update_shift_stats()

        tk.Button(
            card,
            text="End break",
            font=("Ubuntu", 12, "bold"),
            bg=BRAND_BLUE,
            fg="#ffffff",
            activebackground=BRAND_BLUE_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=22,
            pady=10,
            cursor="hand2",
            command=end_manual_break,
        ).pack()

    def log_break(self, start_time, end_time, duration):
        try:
            # If duration is like '0:00:05.227240 (Reason)', round the seconds
            parts = duration.split(" ")
            time_part = parts[0]
            reason_part = " ".join(parts[1:]) if len(parts) > 1 else ""
            h, m, s = map(float, time_part.split(":"))
            rounded_duration = f"{int(h):02}:{int(m):02}:{s:.2f}"
            display_duration = f"{rounded_duration} {reason_part}".strip()
            self.inactivity_log.insert(tk.END, f"{start_time} to {end_time} --- {display_duration}\n")
        except Exception as e:
            self.inactivity_log.insert(tk.END, f"{start_time} to {end_time} --- {duration} (Error rounding: {e})\n")
        self.inactivity_log.yview(tk.END)

    def update_shift_stats(self):
        if not login_time or not self.shift_values:
            return
        current_time = datetime.now()
        login_duration = current_time - login_time
        work_duration = login_duration - total_break_time
        mapping = {
            "Shift Login Duration": str(login_duration).split(".")[0],
            "Shift Breaks Duration": str(total_break_time).split(".")[0],
            "Shift Total Work Duration": str(work_duration).split(".")[0],
        }
        for key, text in mapping.items():
            label = self.shift_values.get(key)
            if label is not None:
                label.config(text=text)

    def save_shift_data_to_json(self):
        if not login_time:
            return

        session_date = login_time.strftime('%Y-%m-%d')
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        system_user = getpass.getuser()
        device_os = platform.system()

        new_session = {
            "login_time": login_time.strftime('%I:%M:%S %p'),
            "logout_time": datetime.now().strftime('%I:%M:%S %p'),
            "login_duration": str(datetime.now() - login_time),
            "work_duration": str(datetime.now() - login_time - total_break_time),
            "total_break_time": str(total_break_time),
            "breaks": break_log_entries,
            "ip_address": ip_address,
            "hostname": hostname,
            "user": system_user,
            "platform": device_os
        }

        os.makedirs("attendance_logs", exist_ok=True)
        filename = os.path.join("attendance_logs", f"{session_date}.json")

        existing_data = {"date": session_date, "sessions": []}
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                try:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        existing_data.update(loaded_data)
                        if "sessions" not in existing_data:
                            existing_data["sessions"] = []
                except json.JSONDecodeError:
                    pass  # Handle corrupted file by starting fresh
        else:
            existing_data = {"date": session_date, "sessions": []}

        existing_data["sessions"].append(new_session)

        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=4)

    def _ui_modal_shell(self):
        """Shared FaceLES overlay + white card shell."""
        overlay = tk.Frame(self.root, bg="#0f1720")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        card = tk.Frame(overlay, bg="#ffffff", padx=28, pady=24)
        card.place(relx=0.5, rely=0.5, anchor="center")
        return overlay, card

    def _ui_alert(self, title, message, kind="info"):
        overlay, card = self._ui_modal_shell()
        accent = BRAND_BLUE if kind != "error" else "#c45c5c"
        hover = BRAND_BLUE_HOVER if kind != "error" else "#a84848"
        tk.Label(card, text=title, bg="#ffffff", fg=UI["text"], font=("Ubuntu", 16, "bold")).pack(anchor="w")
        tk.Label(
            card,
            text=message,
            bg="#ffffff",
            fg=UI["muted"],
            font=("Ubuntu", 11),
            wraplength=360,
            justify="left",
        ).pack(anchor="w", pady=(8, 18))
        tk.Button(
            card,
            text="OK",
            font=("Ubuntu", 11, "bold"),
            bg=accent,
            fg="#ffffff",
            activebackground=hover,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
            cursor="hand2",
            command=overlay.destroy,
        ).pack(anchor="e")

    def _ui_confirm(self, title, message, confirm_text="Confirm", on_confirm=None, danger=False):
        overlay, card = self._ui_modal_shell()
        accent = "#c45c5c" if danger else BRAND_BLUE
        hover = "#a84848" if danger else BRAND_BLUE_HOVER
        tk.Label(card, text=title, bg="#ffffff", fg=UI["text"], font=("Ubuntu", 18, "bold")).pack(anchor="w")
        tk.Label(
            card,
            text=message,
            bg="#ffffff",
            fg=UI["muted"],
            font=("Ubuntu", 11),
            wraplength=380,
            justify="left",
        ).pack(anchor="w", pady=(6, 20))

        actions = tk.Frame(card, bg="#ffffff")
        actions.pack(fill="x")

        def close():
            overlay.destroy()

        def confirm():
            close()
            if on_confirm:
                on_confirm()

        tk.Button(
            actions,
            text="Cancel",
            font=("Ubuntu", 11),
            bg="#ffffff",
            fg=UI["muted"],
            activebackground="#f0f2f5",
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2",
            command=close,
        ).pack(side="left")
        tk.Button(
            actions,
            text=confirm_text,
            font=("Ubuntu", 11, "bold"),
            bg=accent,
            fg="#ffffff",
            activebackground=hover,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
            command=confirm,
        ).pack(side="right")

    def export_log_to_csv(self):
        if not break_log_entries:
            self._ui_alert("Export", "No break logs to export yet.", kind="info")
            return

        overlay, card = self._ui_modal_shell()
        default_name = f"breaks_{datetime.now().strftime('%Y-%m-%d')}.csv"
        export_dir = os.path.abspath("attendance_logs")
        os.makedirs(export_dir, exist_ok=True)

        tk.Label(card, text="Export CSV", bg="#ffffff", fg=UI["text"], font=("Ubuntu", 18, "bold")).pack(anchor="w")
        tk.Label(
            card,
            text="Save today’s break log as a CSV file.",
            bg="#ffffff",
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(anchor="w", pady=(4, 16))

        tk.Label(card, text="File name", bg="#ffffff", fg=UI["muted"], font=("Ubuntu", 10)).pack(anchor="w")
        name_wrap = tk.Frame(card, bg=UI["field_border"], bd=0)
        name_wrap.pack(fill="x", pady=(4, 12))
        name_entry = tk.Entry(
            name_wrap,
            font=("Ubuntu", 12),
            bg="#ffffff",
            fg=UI["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        name_entry.insert(0, default_name)
        name_entry.pack(fill="x", ipady=8, ipadx=10, padx=1, pady=1)

        tk.Label(card, text="Save to", bg="#ffffff", fg=UI["muted"], font=("Ubuntu", 10)).pack(anchor="w")
        tk.Label(
            card,
            text=export_dir,
            bg="#f7f9fc",
            fg=UI["text"],
            font=("Ubuntu", 10),
            anchor="w",
            padx=10,
            pady=8,
        ).pack(fill="x", pady=(4, 18))

        actions = tk.Frame(card, bg="#ffffff")
        actions.pack(fill="x")

        def close():
            overlay.destroy()

        def do_export():
            name = name_entry.get().strip() or default_name
            if not name.lower().endswith(".csv"):
                name += ".csv"
            # keep filename only — no path traversal
            name = os.path.basename(name)
            file_path = os.path.join(export_dir, name)
            try:
                with open(file_path, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Start Time", "End Time", "Duration", "Reason"])
                    writer.writerows(break_log_entries)
            except OSError as e:
                close()
                self._ui_alert("Export failed", str(e), kind="error")
                return
            close()
            self._ui_alert("Exported", f"Break log saved to\n{file_path}", kind="info")

        tk.Button(
            actions,
            text="Cancel",
            font=("Ubuntu", 11),
            bg="#ffffff",
            fg=UI["muted"],
            activebackground="#f0f2f5",
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2",
            command=close,
        ).pack(side="left")
        tk.Button(
            actions,
            text="Export",
            font=("Ubuntu", 11, "bold"),
            bg=BRAND_BLUE,
            fg="#ffffff",
            activebackground=BRAND_BLUE_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
            command=do_export,
        ).pack(side="right")
        name_entry.focus_set()

    def show_summary(self):
        total_breaks = len(break_log_entries)
        total_break_minutes = 0.0
        for _, _, timedelta_str, _ in break_log_entries:
            try:
                parts = timedelta_str.split(":")
                if len(parts) >= 3:
                    total_break_minutes += float(parts[1]) + float(parts[2]) / 60
            except (ValueError, IndexError):
                pass

        reasons = {
            "Inactivity Only": 0,
            "Absence Only": 0,
            "Inactivity + Absence": 0,
            "Meeting": 0,
            "Lunch": 0,
            "Prayer": 0,
            "Tea": 0,
            "Call": 0,
            "Crash": 0,
        }
        for entry in break_log_entries:
            reason = entry[3] if len(entry) > 3 else "Other"
            if reason in reasons:
                reasons[reason] += 1
            elif reason == "Idle Sitting":
                reasons["Inactivity Only"] += 1

        overlay, card = self._ui_modal_shell()
        tk.Label(card, text="Daily summary", bg="#ffffff", fg=UI["text"], font=("Ubuntu", 18, "bold")).pack(anchor="w")
        tk.Label(
            card,
            text="Break activity for this shift.",
            bg="#ffffff",
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(anchor="w", pady=(4, 16))

        stats = tk.Frame(card, bg="#ffffff")
        stats.pack(fill="x")

        def metric(parent, label, value, col):
            tile = tk.Frame(parent, bg="#f7f9fc", padx=14, pady=12)
            tile.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
            tk.Label(tile, text=label, bg="#f7f9fc", fg=UI["muted"], font=("Ubuntu", 9)).pack(anchor="w")
            tk.Label(tile, text=str(value), bg="#f7f9fc", fg=BRAND_BLUE, font=("Ubuntu", 18, "bold")).pack(
                anchor="w", pady=(4, 0)
            )

        stats.columnconfigure(0, weight=1)
        stats.columnconfigure(1, weight=1)
        metric(stats, "Total breaks", total_breaks, 0)
        metric(stats, "Break minutes", round(total_break_minutes, 2), 1)

        tk.Label(
            card,
            text="By type",
            bg="#ffffff",
            fg=UI["text"],
            font=("Ubuntu", 12, "bold"),
        ).pack(anchor="w", pady=(18, 8))

        rows = tk.Frame(card, bg="#ffffff")
        rows.pack(fill="x")
        for i, (name, count) in enumerate(reasons.items()):
            if count == 0 and name == "Crash":
                continue
            row = tk.Frame(rows, bg="#ffffff")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=name, bg="#ffffff", fg=UI["text"], font=("Ubuntu", 11)).pack(side="left")
            tk.Label(row, text=str(count), bg="#ffffff", fg=BRAND_BLUE, font=("Ubuntu", 11, "bold")).pack(side="right")

        tk.Button(
            card,
            text="Close",
            font=("Ubuntu", 11, "bold"),
            bg=BRAND_BLUE,
            fg="#ffffff",
            activebackground=BRAND_BLUE_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
            command=overlay.destroy,
        ).pack(anchor="e", pady=(20, 0))

    def start_biometric_login(self):
        if not os.path.exists(MODEL_FILE):
            self._ui_alert(
                "No face enrolled",
                "Register your face first, then use Biometric login.",
            )
            return
        self.open_biometric_modal(mode="login")

    def capture_and_train_face(self):
        self.open_biometric_modal(mode="enroll")

    def open_biometric_modal(self, mode="enroll"):
        """FaceGate-style modal for enrollment or biometric login."""
        if self._bio is not None:
            return

        self.stop_camera_preview()
        time.sleep(0.25)

        cap = self.open_camera(0)
        if cap is None or not cap.isOpened():
            self._ui_alert("Camera", "No webcam found. Connect a camera to continue.", kind="error")
            self.start_camera_preview()
            return

        cascade = cv2.CascadeClassifier(self.resource_path(CASCADE_FILE))
        recognizer = None
        if mode == "login" and os.path.exists(MODEL_FILE):
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(MODEL_FILE)

        overlay = tk.Frame(self.root, bg=BIO["scrim"])
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        card = tk.Frame(overlay, bg=BIO["card"], padx=28, pady=22)
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="◎",
            bg=BIO["card"],
            fg=BIO["accent"],
            font=("Ubuntu", 22),
        ).pack()
        title = "Face Enrollment" if mode == "enroll" else "Biometric Login"
        tk.Label(
            card,
            text=title,
            bg=BIO["card"],
            fg=BIO["text"],
            font=("Ubuntu", 18, "bold"),
        ).pack(pady=(4, 2))
        tk.Label(
            card,
            text="Follow the prompts on the camera screen",
            bg=BIO["card"],
            fg=BIO["muted"],
            font=("Ubuntu", 10),
        ).pack()

        status = tk.Label(
            card,
            text="Looking for your face…",
            bg=BIO["card"],
            fg=BIO["warn"],
            font=("Ubuntu", 11),
            wraplength=400,
        )
        status.pack(pady=(10, 8))

        preview_wrap = tk.Frame(card, bg=BIO["preview"], padx=2, pady=2)
        preview_wrap.pack()
        preview = tk.Label(
            preview_wrap,
            bg=BIO["preview"],
            text="Starting camera…",
            fg=BIO["muted"],
            font=("Ubuntu", 11),
            width=52,
            height=14,
            compound="center",
        )
        preview.pack()

        progress_track = tk.Canvas(
            card, width=BIO_PREVIEW_W, height=6, bg=BIO["track"], highlightthickness=0, bd=0
        )
        progress_track.pack(pady=(14, 4))
        progress_fill = progress_track.create_rectangle(0, 0, 0, 6, fill=BIO["accent"], width=0)

        count_label = tk.Label(
            card,
            text=f"0 of {ENROLL_TARGET} captures" if mode == "enroll" else "Verifying identity…",
            bg=BIO["card"],
            fg=BIO["muted"],
            font=("Ubuntu", 10),
        )
        count_label.pack()

        btn_row = tk.Frame(card, bg=BIO["card"])
        btn_row.pack(pady=(16, 4))

        recapture_btn = tk.Button(
            btn_row,
            text="Recapture",
            font=("Ubuntu", 11, "bold"),
            bg=BIO["accent"],
            fg="#ffffff",
            activebackground=BIO["accent_hover"],
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=28,
            pady=9,
            cursor="hand2",
            command=self._bio_recapture,
        )
        if mode == "enroll":
            recapture_btn.pack()

        cancel_btn = tk.Button(
            card,
            text="Cancel",
            font=("Ubuntu", 10),
            bg=BIO["card"],
            fg=BIO["muted"],
            activebackground=BIO["card"],
            activeforeground=BIO["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._bio_cancel,
        )
        cancel_btn.pack(pady=(6, 0))

        self._bio = {
            "mode": mode,
            "overlay": overlay,
            "cap": cap,
            "cascade": cascade,
            "recognizer": recognizer,
            "preview": preview,
            "status": status,
            "count_label": count_label,
            "progress_track": progress_track,
            "progress_fill": progress_fill,
            "faces": [],
            "count": 0,
            "last_capture_at": 0.0,
            "login_deadline": time.time() + 15,
            "matched": False,
            "closed": False,
            "photo": None,
        }
        self.root.after(30, self._bio_tick)

    def _bio_assess_face(self, gray, faces):
        """Return (ok, message, best_face_roi_or_None)."""
        if len(faces) == 0:
            return False, "No face detected — center yourself in the circle.", None
        if len(faces) > 1:
            return False, "Multiple faces detected — only one person please.", None

        x, y, w, h = faces[0]
        face = gray[y:y + h, x:x + w]
        brightness = float(np.mean(face))
        h_img, w_img = gray.shape[:2]
        cx, cy = x + w / 2, y + h / 2
        centered = abs(cx - w_img / 2) < w_img * 0.22 and abs(cy - h_img / 2) < h_img * 0.22
        large_enough = w >= 90 and h >= 90

        if brightness < 45 or brightness > 210:
            return False, "Poor lighting or angle — adjust position.", None
        if not large_enough or not centered:
            return False, "Poor lighting or angle — adjust position.", None
        return True, "Hold still… capturing", cv2.resize(face, (200, 200))

    def _bio_draw_preview(self, frame_bgr, ring_rgb=(93, 207, 122)):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(rgb, (BIO_PREVIEW_W, BIO_PREVIEW_H))
        img = Image.fromarray(rgb).convert("RGBA")
        cx, cy = BIO_PREVIEW_W // 2, BIO_PREVIEW_H // 2
        r = min(BIO_PREVIEW_W, BIO_PREVIEW_H) // 2 - 18
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
        dimmed = Image.blend(img, Image.new("RGBA", img.size, (12, 12, 16, 255)), 0.55)
        result = dimmed.copy()
        result.paste(img, (0, 0), mask=mask)
        draw = ImageDraw.Draw(result)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ring_rgb, width=3)
        return ImageTk.PhotoImage(result.convert("RGB"))

    def _bio_set_progress(self, current, total):
        bio = self._bio
        if not bio:
            return
        width = int(BIO_PREVIEW_W * (current / max(total, 1)))
        bio["progress_track"].coords(bio["progress_fill"], 0, 0, width, 6)
        if bio["mode"] == "enroll":
            bio["count_label"].config(text=f"{current} of {total} captures")

    def _bio_tick(self):
        bio = self._bio
        if bio is None or bio["closed"]:
            return

        ret, frame = bio["cap"].read()
        if not ret:
            bio["status"].config(text="Camera feed lost — check your device.", fg=BIO["warn"])
            self.root.after(80, self._bio_tick)
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = bio["cascade"].detectMultiScale(gray, 1.2, 5, minSize=(60, 60))
        ok, message, face_roi = self._bio_assess_face(gray, faces)
        ring = (93, 207, 122) if ok else (232, 93, 93)
        bio["status"].config(text=message, fg=BIO["ok"] if ok else BIO["warn"])

        photo = self._bio_draw_preview(frame, ring_rgb=ring)
        bio["preview"].configure(image=photo)
        bio["photo"] = photo  # keep reference

        now = time.time()
        if bio["mode"] == "enroll" and ok and face_roi is not None:
            if now - bio["last_capture_at"] > 0.55 and bio["count"] < ENROLL_TARGET:
                bio["faces"].append(face_roi)
                bio["count"] += 1
                bio["last_capture_at"] = now
                self._bio_set_progress(bio["count"], ENROLL_TARGET)
                if bio["count"] >= ENROLL_TARGET:
                    self._bio_finish_enroll()
                    return
        elif bio["mode"] == "login":
            elapsed = max(0.0, bio["login_deadline"] - now)
            self._bio_set_progress(15 - elapsed, 15)
            bio["count_label"].config(text="Verifying identity…")
            if ok and bio["recognizer"] is not None and face_roi is not None:
                _id, confidence = bio["recognizer"].predict(face_roi)
                if confidence < 60:
                    bio["matched"] = True
                    bio["status"].config(text="Face matched — signing you in…", fg=BIO["ok"])
                    self.root.after(450, self._bio_finish_login)
                    return
            if now >= bio["login_deadline"]:
                bio["status"].config(text="Face not recognized. Try again or use password.", fg=BIO["warn"])
                self.root.after(900, self._bio_cancel)
                return

        self.root.after(33, self._bio_tick)

    def _bio_recapture(self):
        bio = self._bio
        if not bio or bio["mode"] != "enroll":
            return
        bio["faces"] = []
        bio["count"] = 0
        bio["last_capture_at"] = 0.0
        self._bio_set_progress(0, ENROLL_TARGET)
        bio["status"].config(text="Looking for your face…", fg=BIO["warn"])

    def _bio_close_modal(self):
        bio = self._bio
        if bio is None:
            return
        bio["closed"] = True
        try:
            bio["cap"].release()
        except Exception:
            pass
        try:
            bio["overlay"].destroy()
        except tk.TclError:
            pass
        self._bio = None
        if self.video_label is not None:
            try:
                if self.video_label.winfo_exists():
                    self.start_camera_preview()
            except tk.TclError:
                pass

    def _bio_cancel(self):
        self._bio_close_modal()

    def _bio_finish_enroll(self):
        bio = self._bio
        if not bio:
            return
        faces = bio["faces"]
        self._bio_close_modal()
        if len(faces) < ENROLL_TARGET:
            self._ui_alert("Enrollment", "Not enough faces captured. Try again.", kind="error")
            return
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array([0] * len(faces)))
        recognizer.save(MODEL_FILE)
        with open(LABEL_MAP_FILE, "w") as f:
            f.write(f"0:{VALID_USERNAME}\n")
        self._ui_alert("Success", "Face enrollment complete. You can use Biometric login.")

    def _bio_finish_login(self):
        bio = self._bio
        if not bio or not bio.get("matched"):
            return
        self._bio_close_modal()
        self._finish_login()

    def verify_face_identity(self, timeout=10):
        """Return True if matched, False if rejected, None if camera/model unavailable (skip)."""
        self.stop_camera_preview()
        time.sleep(0.4)

        if not os.path.exists(MODEL_FILE):
            print("No face model found — skipping face check.")
            self.start_camera_preview()
            return None

        cap = self.open_camera(0)
        if cap is None or not cap.isOpened():
            print("Camera unavailable — skipping face check.")
            self.start_camera_preview()
            return None

        try:
            face_cascade = cv2.CascadeClassifier(self.resource_path(CASCADE_FILE))
            recognizer = cv2.face.LBPHFaceRecognizer_create()
            recognizer.read(MODEL_FILE)

            start_time = time.time()
            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if not ret:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.2, 5)
                for (x, y, w, h) in faces:
                    id_, confidence = recognizer.predict(gray[y:y + h, x:x + w])
                    print(f"Detected face with confidence: {confidence}")
                    if confidence < 60:
                        print("Face matched with known employee.")
                        return True
                time.sleep(0.2)

            print("Face not matched or no face detected.")
            return False
        finally:
            cap.release()
            if self.video_label is not None:
                try:
                    if self.video_label.winfo_exists():
                        self.start_camera_preview()
                except tk.TclError:
                    pass

    def load_previous_breaks(self):
        global break_log_entries, total_break_time
        break_log_entries.clear()
        total_break_time = timedelta()
        session_date = datetime.now().strftime('%Y-%m-%d')
        filename = os.path.join("attendance_logs", f"{session_date}.json")
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                try:
                    data = json.load(f)
                    seen_breaks = set()
                    for session in data.get("sessions", []):
                        for b in session.get("breaks", []):
                            break_key = tuple(b[:3])  # (start_time, end_time, duration)
                            if break_key not in seen_breaks:
                                seen_breaks.add(break_key)
                                break_log_entries.append(b)
                                self.log_break(b[0], b[1], f"{b[2]} ({b[3]})")
                                h, m, s = map(float, b[2].split(":"))
                                total_break_time += timedelta(hours=h, minutes=m, seconds=s)
                except json.JSONDecodeError:
                    pass

    def show_login_time(self):
        if os.path.exists(CRASH_FLAG_FILE):
            self.log_crash_break()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if username.lower() != VALID_USERNAME.lower() or password != VALID_PASSWORD:
            self._ui_alert(
                "Login failed",
                f"Invalid username or password.\nExpected username: {VALID_USERNAME}",
                kind="error",
            )
            return
        # Password login — skip blocking face check (use Biometric login for face)
        self._finish_login()

    def _finish_login(self):
        global login_time, last_user_input_time, last_person_seen_time, break_triggered, break_start_time
        session_date = datetime.now().strftime('%Y-%m-%d')
        filename = os.path.join("attendance_logs", f"{session_date}.json")
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                try:
                    data = json.load(f)
                    first_session = data.get("sessions", [])[0] if data.get("sessions") else None
                    if first_session:
                        today = datetime.now()
                        parsed_time = datetime.strptime(first_session["login_time"], '%I:%M:%S %p').time()
                        login_time = datetime.combine(today.date(), parsed_time)
                    else:
                        login_time = datetime.now()
                except Exception:
                    login_time = datetime.now()
        else:
            login_time = datetime.now()
        last_user_input_time = time.time()
        last_person_seen_time = time.time()
        break_triggered = False
        break_start_time = None
        self._countdown_active = False
        self._face_monitor_alive = False

        self.switch_to_dashboard()
        self.load_previous_breaks()
        threading.Thread(target=self.start_face_recognition_monitoring, daemon=True).start()
        self.monitor_idle_state()
        threading.Thread(target=self.check_internet, daemon=True).start()

    def _dash_btn(self, parent, text, command, primary=False, danger=False):
        if danger:
            bg, fg, abg = "#c45c5c", "#ffffff", "#a84848"
            hl = "#c45c5c"
        elif primary:
            bg, fg, abg = UI["accent"], "#ffffff", UI["accent_hover"]
            hl = UI["accent"]
        else:
            bg, fg, abg = "#ffffff", BRAND_BLUE, "#eaf1f9"
            hl = UI["field_border"]
        return tk.Button(
            parent,
            text=text,
            font=("Ubuntu", 10, "bold" if primary or danger else "normal"),
            bg=bg,
            fg=fg,
            activebackground=abg,
            activeforeground=fg,
            relief="flat",
            bd=0,
            highlightthickness=1 if not primary and not danger else 0,
            highlightbackground=hl,
            highlightcolor=hl,
            padx=14,
            pady=8,
            cursor="hand2",
            command=command,
        )

    def _stat_tile(self, parent, label, value_key, initial):
        shell = tk.Frame(parent, bg=UI["field_border"], bd=0)
        tile = tk.Frame(shell, bg="#f7f9fc", padx=14, pady=12)
        tile.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(tile, text=label, bg="#f7f9fc", fg=UI["muted"], font=("Ubuntu", 9)).pack(anchor="w")
        value = tk.Label(
            tile,
            text=initial,
            bg="#f7f9fc",
            fg=BRAND_BLUE,
            font=("Ubuntu", 16, "bold"),
        )
        value.pack(anchor="w", pady=(4, 0))
        self.shift_values[value_key] = value
        return shell

    def switch_to_dashboard(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        self.root.title("FaceLES · Dashboard")
        self.root.geometry("980x720")
        self.root.configure(bg=UI["bg"])
        self.shift_values = {}
        self._profile_photo = None

        # Top bar
        top = tk.Frame(self.root, bg=UI["panel"], height=64)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(
            top,
            text="FaceLES",
            bg=UI["panel"],
            fg="#ffffff",
            font=("Ubuntu", 18, "bold"),
        ).pack(side="left", padx=22)
        tk.Label(
            top,
            text="Shift monitor",
            bg=UI["panel"],
            fg="#a8c4e0",
            font=("Ubuntu", 10),
        ).pack(side="left", padx=(0, 12))

        status_dot = tk.Label(top, text="●  On shift", bg=UI["panel"], fg=BRAND_BLUE, font=("Ubuntu", 10))
        status_dot.pack(side="right", padx=22)

        body = tk.Frame(self.root, bg=UI["bg"])
        body.pack(fill="both", expand=True, padx=22, pady=18)

        # Profile row
        profile_row = tk.Frame(body, bg=UI["bg"])
        profile_row.pack(fill="x", pady=(0, 16))

        avatar_wrap = tk.Frame(profile_row, bg=UI["bg"])
        avatar_wrap.pack(side="left")
        try:
            image = Image.open("profile_pic.jpg").resize((72, 72)).convert("RGBA")
            mask = Image.new("L", (72, 72), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 72, 72), fill=255)
            image.putalpha(mask)
            self._profile_photo = ImageTk.PhotoImage(image)
            tk.Label(avatar_wrap, image=self._profile_photo, bg=UI["bg"]).pack()
        except Exception:
            tk.Label(
                avatar_wrap,
                text="SU",
                bg=UI["panel"],
                fg="#ffffff",
                font=("Ubuntu", 18, "bold"),
                width=4,
                height=2,
            ).pack()

        identity = tk.Frame(profile_row, bg=UI["bg"])
        identity.pack(side="left", padx=14)
        tk.Label(
            identity,
            text="Saleet Ul Hassan",
            bg=UI["bg"],
            fg=UI["text"],
            font=("Ubuntu", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            identity,
            text="Employee · Face-verified attendance",
            bg=UI["bg"],
            fg=UI["muted"],
            font=("Ubuntu", 10),
        ).pack(anchor="w", pady=(2, 0))

        # Main columns
        main = tk.Frame(body, bg=UI["bg"])
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, bg=UI["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))

        tk.Label(
            left,
            text="Shift overview",
            bg=UI["bg"],
            fg=UI["text"],
            font=("Ubuntu", 12, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        tiles = tk.Frame(left, bg=UI["bg"])
        tiles.pack(fill="x")
        login_str = login_time.strftime("%I:%M %p") if login_time else "--"
        grid = [
            ("Login time", "Shift Login Time", login_str),
            ("On shift", "Shift Login Duration", "00:00:00"),
            ("Breaks", "Shift Breaks Duration", "00:00:00"),
            ("Worked", "Shift Total Work Duration", "00:00:00"),
        ]
        for i, (label, key, initial) in enumerate(grid):
            tile = self._stat_tile(tiles, label, key, initial)
            tile.grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0 if i % 2 == 0 else 8), pady=6)
        tiles.columnconfigure(0, weight=1)
        tiles.columnconfigure(1, weight=1)

        tk.Label(
            left,
            text="Break log",
            bg=UI["bg"],
            fg=UI["text"],
            font=("Ubuntu", 12, "bold"),
        ).pack(anchor="w", pady=(16, 8))

        log_shell = tk.Frame(left, bg=UI["field_border"], bd=0, padx=1, pady=1)
        log_shell.pack(fill="both", expand=True)
        self.inactivity_log = tk.Text(
            log_shell,
            height=12,
            font=("Ubuntu Mono", 10),
            wrap=tk.NONE,
            bg="#f7f9fc",
            fg=UI["text"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=10,
            pady=8,
        )
        self.inactivity_log.pack(fill="both", expand=True)

        # Camera column
        right = tk.Frame(main, bg=UI["bg"], width=360)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right,
            text="Live camera",
            bg=UI["bg"],
            fg=UI["text"],
            font=("Ubuntu", 12, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        cam_shell = tk.Frame(right, bg=UI["field_border"], bd=0, padx=1, pady=1)
        cam_shell.pack(fill="x")
        self.video_label = tk.Label(
            cam_shell,
            bg=UI["camera_bg"],
            text="Camera unavailable",
            fg="#6a8a90",
            font=("Ubuntu", 10),
            width=42,
            height=14,
            compound="center",
        )
        self.video_label.pack()

        toggle_btn = self._dash_btn(right, "Hide camera", None)

        def toggle_camera():
            if self.video_label.winfo_ismapped():
                self.video_label.pack_forget()
                toggle_btn.config(text="Show camera")
            else:
                self.video_label.pack()
                toggle_btn.config(text="Hide camera")

        toggle_btn.config(command=toggle_camera)
        toggle_btn.pack(anchor="w", pady=(10, 0))

        tip = tk.Label(
            right,
            text="Stay in view to avoid\nauto absence breaks.",
            bg=UI["bg"],
            fg=UI["muted"],
            font=("Ubuntu", 9),
            justify="left",
        )
        tip.pack(anchor="w", pady=(14, 0))

        self.start_camera_preview()

        # Action bar
        actions = tk.Frame(self.root, bg="#d5e0ec", height=64)
        actions.pack(fill="x", side="bottom")
        actions.pack_propagate(False)
        inner = tk.Frame(actions, bg="#d5e0ec")
        inner.pack(expand=True)

        self._dash_btn(inner, "Start break", self.start_manual_break, primary=True).pack(
            side="left", padx=6, pady=12
        )
        self._dash_btn(inner, "Export CSV", self.export_log_to_csv).pack(side="left", padx=6, pady=12)
        self._dash_btn(inner, "Summary", self.show_summary).pack(side="left", padx=6, pady=12)
        self._dash_btn(inner, "Logout", self.on_close, danger=True).pack(side="left", padx=6, pady=12)

        self.update_shift_stats()
        self.root.after(1000, self._tick_dashboard_stats)

    def _tick_dashboard_stats(self):
        try:
            if not self.shift_values:
                return
            self.update_shift_stats()
            self.root.after(1000, self._tick_dashboard_stats)
        except tk.TclError:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = EmployeeMonitorApp(root)
    atexit.register(app.save_shift_data_to_json)
    root.mainloop()

