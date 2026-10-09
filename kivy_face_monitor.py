import json
import os
import numpy as np
from datetime import datetime, timedelta
import threading
import time
import cv2
import csv
import socket
import platform
import getpass
import urllib.request
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KivyImage
from kivy.uix.scrollview import ScrollView
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.modalview import ModalView
from kivy.properties import StringProperty, ObjectProperty, NumericProperty, BooleanProperty
from kivy.core.window import Window
from kivy.uix.carousel import Carousel
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.spinner import Spinner
from kivy.uix.progressbar import ProgressBar
from PIL import Image as PILImage, ImageDraw
import webbrowser

CRASH_FLAG_FILE = "crash_flag.tmp"

# Constants
INACTIVITY_THRESHOLD = 60
VALID_USERNAME = "saleet"
VALID_PASSWORD = "123"
MANUAL_BREAK_OPTIONS = ["Meeting", "Lunch", "Prayer", "Tea", "Call"]
BREAK_COOLDOWN_SECONDS = 60


class EmployeeDashboard(BoxLayout):
    login_time = ObjectProperty(None)
    last_user_input_time = NumericProperty(0)
    last_person_seen_time = NumericProperty(0)
    total_break_time = ObjectProperty(timedelta())
    break_start_time = ObjectProperty(None)
    break_triggered = BooleanProperty(False)
    break_reason = StringProperty("")
    manual_break_type = StringProperty("")
    is_user_visible = BooleanProperty(True)
    internet_was_connected = BooleanProperty(True)
    last_break_end_time = NumericProperty(0)
    break_log_entries = ObjectProperty([])
    preview_cap = ObjectProperty(None)
    video_stream_active = BooleanProperty(False)
    video_texture = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(EmployeeDashboard, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.last_user_input_time = time.time()
        self.last_person_seen_time = time.time()
        self.break_log_entries = []

        # Start monitoring threads
        threading.Thread(target=self.check_internet, daemon=True).start()
        threading.Thread(target=self.monitor_idle_state, daemon=True).start()

        # Schedule regular updates
        Clock.schedule_interval(self.update_shift_stats, 1)

    def on_stop(self):
        if self.login_time:
            self.save_shift_data_to_json()
        if os.path.exists(CRASH_FLAG_FILE):
            os.remove(CRASH_FLAG_FILE)

    def resource_path(self, relative_path):
        import sys
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.abspath(relative_path)

    def update_activity(self, *args):
        self.last_user_input_time = time.time()

    def log_crash_break(self):
        if self.login_time:
            now = datetime.now()
            duration = timedelta(seconds=1)
            self.total_break_time += duration
            log_entry = [
                now.strftime('%I:%M:%S %p'),
                now.strftime('%I:%M:%S %p'),
                str(duration),
                "Crash"
            ]
            if not self.break_log_entries or self.break_log_entries[-1][3] != "Crash":
                self.break_log_entries.append(log_entry)
                self.log_break(log_entry[0], log_entry[1], f"{log_entry[2]} (Crash)")

    def start_camera_preview(self):
        self.video_stream_active = True
        self.preview_cap = cv2.VideoCapture(0)

        if not self.preview_cap.isOpened():
            print("Camera could not be opened")
            return

        Clock.schedule_interval(self.update_camera_frame, 1 / 30)

    def update_camera_frame(self, dt):
        if not self.video_stream_active:
            return

        ret, frame = self.preview_cap.read()
        if ret:
            frame = cv2.resize(frame, (300, 200))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # buf = frame.tostring()
            buf = frame.tobytes()

            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')
            # self.ids.camera_preview.texture = texture
            if hasattr(self, 'camera_preview') and self.camera_preview:
                self.camera_preview.texture = texture

    def stop_camera_preview(self):
        self.video_stream_active = False
        if self.preview_cap is not None:
            self.preview_cap.release()
            self.preview_cap = None

    def start_face_recognition_monitoring(self):
        face_cascade = cv2.CascadeClassifier(self.resource_path('haarcascade_frontalface_default.xml'))
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

        cap = cv2.VideoCapture(0)

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

            self.is_user_visible = recognized
            if recognized:
                self.last_person_seen_time = time.time()

            time.sleep(1)

    def monitor_idle_state(self):
        while True:
            now = time.time()
            no_user_input = now - self.last_user_input_time > INACTIVITY_THRESHOLD
            user_absent = now - self.last_person_seen_time > INACTIVITY_THRESHOLD
            cooldown_elapsed = True
            if self.last_break_end_time:
                cooldown_elapsed = time.time() - self.last_break_end_time > BREAK_COOLDOWN_SECONDS

            if (no_user_input or user_absent) and not self.break_triggered and cooldown_elapsed:
                if no_user_input and user_absent:
                    self.break_reason = "Inactivity + Absence"
                elif no_user_input:
                    self.break_reason = "Inactivity Only"
                elif user_absent:
                    self.break_reason = "Absence Only"

                inactivity_elapsed = now - self.last_user_input_time
                absence_elapsed = now - self.last_person_seen_time
                earliest_trigger = min(inactivity_elapsed, absence_elapsed)
                self.break_start_time = datetime.now() - timedelta(seconds=earliest_trigger)

                Clock.schedule_once(lambda dt: self.show_break_countdown(10))
                self.break_triggered = True

            if self.break_triggered and (not no_user_input and not user_absent):
                if self.break_start_time:
                    Clock.schedule_once(lambda dt: self.auto_end_break())
            time.sleep(1)

    def show_break_countdown(self, seconds=10):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="Break will start in:", font_size=16))

        timer_label = Label(text=f"{seconds}s", font_size=24, color=(0.85, 0.26, 0.08, 1))
        content.add_widget(timer_label)

        popup = Popup(title="Break Starting Soon",
                      content=content,
                      size_hint=(0.5, 0.3),
                      auto_dismiss=False)

        def cancel_countdown():
            self.break_triggered = False
            self.break_start_time = None
            self.last_user_input_time = time.time()
            self.last_person_seen_time = time.time()
            popup.dismiss()

        def countdown(count):
            if count > 0:
                timer_label.text = f"{count}s"
                Clock.schedule_once(lambda dt: countdown(count - 1), 1)
            else:
                popup.dismiss()
                self.auto_start_break()

        content.add_widget(Button(text="Cancel", size_hint=(1, 0.3), on_press=lambda x: cancel_countdown()))
        popup.open()
        countdown(seconds)

    def auto_start_break(self):
        if not self.break_start_time:
            inactivity_elapsed = time.time() - self.last_user_input_time
            absence_elapsed = time.time() - self.last_person_seen_time
            earliest_trigger = min(inactivity_elapsed, absence_elapsed)
            self.break_start_time = datetime.now() - timedelta(seconds=earliest_trigger)

        self.show_break_alert_auto()
        display_reason = "Idle Sitting" if self.break_reason == "Inactivity Only" else self.break_reason
        self.log_break("AUTO", f"Break started", f"0:00:00.00 ({display_reason})")
        self.update_shift_stats()
        self.break_triggered = True

    def show_break_alert_auto(self):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="⚠ Auto Break Triggered", font_size=16, color=(0.9, 0.32, 0, 1)))

        time_label = Label(text="", font_size=14)
        content.add_widget(time_label)

        def update_time_label(dt):
            if self.break_start_time:
                now = datetime.now()
                elapsed = now - self.break_start_time
                time_label.text = f"Break duration: {str(elapsed).split('.')[0]}"

        def manual_end_auto_break(instance):
            if self.break_start_time:
                break_end_time = datetime.now()
                break_duration = break_end_time - self.break_start_time
                self.total_break_time += break_duration
                log_entry = [
                    self.break_start_time.strftime('%I:%M:%S %p'),
                    break_end_time.strftime('%I:%M:%S %p'),
                    str(break_duration),
                    self.break_reason or "Auto"
                ]
                self.break_log_entries.append(log_entry)
                display_reason = "Idle Sitting" if self.break_reason == "Inactivity Only" else self.break_reason
                self.log_break(log_entry[0], log_entry[1], f"{log_entry[2]} ({display_reason})")
                self.break_start_time = None
                self.last_break_end_time = time.time()

            self.last_user_input_time = time.time()
            self.last_person_seen_time = time.time()
            self.update_shift_stats()
            popup.dismiss()
            self.break_triggered = False

        content.add_widget(Button(text="End Break", size_hint=(1, 0.3), on_press=manual_end_auto_break))

        popup = Popup(title="Auto Break Started",
                      content=content,
                      size_hint=(0.6, 0.4),
                      auto_dismiss=False)

        Clock.schedule_interval(update_time_label, 1)
        popup.open()

    def auto_end_break(self):
        if self.break_start_time:
            break_end_time = datetime.now()
            break_duration = break_end_time - self.break_start_time
            self.total_break_time += break_duration
            log_entry = [
                self.break_start_time.strftime('%I:%M:%S %p'),
                break_end_time.strftime('%I:%M:%S %p'),
                str(break_duration),
                self.break_reason
            ]
            self.break_log_entries.append(log_entry)
            display_reason = "Idle Sitting" if self.break_reason == "Inactivity Only" else self.break_reason
            self.log_break(log_entry[0], log_entry[1], f"{log_entry[2]} (Auto: {display_reason})")
            self.break_start_time = None
            self.last_break_end_time = time.time()
            self.break_reason = ""
            self.update_shift_stats()

    def start_manual_break(self):
        if self.break_start_time:
            self.show_popup("Break Active", "A break is already in progress.")
            return

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="Select Break Type", font_size=16, color=(0.13, 0.59, 0.95, 1)))

        self.manual_break_type = ""
        spinner = Spinner(
            text='Select Break Type',
            values=MANUAL_BREAK_OPTIONS,
            size_hint=(1, 0.3),
            font_size=14
        )

        def on_spinner_select(spinner, text):
            self.manual_break_type = text

        spinner.bind(text=on_spinner_select)
        content.add_widget(spinner)

        def start_selected_break(instance):
            if not self.manual_break_type:
                self.show_popup("Select Break", "Please choose a break type.")
                return

            popup.dismiss()
            self.begin_manual_break()

        content.add_widget(Button(text="Start Break", size_hint=(1, 0.3), on_press=start_selected_break))

        popup = Popup(title="Manual Break",
                      content=content,
                      size_hint=(0.5, 0.4))
        popup.open()

    def begin_manual_break(self):
        self.break_start_time = datetime.now()

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=f"{self.manual_break_type} Break", font_size=16, color=(0.13, 0.59, 0.95, 1)))

        time_label = Label(text="", font_size=14)
        content.add_widget(time_label)

        def update_time(dt):
            if self.break_start_time:
                now = datetime.now()
                elapsed = now - self.break_start_time
                time_label.text = f"{self.manual_break_type} break in progress: {str(elapsed).split('.')[0]}"

        def end_manual_break(instance):
            if self.break_start_time:
                break_end_time = datetime.now()
                break_duration = break_end_time - self.break_start_time
                self.total_break_time += break_duration
                log_entry = [
                    self.break_start_time.strftime('%I:%M:%S %p'),
                    break_end_time.strftime('%I:%M:%S %p'),
                    str(break_duration),
                    self.manual_break_type
                ]
                self.break_log_entries.append(log_entry)
                self.log_break(log_entry[0], log_entry[1], f"{log_entry[2]} ({self.manual_break_type})")
                self.break_start_time = None

            self.last_user_input_time = time.time()
            self.last_person_seen_time = time.time()
            popup.dismiss()
            self.update_shift_stats()

        content.add_widget(Button(text="End Break", size_hint=(1, 0.3), on_press=end_manual_break))

        popup = Popup(title=f"{self.manual_break_type} Break",
                      content=content,
                      size_hint=(0.6, 0.4),
                      auto_dismiss=False)

        Clock.schedule_interval(update_time, 1)
        popup.open()

    def log_break(self, start_time, end_time, duration):
        try:
            parts = duration.split(" ")
            time_part = parts[0]
            reason_part = " ".join(parts[1:]) if len(parts) > 1 else ""
            h, m, s = map(float, time_part.split(":"))
            rounded_duration = f"{int(h):02}:{int(m):02}:{s:.2f}"
            display_duration = f"{rounded_duration} {reason_part}".strip()
            self.ids.inactivity_log.text += f"{start_time} to {end_time} --- {display_duration}\n"
        except Exception as e:
            self.ids.inactivity_log.text += f"{start_time} to {end_time} --- {duration} (Error rounding: {e})\n"

    def update_shift_stats(self, *args):
        if self.login_time:
            current_time = datetime.now()
            login_duration = current_time - self.login_time
            work_duration = login_duration - self.total_break_time
            self.ids.shift_duration.text = str(login_duration).split(".")[0]
            self.ids.break_duration.text = str(self.total_break_time).split(".")[0]
            self.ids.work_duration.text = str(work_duration).split(".")[0]

    def save_shift_data_to_json(self):
        if not self.login_time:
            return

        session_date = self.login_time.strftime('%Y-%m-%d')
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        system_user = getpass.getuser()
        device_os = platform.system()

        new_session = {
            "login_time": self.login_time.strftime('%I:%M:%S %p'),
            "logout_time": datetime.now().strftime('%I:%M:%S %p'),
            "login_duration": str(datetime.now() - self.login_time),
            "work_duration": str(datetime.now() - self.login_time - self.total_break_time),
            "total_break_time": str(self.total_break_time),
            "breaks": self.break_log_entries,
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
                    pass

        existing_data["sessions"].append(new_session)

        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=4)

    def export_log_to_csv(self):
        if not self.break_log_entries:
            self.show_popup("Export", "No break logs to export.")
            return

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="Enter filename to save:", font_size=16))

        filename_input = TextInput(multiline=False, size_hint=(1, 0.3))
        content.add_widget(filename_input)

        def save_csv(instance):
            filename = filename_input.text.strip()
            if not filename:
                self.show_popup("Error", "Please enter a filename.")
                return

            if not filename.endswith('.csv'):
                filename += '.csv'

            try:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Start Time", "End Time", "Duration", "Reason"])
                    writer.writerows(self.break_log_entries)
                popup.dismiss()
                self.show_popup("Success", f"Break log exported to {filename}")
            except Exception as e:
                self.show_popup("Error", f"Failed to export: {str(e)}")

        content.add_widget(Button(text="Export", size_hint=(1, 0.3), on_press=save_csv))

        popup = Popup(title="Export Break Log",
                      content=content,
                      size_hint=(0.6, 0.4))
        popup.open()

    def show_summary(self):
        total_breaks = len(self.break_log_entries)
        total_break_minutes = sum(
            [float(timedelta_str.split(':')[1]) + float(timedelta_str.split(':')[2]) / 60
             for _, _, timedelta_str, _ in self.break_log_entries])

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

        for entry in self.break_log_entries:
            reason = entry[3]
            if reason in reasons:
                reasons[reason] += 1

        summary = f"Total Breaks: {total_breaks}\nTotal Break Time (approx min): {round(total_break_minutes, 2)}\n\n"
        for k, v in reasons.items():
            summary += f"{k}: {v}\n"

        self.show_popup("Daily Summary", summary)

    def verify_face_identity(self, timeout=10):
        self.stop_camera_preview()
        time.sleep(0.5)
        self.start_camera_preview()

        face_cascade = cv2.CascadeClassifier(self.resource_path('haarcascade_frontalface_default.xml'))
        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read("lbph_model.yml")
        cap = cv2.VideoCapture(0)

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
        self.show_popup("Face Authentication", "Face not matched or no face detected.")
        return False

    def capture_and_train_face(self):
        self.stop_camera_preview()
        time.sleep(0.5)
        self.start_camera_preview()

        face_cascade = cv2.CascadeClassifier(self.resource_path('haarcascade_frontalface_default.xml'))
        cap = cv2.VideoCapture(0)
        faces = []
        count = 0

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text="Registering Face", font_size=16))

        progress = ProgressBar(max=100, size_hint=(1, 0.2))
        content.add_widget(progress)

        status_label = Label(text="Capturing Face 0/100", font_size=14)
        content.add_widget(status_label)

        popup = Popup(title="Face Registration",
                      content=content,
                      size_hint=(0.6, 0.4),
                      auto_dismiss=False)
        popup.open()

        def update_capture():
            nonlocal count
            ret, frame = cap.read()
            if not ret:
                return

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected_faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in detected_faces:
                face_img = gray[y:y + h, x:x + w]
                resized = cv2.resize(face_img, (200, 200))
                faces.append(resized)
                count += 1
                status_label.text = f"Capturing Face {count}/100"
                progress.value = count

                if count >= 100:
                    cap.release()
                    popup.dismiss()

                    if len(faces) >= 10:
                        labels = [0] * len(faces)
                        recognizer = cv2.face.LBPHFaceRecognizer_create()
                        recognizer.train(faces, np.array(labels))
                        recognizer.save("lbph_model.yml")
                        self.show_popup("Success", "Face registration complete.")
                    else:
                        self.show_popup("Error", "Not enough faces captured. Try again.")
                    return

            Clock.schedule_once(lambda dt: update_capture(), 0.1)

        update_capture()

    def load_previous_breaks(self):
        self.break_log_entries.clear()
        self.total_break_time = timedelta()
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
                                self.break_log_entries.append(b)
                                self.log_break(b[0], b[1], f"{b[2]} ({b[3]})")
                                h, m, s = map(float, b[2].split(":"))
                                self.total_break_time += timedelta(hours=h, minutes=m, seconds=s)
                except json.JSONDecodeError:
                    pass

    def check_internet(self):
        while True:
            try:
                urllib.request.urlopen('http://clients3.google.com/generate_204', timeout=5)
                self.internet_was_connected = True
            except:
                if self.internet_was_connected:
                    self.internet_was_connected = False
                    Clock.schedule_once(lambda dt: self.log_crash_break())
            time.sleep(10)

    def show_login_time(self):
        if os.path.exists(CRASH_FLAG_FILE):
            self.log_crash_break()

        username = self.ids.username_input.text.strip()
        password = self.ids.password_input.text.strip()

        if username != VALID_USERNAME or password != VALID_PASSWORD:
            self.show_popup("Login Failed", "Invalid username or password.")
            return

        # Start facial verification
        if not self.verify_face_identity(timeout=10):
            self.show_popup("Face Mismatch", "Face did not match registered employee.")
            return

        # Login success
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
                        self.login_time = datetime.combine(today.date(), parsed_time)
                    else:
                        self.login_time = datetime.now()
                except Exception:
                    self.login_time = datetime.now()
        else:
            self.login_time = datetime.now()

        self.last_user_input_time = time.time()
        self.switch_to_dashboard()
        self.load_previous_breaks()
        threading.Thread(target=self.start_face_recognition_monitoring, daemon=True).start()

    def switch_to_dashboard(self):
        self.clear_widgets()

        # Main layout
        main_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)

        # Profile header
        profile_header = BoxLayout(size_hint=(1, 0.1))
        profile_header.add_widget(Label(text="Saleet Ul Hassan", font_size=18, bold=True))
        main_layout.add_widget(profile_header)

        # Content area (stats + camera)
        content_area = BoxLayout(size_hint=(1, 0.4))

        # Stats frame
        stats_frame = BoxLayout(orientation='vertical', size_hint=(0.6, 1), spacing=10)

        stats = [
            ("Shift Login Time", self.login_time.strftime('%I:%M %p')),
            ("Shift Login Duration", "00:00:00"),
            ("Shift Breaks Duration", "00:00:00"),
            ("Shift Total Work Duration", "00:00:00"),
        ]

        # Create references for updating stats
        self.shift_duration_label = None
        self.break_duration_label = None
        self.work_duration_label = None

        for text, value in stats:
            row = BoxLayout(size_hint=(1, 0.2))
            row.add_widget(Label(text=text + ":", font_size=14))
            value_label = Label(text=value, font_size=14, bold=True, color=(0.1, 0.47, 0.95, 1))
            if text == "Shift Login Duration":
                self.shift_duration_label = value_label
            elif text == "Shift Breaks Duration":
                self.break_duration_label = value_label
            elif text == "Shift Total Work Duration":
                self.work_duration_label = value_label
            row.add_widget(value_label)
            stats_frame.add_widget(row)

        content_area.add_widget(stats_frame)

        # Camera preview frame
        camera_frame = BoxLayout(orientation='vertical', size_hint=(0.4, 1), spacing=5)
        camera_frame.add_widget(Label(text="Live Camera View", font_size=14))

        camera_container = BoxLayout(size_hint=(1, 0.8))
        self.camera_preview = KivyImage()
        camera_container.add_widget(self.camera_preview)
        camera_frame.add_widget(camera_container)

        toggle_btn = Button(text="Hide Camera", size_hint=(1, 0.1))

        def toggle_camera(instance):
            if self.camera_preview.parent:
                camera_container.remove_widget(self.camera_preview)
                toggle_btn.text = "Show Camera"
            else:
                camera_container.add_widget(self.camera_preview)
                toggle_btn.text = "Hide Camera"

        toggle_btn.bind(on_press=toggle_camera)
        camera_frame.add_widget(toggle_btn)

        content_area.add_widget(camera_frame)
        main_layout.add_widget(content_area)

        # Action buttons
        action_buttons = BoxLayout(size_hint=(1, 0.1), spacing=10)
        action_buttons.add_widget(Button(text="Mark Break", on_press=lambda x: self.start_manual_break()))
        action_buttons.add_widget(Button(text="Summary", on_press=lambda x: self.show_summary()))
        action_buttons.add_widget(Button(text="Export CSV", on_press=lambda x: self.export_log_to_csv()))
        action_buttons.add_widget(Button(text="Logout", on_press=lambda x: self.on_close()))
        main_layout.add_widget(action_buttons)

        # Inactivity log
        log_frame = BoxLayout(orientation='vertical', size_hint=(1, 0.4))
        log_frame.add_widget(Label(text="Inactivity Log", font_size=16, bold=True, color=(0.1, 0.47, 0.95, 1)))

        scroll_view = ScrollView()
        self.inactivity_log_box = TextInput(readonly=True, font_size=12, background_color=(1, 1, 1, 1))
        scroll_view.add_widget(self.inactivity_log_box)
        log_frame.add_widget(scroll_view)

        main_layout.add_widget(log_frame)

        self.add_widget(main_layout)
        self.start_camera_preview()


