import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
CRASH_FLAG_FILE = "crash_flag.tmp"

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

INACTIVITY_THRESHOLD = 60
VALID_USERNAME = "saleet"
VALID_PASSWORD = "123"
MANUAL_BREAK_OPTIONS = ["Meeting", "Lunch", "Prayer", "Tea", "Call"]


def on_close():
    if messagebox.askokcancel("Quit", "Are you sure you want to Logout?"):
        save_shift_data_to_json()
        root.destroy()


def check_internet():
    global internet_was_connected
    while True:
        try:
            urllib.request.urlopen('http://clients3.google.com/generate_204', timeout=5)
            internet_was_connected = True
        except:
            if internet_was_connected:
                internet_was_connected = False
                root.after(0, log_crash_break)
        time.sleep(10)


def resource_path(relative_path):
    import sys
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)


def update_activity(event=None):
    global last_user_input_time
    last_user_input_time = time.time()


def bind_activity_events():
    root.bind_all("<Motion>", update_activity)
    root.bind_all("<KeyPress>", update_activity)

def log_crash_break():
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
            log_break(log_entry[0], log_entry[1], f"{log_entry[2]} (Crash)")


def start_camera_preview():
    global video_label, video_stream_active, preview_cap
    video_stream_active = True
    preview_cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

    if not preview_cap.isOpened():
        print("Camera could not be opened")
        return

    def update_frame():
        if not video_stream_active:
            preview_cap.release()
            return
        ret, frame = preview_cap.read()
        if ret:
            frame = cv2.resize(frame, (300, 200))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(frame))
            video_label.configure(image=img)
            video_label.image = img
        video_label.after(30, update_frame)

    update_frame()


def stop_camera_preview():
    global video_stream_active, preview_cap
    video_stream_active = False
    if preview_cap is not None:
        preview_cap.release()
        preview_cap = None


