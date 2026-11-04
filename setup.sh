#!/bin/bash
# Project ZRN — Setup script for Raspberry Pi OS
# ByteBell Software
# Usage: bash setup.sh

set -e
echo "=== Project ZRN Setup ==="

# 1. System updates + dependencies
sudo apt-get update -q
sudo apt-get install -y python3-pip python3-venv chromium-browser \
    unclutter xdotool libgpiod3

# 2. Enable SPI (for the MFRC522)
# On recent Raspberry Pi OS versions (Bookworm/Trixie+), /boot/config.txt is
# no longer the real boot config file — it moved to /boot/firmware/config.txt.
# Older versions still use /boot/config.txt.
if [ -f /boot/firmware/config.txt ]; then
    BOOT_CONFIG="/boot/firmware/config.txt"
else
    BOOT_CONFIG="/boot/config.txt"
fi
if ! grep -q "^dtparam=spi=on" "$BOOT_CONFIG"; then
    echo "dtparam=spi=on" | sudo tee -a "$BOOT_CONFIG" > /dev/null
    echo "[!] SPI enabled in $BOOT_CONFIG — reboot required after setup"
fi

# 3. Project location
# setup.sh assumes it's already being run from the cloned/copied project
# directory on the Pi (see README: git clone + cd + setup.sh, or scp/rsync
# if git clone isn't possible on the Pi itself).
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "--- Installing from: $INSTALL_DIR"

# 4. Python venv + packages
cd "$INSTALL_DIR"
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 5. Create config if it doesn't exist yet
if [ ! -f config.yaml ]; then
    cp config.yaml.example config.yaml
    echo "[!] Fill in config.yaml with your school and zermelo_token!"
fi

# 6. Install the systemd service
# zrn-terminal.service assumes user "pi" and /home/pi/project-zrn — replace
# the path and username with the real install location/user before
# installing the service (this can be a different user, e.g. with a custom
# username set via Raspberry Pi Imager).
sed -e "s|/home/pi/project-zrn|$INSTALL_DIR|g" -e "s|^User=pi$|User=$(whoami)|" \
    zrn-terminal.service | sudo tee /etc/systemd/system/zrn-terminal.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable zrn-terminal
sudo systemctl start zrn-terminal

# 7. Chromium kiosk autostart
# Restart loop: if Chromium closes for any reason (crash, or a user managing
# to close the window), the kiosk is back on screen within ~2s instead of
# leaving the Pi on a bare desktop. --disable-dev-tools blocks F12/
# Ctrl+Shift+I (without it the whole lockdown is pointless — devtools let
# anyone navigate anywhere). flock ensures only one loop ever runs at a
# time — in practice the autostart hook on this Pi sometimes fired twice,
# resulting in two Chromium instances that crashed each other (blank screen).
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/zrn-kiosk.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=ZRN Kiosk
Exec=bash -c 'exec 200>/tmp/zrn-kiosk.lock; flock -n 200 || exit 0; sleep 5 && unclutter -idle 0 & CHROMIUM_BIN=$(command -v chromium-browser || command -v chromium); while true; do "$CHROMIUM_BIN" --kiosk --noerrdialogs --disable-infobars --disable-dev-tools --disable-pinch --overscroll-history-navigation=0 --disable-session-crashed-bubble --disable-translate --disable-features=TranslateUI --password-store=basic --incognito --app=http://localhost:5000; sleep 2; done'
X-GNOME-Autostart-enabled=true
DESKTOP

# 7b. Disable the translate bar via a Chromium enterprise policy
# --disable-features=TranslateUI no longer works on newer Chromium builds.
# The official policy route is reliable and prevents the clickable
# "Dutch/English" translate bar (a breakout/distraction point outside the
# kiosk app itself).
sudo mkdir -p /etc/chromium/policies/managed
echo '{"TranslateEnabled": false}' | sudo tee /etc/chromium/policies/managed/zrn-policy.json > /dev/null