class LoginScreen(BoxLayout):
    def __init__(self, app, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = 15
        self.padding = [50, 20]

        # Title
        self.add_widget(Label(text="Employee Login", font_size=24, size_hint=(1, 0.2)))

        # Username
        self.add_widget(Label(text="Username", font_size=16, size_hint=(1, 0.1)))
        self.ids.username_input = TextInput(multiline=False, font_size=18, size_hint=(1, 0.15))
        self.add_widget(self.ids.username_input)

        # Password
        self.add_widget(Label(text="Password", font_size=16, size_hint=(1, 0.1)))
        self.ids.password_input = TextInput(multiline=False, font_size=18, size_hint=(1, 0.15), password=True)
        self.add_widget(self.ids.password_input)

        # Login button
        login_btn = Button(text="Login", font_size=18, size_hint=(1, 0.15), background_color=(0.1, 0.6, 0.9, 1))
        # login_btn.bind(on_press=lambda x: self.app.dashboard.show_login_time())
        login_btn.bind(on_press=lambda x: self.app.show_login_time())

        self.add_widget(login_btn)

        # Register face button
        register_btn = Button(text="Register Face", font_size=16, size_hint=(1, 0.15))
        register_btn.bind(on_press=lambda x: self.app.capture_and_train_face())

        self.add_widget(register_btn)

        # Camera preview
        self.add_widget(Label(text="Camera Preview", font_size=14, size_hint=(1, 0.1)))
        camera_container = BoxLayout(size_hint=(1, 0.5))
        self.camera_preview = KivyImage()
        camera_container.add_widget(self.camera_preview)
        self.add_widget(camera_container)

        Clock.schedule_interval(self.update_camera_preview, 1 / 30)

    def update_camera_preview(self, dt):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            buf = cv2.flip(frame, 0).tobytes()
            tex = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            tex.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            # self.ids.camera_preview.texture = tex
            self.camera_preview.texture = tex


class RootWidget(BoxLayout):
    def __init__(self, app, **kwargs):
        self.app = app  # store app instance
        kwargs.pop('app', None)  # remove 'app' to avoid Kivy's error
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.login_screen = LoginScreen(app=self)
        self.add_widget(self.login_screen)

    def show_dashboard(self):
        self.clear_widgets()
        self.dashboard = EmployeeDashboard()
        self.add_widget(self.dashboard)
        self.dashboard.switch_to_dashboard()

    def capture_and_train_face(self):
        self.dashboard = EmployeeDashboard()
        self.dashboard.capture_and_train_face()


class MonitorApp(App):
    def build(self):
        self.root_widget = RootWidget(app=self)
        return self.root_widget

    def show_login_time(self):
        if hasattr(self.root_widget, "dashboard"):
            self.root_widget.dashboard.show_login_time()

    def handle_login(self, username, password):
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            self.root_widget.login_time = datetime.now()
            self.show_login_time()
        else:
            Popup(
                title="Login Failed",
                content=Label(text="Invalid credentials"),
                size_hint=(0.5, 0.3)
            ).open()

    def capture_and_train_face(self):
        if hasattr(self.root_widget, "dashboard"):
            self.root_widget.dashboard.capture_and_train_face()
        else:
            print("Dashboard not initialized yet.")

    def logout(self):
        if hasattr(self.root_widget, "dashboard"):
            self.root_widget.dashboard.on_close()

    def on_stop(self):
        if hasattr(self.root_widget, "dashboard"):
            self.root_widget.dashboard.on_close()




if __name__ == '__main__':
    MonitorApp().run()