def start_face_recognition_monitoring():
    global last_person_seen_time, is_user_visible
    # face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    face_cascade = cv2.CascadeClassifier(resource_path('haarcascade_frontalface_default.xml'))
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("lbph_model.yml")

    # Load label map
    label_map = {}
    if os.path.exists("label_map.txt"):
        with open("label_map.txt", "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) == 2:
                    label_map[int(parts[0])] = parts[1]

    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

    if not cap.isOpened():
        print("Error: Cannot open webcam.")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
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


def monitor_idle_state():
    def idle_check():
        global break_start_time, break_triggered, break_reason, last_break_end_time
        while True:
            now = time.time()
            no_user_input = now - last_user_input_time > INACTIVITY_THRESHOLD
            user_absent = now - last_person_seen_time > INACTIVITY_THRESHOLD
            cooldown_elapsed = True
            if last_break_end_time:
                cooldown_elapsed = time.time() - last_break_end_time > BREAK_COOLDOWN_SECONDS

            if (no_user_input or user_absent) and not break_triggered and cooldown_elapsed:
                if no_user_input and user_absent:
                    break_reason = "Inactivity + Absence"
                elif no_user_input:
                    break_reason = "Inactivity Only"
                elif user_absent:
                    break_reason = "Absence Only"
                inactivity_elapsed = now - last_user_input_time
                absence_elapsed = now - last_person_seen_time
                earliest_trigger = min(inactivity_elapsed, absence_elapsed)
                break_start_time = datetime.now() - timedelta(seconds=earliest_trigger)
                root.after(0, lambda: show_break_countdown(10))
                break_triggered = True

            if break_triggered and (not no_user_input and not user_absent):
                if break_start_time:
                    root.after(0, auto_end_break)
            time.sleep(1)

    threading.Thread(target=idle_check, daemon=True).start()


def show_break_alert_auto():
    global break_window
    break_window = tk.Toplevel(root)
    break_window.transient(root)
    break_window.grab_set()
    break_window.lift()
    break_window.focus_force()
    break_window.title("Auto Break Started")
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    break_window.geometry(f"500x300+{root_x}+{root_y}")
    break_window.configure(bg="#fff8e1")
    break_window.resizable(False, False)
    break_window.protocol("WM_DELETE_WINDOW", lambda: None)

    tk.Label(break_window, text="⚠ Auto Break Triggered", font=("Segoe UI", 16, "bold"), fg="#e65100",
             bg="#fff8e1").pack(pady=(15, 5))
    time_label = tk.Label(break_window, text="", font=("Segoe UI", 14), bg="#fff8e1")
    time_label.pack(pady=(5, 15))

    def update_time_label():
        if break_start_time:
            now = datetime.now()
            elapsed = now - break_start_time
            time_label.config(text=f"Break duration: {str(elapsed).split('.')[0]}")
            time_label.after(1000, update_time_label)

    def manual_end_auto_break():
        global total_break_time, break_start_time, break_window, break_triggered
        if break_start_time:
            break_end_time = datetime.now()
            break_duration = break_end_time - break_start_time
            total_break_time += break_duration
            log_entry = [
                break_start_time.strftime('%I:%M:%S %p'),
                break_end_time.strftime('%I:%M:%S %p'),
                str(break_duration),
                break_reason or "Auto"
            ]
            break_log_entries.append(log_entry)
            display_reason = "Idle Sitting" if break_reason == "Inactivity Only" else break_reason
            log_break(log_entry[0], log_entry[1], f"{log_entry[2]} ({display_reason})")
            break_start_time = None
            last_break_end_time = time.time()

        if break_window:
            break_window.destroy()
            break_window = None

        break_triggered = False
        global last_user_input_time, last_person_seen_time
        last_user_input_time = time.time()
        last_person_seen_time = time.time()
        update_shift_stats()

    update_time_label()

    tk.Button(break_window, text="End Break", font=("Segoe UI", 12, "bold"), bg="#e65100", fg="white", padx=12, pady=6,
              relief="flat", command=manual_end_auto_break).pack(pady=10)


def auto_start_break():
    global break_start_time
    if not break_start_time:
        inactivity_elapsed = time.time() - last_user_input_time
        absence_elapsed = time.time() - last_person_seen_time
        earliest_trigger = min(inactivity_elapsed, absence_elapsed)
        break_start_time = datetime.now() - timedelta(seconds=earliest_trigger)
    show_break_alert_auto()
    # log_break("AUTO", f"Break started", f"0:00:00.00 ({break_reason})")
    display_reason = "Idle Sitting" if break_reason == "Inactivity Only" else break_reason
    log_break("AUTO", f"Break started", f"0:00:00.00 ({display_reason})")
    update_shift_stats()
    break_triggered = True


def auto_end_break():
    global break_start_time, total_break_time, break_reason
    if break_start_time:
        break_end_time = datetime.now()
        break_duration = break_end_time - break_start_time
        total_break_time += break_duration
        log_entry = [
            break_start_time.strftime('%I:%M:%S %p'),
            break_end_time.strftime('%I:%M:%S %p'),
            str(break_duration),
            break_reason
        ]
        break_log_entries.append(log_entry)
        # log_break(log_entry[0], log_entry[1], f"{log_entry[2]} (Auto: {break_reason})")
        display_reason = "Idle Sitting" if break_reason == "Inactivity Only" else break_reason
        log_break(log_entry[0], log_entry[1], f"{log_entry[2]} (Auto: {display_reason})")
        break_start_time = None
        last_break_end_time = time.time()
        break_reason = None
        update_shift_stats()
        # break_triggered = False  # removed to avoid redundant reset

def show_break_countdown(seconds=10):
    countdown_win = tk.Toplevel(root)
    countdown_win.title("Break Starting Soon")
    countdown_win.geometry("300x150+{}+{}".format(root.winfo_x() + 100, root.winfo_y() + 100))
    countdown_win.configure(bg="#fff3e0")
    countdown_win.transient(root)
    countdown_win.grab_set()
    countdown_win.lift()
    countdown_win.focus_force()

    label = tk.Label(countdown_win, text="Break will start in:", font=("Segoe UI", 12), bg="#fff3e0")
    label.pack(pady=(20, 5))
    timer_label = tk.Label(countdown_win, text="", font=("Segoe UI", 24, "bold"), fg="#d84315", bg="#fff3e0")
    timer_label.pack()

    def cancel_countdown():
        global break_triggered, break_start_time, last_user_input_time, last_person_seen_time
        break_triggered = False
        break_start_time = None
        last_user_input_time = time.time()
        last_person_seen_time = time.time()
        countdown_win.destroy()

    countdown_win.protocol("WM_DELETE_WINDOW", cancel_countdown)

    def countdown(count):
        if count > 0:
            timer_label.config(text=f"{count}s")
            countdown_win.after(1000, countdown, count - 1)
            root.bell()  # Add beep sound
        else:
            countdown_win.destroy()
            auto_start_break()

    countdown(seconds)


def start_manual_break():
    global break_start_time, manual_break_type, break_reason
    if break_start_time:
        messagebox.showinfo("Break Active", "A break is already in progress.")
        return

    def start_selected_break():
        global break_reason, manual_break_type
        selected = break_type_var.get()
        if not selected:
            messagebox.showwarning("Select Break", "Please choose a break type.")
            return
        break_reason = selected
        break_selection.destroy()
        manual_break_type = selected
        begin_manual_break()

    # Get root window position to center the panel relative to it
    root.update_idletasks()
    x = root.winfo_x() + root.winfo_width() // 2 - 160
    y = root.winfo_y() + root.winfo_height() // 2 - 110

    break_selection = tk.Toplevel(root)
    break_selection.transient(root)
    break_selection.geometry(f"320x250+{x}+{y}")
    break_selection.configure(bg="#f0f2f5")

    container = tk.Frame(break_selection, bg="#f0f2f5")
    container.pack(expand=True, fill="both", padx=20, pady=15)

    tk.Label(container, text="Select Break Type", font=("Segoe UI", 13, "bold"),
             bg="#f0f2f5", fg="#1a237e").pack(pady=(0, 10))

    break_type_var = tk.StringVar()
    style = ttk.Style()
    style.configure("TRadiobutton", background="#f0f2f5", font=("Segoe UI", 11), relief="flat")
    style.map("TRadiobutton", background=[('active', '#f0f2f5')])
    style.configure("TButton", font=("Segoe UI", 11), padding=6)

    for option in MANUAL_BREAK_OPTIONS:
        rb = ttk.Radiobutton(container, text=option, variable=break_type_var, value=option, style="TRadiobutton")
        rb.pack(anchor="w", pady=2, padx=5)

    ttk.Button(container, text="Start Break", command=start_selected_break, style="TButton").pack(pady=(10, 5))


def begin_manual_break():
    global break_start_time, manual_break_type, break_window
    break_start_time = datetime.now()
    break_window = tk.Toplevel(root)
    break_window.transient(root)
    root_x = root.winfo_x()
    root_y = root.winfo_y()
    break_window.geometry(f"500x250+{root_x}+{root_y}")
    break_window.grab_set()
    break_window.lift()
    break_window.focus_force()
    break_window.title(f"{manual_break_type} Break")
    break_window.configure(bg="#e3f2fd")
    break_window.resizable(False, False)
    time_label = tk.Label(break_window, text="", font=("Segoe UI", 14), bg="#e3f2fd")
    time_label.pack(pady=(20, 10))

    def update_time():
        if break_start_time:
            now = datetime.now()
            elapsed = now - break_start_time
            time_label.config(text=f"{manual_break_type} break in progress: {str(elapsed).split('.')[0]}")
            time_label.after(1000, update_time)

    update_time()

    def end_manual_break():
        global total_break_time, break_start_time, break_window
        if break_start_time:
            break_end_time = datetime.now()
            break_duration = break_end_time - break_start_time
            total_break_time += break_duration
            log_entry = [
                break_start_time.strftime('%I:%M:%S %p'),
                break_end_time.strftime('%I:%M:%S %p'),
                str(break_duration),
                manual_break_type
            ]
            break_log_entries.append(log_entry)
            log_break(log_entry[0], log_entry[1], f"{log_entry[2]} ({manual_break_type})")
            break_start_time = None
        global last_user_input_time, last_person_seen_time
        last_user_input_time = time.time()
        last_person_seen_time = time.time()
        break_window.destroy()
        break_window = None
        update_shift_stats()

    tk.Button(break_window, text="End Break", font=("Segoe UI", 12, "bold"), bg="#fff8e1", fg="black", padx=12, pady=6,
              relief="flat", command=end_manual_break).pack(pady=10)


def log_break(start_time, end_time, duration):
    try:
        # If duration is like '0:00:05.227240 (Reason)', round the seconds
        parts = duration.split(" ")
        time_part = parts[0]
        reason_part = " ".join(parts[1:]) if len(parts) > 1 else ""
        h, m, s = map(float, time_part.split(":"))
        rounded_duration = f"{int(h):02}:{int(m):02}:{s:.2f}"
        display_duration = f"{rounded_duration} {reason_part}".strip()
        inactivity_log.insert(tk.END, f"{start_time} to {end_time} --- {display_duration}\n")
    except Exception as e:
        inactivity_log.insert(tk.END, f"{start_time} to {end_time} --- {duration} (Error rounding: {e})\n")
    inactivity_log.yview(tk.END)


def update_shift_stats():
    if login_time:
        current_time = datetime.now()
        login_duration = current_time - login_time
        work_duration = login_duration - total_break_time
        shift_values["Shift Login Duration"].config(text=str(login_duration).split(".")[0])
        shift_values["Shift Breaks Duration"].config(text=str(total_break_time).split(".")[0])
        shift_values["Shift Total Work Duration"].config(text=str(work_duration).split(".")[0])


def save_shift_data_to_json():
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


def export_log_to_csv():
    if not break_log_entries:
        messagebox.showwarning("Export", "No break logs to export.")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    if not file_path:
        return
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Start Time", "End Time", "Duration", "Reason"])
        writer.writerows(break_log_entries)
    messagebox.showinfo("Export", f"Break log exported to {file_path}")


def show_summary():
    total_breaks = len(break_log_entries)
    total_break_minutes = sum(
        [float(timedelta_str.split(':')[1]) + float(timedelta_str.split(':')[2]) / 60 for _, _, timedelta_str, _ in
         break_log_entries])
    # reasons = {"Inactivity Only": 0, "Absence Only": 0, "Inactivity + Absence": 0}
    reasons = {
        "Inactivity Only": 0,
        "Absence Only": 0,
        "Inactivity + Absence": 0,
        "Meeting": 0,
        "Lunch": 0,
        "Prayer": 0,
        "Tea": 0,
        "Call": 0
    }
    for entry in break_log_entries:
        reason = entry[3]
        if reason in reasons:
            reasons[reason] += 1
    summary = f"Total Breaks: {total_breaks}\nTotal Break Time (approx min): {round(total_break_minutes, 2)}\n\n"
    for k, v in reasons.items():
        summary += f"{k}: {v}\n"
    messagebox.showinfo("Daily Summary", summary)


def verify_face_identity(timeout=10):
    stop_camera_preview()
    time.sleep(0.5)  # give it a short moment to release camera
    start_camera_preview()

    face_cascade = cv2.CascadeClassifier(resource_path('haarcascade_frontalface_default.xml'))
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("lbph_model.yml")
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

    start_time = time.time()
    matched = False
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
                cap.release()
                print("Face matched with known employee.")
                return True
        time.sleep(0.2)

    cap.release()
    print("Face not matched or no face detected.")
    messagebox.showerror("Face Authentication", "Face not matched or no face detected.")
    return False


def capture_and_train_face():
    stop_camera_preview()
    time.sleep(0.5)  # give it a short moment to release camera
    start_camera_preview()

    face_cascade = cv2.CascadeClassifier(resource_path('haarcascade_frontalface_default.xml'))
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    faces = []
    count = 0

    while count < 100:
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detected_faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        for (x, y, w, h) in detected_faces:
            face_img = gray[y:y + h, x:x + w]
            resized = cv2.resize(face_img, (200, 200))
            faces.append(resized)
            count += 1
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(frame, f"Capturing Face {count}/100", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (255, 255, 255), 2)
        cv2.imshow("Registering Face", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if len(faces) >= 10:
        labels = [0] * len(faces)
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(labels))
        recognizer.save("lbph_model.yml")
        messagebox.showinfo("Success", "Face registration complete.")
    else:
        messagebox.showerror("Error", "Not enough faces captured. Try again.")


def load_previous_breaks():
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
                            log_break(b[0], b[1], f"{b[2]} ({b[3]})")
                            h, m, s = map(float, b[2].split(":"))
                            total_break_time += timedelta(hours=h, minutes=m, seconds=s)
            except json.JSONDecodeError:
                pass


def show_login_time():
    if os.path.exists(CRASH_FLAG_FILE):
        log_crash_break()
    username = username_entry.get().strip()
    password = password_entry.get().strip()
    if username != VALID_USERNAME or password != VALID_PASSWORD:
        messagebox.showerror("Login Failed", "Invalid username or password.")
        return

    # Start a short facial verification session
    if not verify_face_identity(timeout=10):
        messagebox.showerror("Face Mismatch", "Face did not match registered employee.")
        return

    # Login success
    global login_time, last_user_input_time
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

    switch_to_dashboard()
    load_previous_breaks()  # ← Load previous breaks after successful login
    threading.Thread(target=start_face_recognition_monitoring, daemon=True).start()
    monitor_idle_state()
    threading.Thread(target=check_internet, daemon=True).start()  # ← Add this here


def switch_to_dashboard():
    for widget in root.winfo_children():
        widget.destroy()
    root.title("Employee Dashboard")
    root.configure(bg="#f0f2f5")
    profile_frame = tk.Frame(root, bg="#f0f2f5", pady=10)
    profile_frame.pack()
    tk.Label(profile_frame, text="Saleet Ul Hassan", font=("Segoe UI", 14, "bold"), bg="#f0f2f5").pack()
    content_frame = tk.Frame(root, bg="#f0f2f5")
    content_frame.pack(pady=10)
    try:
        image = Image.open("profile_pic.jpg").resize((100, 100)).convert("RGBA")
        mask = Image.new('L', (100, 100), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, 100, 100), fill=255)
        image.putalpha(mask)
        circle_image = ImageTk.PhotoImage(image)
        image_label = tk.Label(content_frame, image=circle_image, bg="#f0f2f5")
        image_label.image = circle_image
        image_label.pack(side="left", padx=20)
    except:
        pass
    global shift_values
    shift_values = {}
    stats_frame = tk.Frame(content_frame, bg="#f0f2f5")
    stats_frame.pack(side="left")

    # Live Camera Preview
    preview_frame = tk.Frame(content_frame, bg="#f0f2f5")
    preview_frame.pack(side="left", padx=20)

    tk.Label(preview_frame, text="Live Camera View", font=("Segoe UI", 12), bg="#f0f2f5").pack()
    camera_container = tk.Frame(preview_frame, bg="#000000", highlightbackground="#1976d2", highlightthickness=2, bd=0)
    camera_container.pack()

    tk.Label(camera_container, text="Monitoring...", font=("Segoe UI", 9), bg="#000000", fg="white").place(x=5, y=5)

    global video_label

    video_label = tk.Label(camera_container, bg="#000000", width=300, height=200)
    video_label.pack()

    # Declare toggle_btn first so it can be updated later
    toggle_btn = tk.Button(preview_frame, text="Hide Camera", font=("Segoe UI", 9))

    def toggle_camera():
        global video_label
        if video_label.winfo_ismapped():
            video_label.pack_forget()
            toggle_btn.config(text="Show Camera")
        else:
            video_label.pack()
            toggle_btn.config(text="Hide Camera")

    toggle_btn.config(command=toggle_camera)
    toggle_btn.pack(pady=5)

    start_camera_preview()

    stats = [
        ("Shift Login Time", login_time.strftime('%I:%M %p')),
        ("Shift Login Duration", "00:00:00"),
        ("Shift Breaks Duration", "00:00:00"),
        ("Shift Total Work Duration", "00:00:00"),
    ]
    for text, value in stats:
        row = tk.Frame(stats_frame, bg="#f0f2f5")
        row.pack(anchor="w", padx=30, pady=4)
        tk.Label(row, text=text + ":", font=("Segoe UI", 12), bg="#f0f2f5").pack(side="left")
        shift_values[text] = tk.Label(row, text=value, font=("Segoe UI", 12, "bold"), fg="#1976d2", bg="#f0f2f5")
        shift_values[text].pack(side="left")
    action_frame = tk.Frame(root, bg="#f0f2f5")
    action_frame.pack(pady=(10, 5))
    tk.Button(action_frame, text="Mark Break", font=("Segoe UI", 11), command=start_manual_break, bg="#ffcc00",
              padx=10).pack(side="left", padx=10)
    tk.Button(action_frame, text="Summary", command=show_summary).pack(side="left", padx=10)
    tk.Button(action_frame, text="Export CSV", command=export_log_to_csv).pack(side="left", padx=10)
    tk.Button(action_frame, text="Logout", font=("Segoe UI", 11), command=on_close, bg="#e57373", padx=10).pack(
        side="left", padx=10)
    log_frame = tk.Frame(root, highlightbackground="#1976d2", highlightthickness=2, pady=5, padx=5, bg="#ffffff")
    log_frame.pack(pady=15, fill="both", expand=True)
    tk.Label(log_frame, text="Inactivity Log", font=("Segoe UI", 12, "bold"), fg="#1976d2", bg="#ffffff").pack()
    global inactivity_log
    inactivity_log = tk.Text(log_frame, height=12, width=70, font=("Segoe UI", 11), bg="#ffffff")
    inactivity_log.pack()
    bind_activity_events()

    def update_time_loop():
        while True:
            time.sleep(1)
            root.after(0, update_shift_stats)

    threading.Thread(target=update_time_loop, daemon=True).start()