# 8. Window manager (labwc) kiosk lockdown
# By default, labwc ships a bunch of key combos that break out of the kiosk:
# open a terminal (Ctrl+Alt+T), shut down the Pi (Ctrl+Alt+Delete), open a
# reboot/installer menu (Ctrl+Alt+Space), open network/Bluetooth menus,
# lock the screen, open a run-command dialog (Alt+F2), open the start menu
# (Super), and more. For a school kiosk each of those is a breakout route.
#
# Important: labwc MERGES the system-wide /etc/xdg/labwc/rc.xml with this
# user rc.xml rather than fully replacing it — an empty <keyboard> section
# does NOT remove the system bindings. Each dangerous key must therefore be
# explicitly redefined here with an empty (no-op) action to override it.
LABWC_DIR="$HOME/.config/labwc"
mkdir -p "$LABWC_DIR"
cat > "$LABWC_DIR/rc.xml" << 'LABWC'
<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <theme>
    <name>PiXtrix</name>
    <cornerRadius>0</cornerRadius>
    <keepBorder>no</keepBorder>
  </theme>
  <keyboard>
    <!-- Each dangerous combo from the system-wide /etc/xdg/labwc/rc.xml is
         explicitly overridden here with an empty (no-op) action. -->
    <keybind key="C-A-t"></keybind>          <!-- terminal -->
    <keybind key="C-A-Delete"></keybind>     <!-- shutdown -->
    <keybind key="C-A-space"></keybind>      <!-- reboot/installer menu -->
    <keybind key="C-A-w"></keybind>          <!-- network menu -->
    <keybind key="C-A-b"></keybind>          <!-- bluetooth menu -->
    <keybind key="C-A-l"></keybind>          <!-- screen lock -->
    <keybind key="A-F2"></keybind>           <!-- run-command dialog -->
    <keybind key="Super_L" onRelease="yes"></keybind> <!-- start menu -->
    <keybind key="XF86PowerOff" onRelease="yes"></keybind>
  </keyboard>
  <mouse>
    <context name="All">
    </context>
  </mouse>
</openbox_config>
LABWC

# 8b. Disable the taskbar and desktop icons
# The system-wide /etc/xdg/labwc/autostart launches wf-panel-pi (taskbar
# with a menu + terminal shortcut) and pcmanfm-pi (desktop icons, including
# a right-click "open terminal here") by default — both a direct breakout
# route that the rc.xml lockdown above doesn't cover (it only blocks key
# combos, not clickable UI). A minimal user-level autostart overrides this
# and only starts what the kiosk needs: kanshi (display config) and
# lxsession-xdg-autostart (needed to run our own
# ~/.config/autostart/zrn-kiosk.desktop).
cat > "$LABWC_DIR/autostart" << 'AUTOSTART'
/usr/bin/kanshi &
/usr/bin/lxsession-xdg-autostart
AUTOSTART

# 9. Disable VT switching (Ctrl+Alt+F1..F7)
# Prevents switching to a text console outside the kiosk.
#
# NAutoVTs=1/ReserveVT=0 only stops systemd-logind from spawning a login
# prompt (getty) on the other VTs — it does NOT block the raw Ctrl+Alt+Fn
# keypress itself, which is handled by the kernel console keyboard driver.
# Confirmed on-device: with only this logind.conf change, Ctrl+Alt+F2 still
# switched away from the kiosk (to a blank console). The actual fix is to
# void those key combos in the console keymap directly.
sudo mkdir -p /etc/systemd/logind.conf.d
cat << 'LOGIND' | sudo tee /etc/systemd/logind.conf.d/zrn-kiosk-novtswitch.conf > /dev/null
[Login]
NAutoVTs=1
ReserveVT=0
LOGIND
sudo systemctl restart systemd-logind || true

# Void Ctrl+Alt+F1..F7 (keycodes 59-65) in the console keymap. loadkeys
# needs a real console device, not an SSH session, hence -C /dev/tty1.
sudo mkdir -p /etc/console-setup/zrn
cat << 'KEYMAP' | sudo tee /etc/console-setup/zrn/novtswitch.keymap > /dev/null
control alt keycode 59 = VoidSymbol
control alt keycode 60 = VoidSymbol
control alt keycode 61 = VoidSymbol
control alt keycode 62 = VoidSymbol
control alt keycode 63 = VoidSymbol
control alt keycode 64 = VoidSymbol
control alt keycode 65 = VoidSymbol
KEYMAP
sudo loadkeys -C /dev/tty1 /etc/console-setup/zrn/novtswitch.keymap

# Persist across reboots: the default keymap gets reloaded at boot by
# console-setup, so our override needs to run again after that, before a
# getty can grab tty1.
cat << 'UNIT' | sudo tee /etc/systemd/system/zrn-novtswitch.service > /dev/null
[Unit]
Description=ZRN kiosk — disable Ctrl+Alt+F1..F7 VT switching
After=systemd-vconsole-setup.service console-setup.service
Before=getty@tty1.service

[Service]
Type=oneshot
ExecStart=/usr/bin/loadkeys -C /dev/tty1 /etc/console-setup/zrn/novtswitch.keymap
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable zrn-novtswitch.service

echo ""
echo "=== Setup complete! ==="
echo "Fill in $INSTALL_DIR/config.yaml and reboot the Pi."
echo "[!] After the reboot, physically test that Ctrl+Alt+T, Ctrl+Alt+Delete and Ctrl+Alt+F2 are truly blocked."
