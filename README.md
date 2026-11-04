# Project ZRN — Schedule Terminal

**ByteBell Software** | C&C Project — Willem van Oranje College Waalwijk

A fixed NFC terminal that shows a student's schedule via the Zermelo API.
Students tap their school card or type their student number on a physical
keyboard/NumPad. The final product has **no mouse and no touchscreen** — the
entire UI is keyboard-driven.

## Hardware
- Raspberry Pi 3
- MFRC522 NFC reader (SPI)
- Monitor via HDMI
- USB keyboard / NumPad (required — the UI has no clickable elements)

## Project structure
```
zrn/
├── api/
│   └── zermelo.py        # Zermelo API client
├── nfc/
│   ├── reader.py         # NFC UID reading
│   └── mapping.py        # UID -> student number (SQLite)
├── ui/
│   ├── templates/
│   │   └── index.html    # Kiosk UI
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── utils/
│   └── config.py         # Configuration loading
├── app.py                # Flask server (main app)
└── config.yaml            # School settings (API token, school name)
```

## Installing on a Raspberry Pi
```bash
git clone https://github.com/Hackercat-git/ZRN.git project-zrn
cd project-zrn
bash setup.sh
```
The repo is private, so cloning on the Pi requires GitHub credentials (or an
SSH deploy key). If that doesn't work, copy the folder over instead:
```bash
scp -r code/ pi@<pi-ip>:/home/pi/project-zrn
ssh pi@<pi-ip>
cd /home/pi/project-zrn
bash setup.sh
```

## Configuration
Copy `config.yaml.example` to `config.yaml` and fill in:
- `school`: your Zermelo school name (e.g. `wvoo`)
- `zermelo_token`: API token from Zermelo — see below

### Getting a Zermelo token
1. Log in on your school's Zermelo portal (e.g. `https://wvoo.zportal.nl/app/`)
2. Settings -> Connections -> generate a pairing code
3. Exchange it for an access token:
   `POST https://{school}.zportal.nl/api/v3/oauth/token?grant_type=authorization_code&code=<pairing code>`
4. A personal token only grants access to your own schedule. A school-wide
   kiosk (showing arbitrary students) needs an admin/integration token from
   the school's IT department.

## Known limitations
- **NFC hardware**: the `mfrc522` Python library must be installed *and* a
  physical MFRC522 reader wired up for `reader.py` to work. If the library
  is present but no reader is connected, scans will time out after 15s
  instead of falling back to a mock UID — manual entry via the keyboard
  still works in that case.
- **UID -> student number mapping**: students currently register themselves
  on first scan (enrollment flow). A school-provided export would be more
  reliable and is preferred long-term.

## Powered by ByteBell Software