root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", on_close)
root.title("Employment System")
root.geometry("720x700")
root.configure(bg="#f0f2f5")
root.resizable(False, False)
tk.Label(root, text="Official Email / Username *", bg="#f0f2f5", font=("Segoe UI", 15)).pack(pady=(30, 8))
username_entry = ttk.Entry(root, width=40, font=("Segoe UI", 20))
username_entry.pack()
tk.Label(root, text="Password", bg="#f0f2f5", font=("Segoe UI", 15)).pack(pady=(15, 8))
password_entry = ttk.Entry(root, width=40, font=("Segoe UI", 20), show="*")
password_entry.pack()
login_button = ttk.Button(root, text="Login", command=show_login_time)

tk.Label(root, text="Camera View (Adjust yourself):", bg="#f0f2f5", font=("Segoe UI", 12)).pack(pady=(10, 0))
video_label = tk.Label(root, bg="#000000", width=300, height=200)
video_label.pack(pady=10)
start_camera_preview()

login_button.pack(pady=25)
register_button = ttk.Button(root, text="Register Face", command=capture_and_train_face)
register_button.pack(pady=(0, 10))
bind_activity_events()

try:
    with open(CRASH_FLAG_FILE, "w") as f:
        f.write("crash marker")
    root.mainloop()
except Exception as e:
    log_crash_break()
    save_shift_data_to_json()
    raise e
finally:
    if os.path.exists(CRASH_FLAG_FILE):
        os.remove(CRASH_FLAG_FILE)
