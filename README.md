# Google Flow Nano Banana 2 Live Desktop Generator

A streamlined, local-first Python desktop automation bot that launches Google Chrome to generate high-resolution images on Google Flow using **Nano Banana 2** with direct reference image workflows.

---

## 🚀 Quick Start (1-Click Run)

Simply double-click:
```cmd
run_live_chrome.bat
```
or run via terminal:
```powershell
& "C:\Users\Rukshan Amodya\AppData\Local\Programs\Python\Python313\python.exe" scripts/watch_automation.py
```

---

## 📁 Workspace Structure

```
FlowBot/
├── run_live_chrome.bat          # 1-Click Desktop Launcher
├── scripts/
│   ├── watch_automation.py      # Main Live Automation Runner
│   └── login.py                 # One-time Google Account Sign-In helper
├── app/
│   ├── config.py                # Bot Configurations & Path settings
│   ├── services/
│   │   ├── flow_adapter.py      # Direct DOM controller (Model & UI interactions)
│   │   ├── flow_generator.py    # Automation lifecycle & progress engine
│   │   ├── flow_selectors.py    # Google Flow DOM element selectors
│   │   ├── image_downloader.py  # High-res output downloader
│   │   └── session_manager.py   # Browser session manager
│   └── utils/
│       └── logger.py            # Structured UTF-8 console logger
├── browser_profile/             # Saved local Chrome login profile
└── generated/                   # Downloaded output images
```

---

## 🔑 One-Time Login Setup

If you need to refresh your Google session:
```powershell
python scripts/login.py
```
Sign in to your Google account in the opened window, verify Google Flow loads, and press **ENTER** in the terminal to save your session.
