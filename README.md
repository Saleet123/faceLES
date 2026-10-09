# FaceLES - Face Login & Attendance System

**FaceLES** is a desktop application that combines facial recognition and user activity monitoring to manage employee attendance, detect idle time, and generate break logs in real-time.

---

## ✨ Features

- 👤 **Face Recognition Login**
  - Uses OpenCV LBPH face recognizer
  - Matches face against registered dataset

- ⏰ **Real-time Shift Tracking**
  - Tracks login time, break durations, work duration, etc.
  
- ✉ **Break Monitoring & Auto Detection**
  - Manual break types: Prayer, Tea, Meeting, Lunch, etc.
  - Auto breaks triggered by:
    - Absence from screen
    - Inactivity (keyboard + mouse)
    - Crash detection (network loss or unexpected termination)

- ⚡ **Live Camera Preview**
  - Display your face as you work

- 📊 **Daily Summary & Export**
  - View all breaks with type and time
  - Export logs to CSV

---

## 📆 Installation & Setup

### Requirements
- Python 3.10+
- OpenCV with `opencv-contrib-python`
- PIL, Tkinter, Numpy, etc.

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Register your face
```bash
python main.py
# Then click "Register Face" and follow on-screen prompts.
```

### 3. Run the App
```bash
python main.py
```

---

## 🌟 Building Executable

### macOS (.app)
```bash
pyinstaller --windowed --name FaceLES main.py \
  --add-data "haarcascade_frontalface_default.xml:." \
  --icon=face-unlock.icns --osx-bundle-identifier com.saleet.faceles
```

Make sure to:
- Add `NSCameraUsageDescription` in `Info.plist`
- Code-sign the app with proper entitlements for camera access

### Windows (.exe)
You **must build on a Windows machine**:
```bash
pyinstaller --noconsole --onefile main.py
```

---

## 🔗 Directory Structure
```
FaceLES/
├── main.py
├── lbph_model.yml
├── label_map.txt
├── haarcascade_frontalface_default.xml
├── profile_pic.jpg
├── attendance_logs/
├── README.md
├── requirements.txt
├── .gitignore
├── face-unlock.icns
└── FaceLES.spec
```

---

## 🚫 Permissions & Camera Access
- Ensure Info.plist has `NSCameraUsageDescription`
- App must be signed on macOS to access camera in bundled form

---

## 📢 Contributing
Want to add new break types, improve UI, or integrate notifications? PRs are welcome!

---

## 🚀 Author
**Saleet Ul Hassan**  
Crafted with purpose and precision.

