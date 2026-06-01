"""
QR-code connection: display a QR code, wait for the robot to scan it and
announce itself, then connect.

Usage:
    SSID=MyWifi PASSWORD=secret python3 examples/05_qrcode.py

Optional env vars:
    IP         — override the auto-detected local IP
    PORT       — UDP listen port (default 12345)
    QR_OUTPUT  — "terminal" (default), "file", or "text"
    QR_FILE    — output path when QR_OUTPUT=file (default "qrcode.png")
"""
import os
import time
from clicbot_unofficial import ClicBot, BrainState, build_qr_content, show_qr_code, wait_for_robot


def on_battery(level):
    print(f"Battery: {round(level * 100)}%")


def on_angles(angles):
    for mid, angle in angles.items():
        print(f"  module {mid}: {angle:.1f}°")


def main() -> None:
    ssid = os.environ.get("SSID") or input("WiFi SSID: ")
    password = os.environ.get("PASSWORD") or input("WiFi password: ")
    local_ip = os.environ.get("IP") or None
    udp_port = int(os.environ.get("PORT", 12345))
    qr_mode = os.environ.get("QR_OUTPUT", "terminal")  # type: ignore[arg-type]
    qr_file = os.environ.get("QR_FILE") or None

    content = build_qr_content(ssid, password, local_ip, udp_port)
    show_qr_code(content, mode=qr_mode, file=qr_file)
    device = wait_for_robot(udp_port, timeout=60.0)

    print(f"\nRobot at {device.ip}:{device.port} — connecting...")

    bot = ClicBot()
    bot.connect(device.ip, device.port)
    print("Connected")

    bot.on_battery = on_battery
    bot.on_angles = on_angles

    bot.send_client_info()
    bot.set_brain_state(BrainState.CUSTOM)

    modules = bot.get_structure()
    print(f"Structure: {len(modules)} modules")
    bot.request_angles()

    time.sleep(30)
    bot.disconnect()


main()
