"""UDP discovery — find ClicBot robots on the local network."""

from __future__ import annotations

import json
import socket
import struct
import time
from dataclasses import dataclass
from typing import List, Literal, Optional

_DISCOVERY_PORT = 9633
_UDP_DISCOVER_REQUEST = 666
_UDP_DISCOVER_RESPONSE = 667
_SEND_INTERVAL = 1.0
_RECV_TIMEOUT = 0.1


@dataclass
class DiscoveredDevice:
    ip: str
    port: int
    name: str
    mode: int
    invite: int

    def __repr__(self) -> str:
        return f"<DiscoveredDevice name={self.name!r} ip={self.ip} port={self.port}>"


def _build_search_packet() -> bytes:
    # [type: u16 LE][bodyLen: u16 LE][total: u16 LE][page: u16 LE][index: u16 LE]
    return struct.pack("<HHHHH", _UDP_DISCOVER_REQUEST, 0, 1, 1, 0)


def _parse_response(data: bytes) -> Optional[DiscoveredDevice]:
    if len(data) < 10:
        return None
    pkt_type, body_len = struct.unpack_from("<HH", data)
    if pkt_type != _UDP_DISCOVER_RESPONSE or len(data) < 10 + body_len:
        return None
    try:
        payload = json.loads(data[10 : 10 + body_len].decode())
        return DiscoveredDevice(
            ip=payload["IP"],
            port=payload["Port"],
            name=payload["name"],
            mode=payload["brain_state"],
            invite=payload["invite"],
        )
    except Exception:
        return None


def discover_all(timeout: float = 3.0, interval: float = 1.0) -> List[DiscoveredDevice]:
    """Collect all devices that respond within *timeout* seconds."""
    devices: List[DiscoveredDevice] = []
    seen: set[str] = set()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(_RECV_TIMEOUT)
        sock.bind(("0.0.0.0", 0))

        deadline = time.monotonic() + timeout
        last_send = 0.0

        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_send >= interval:
                sock.sendto(_build_search_packet(), ("255.255.255.255", _DISCOVERY_PORT))
                last_send = now
            try:
                data, _ = sock.recvfrom(4096)
                device = _parse_response(data)
                if device:
                    key = f"{device.ip}:{device.port}"
                    if key not in seen:
                        seen.add(key)
                        devices.append(device)
            except (socket.timeout, TimeoutError):
                pass

    return devices


def discover_first(timeout: float = 5.0) -> DiscoveredDevice:
    """Return the first device that responds, or raise TimeoutError."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(_RECV_TIMEOUT)
        sock.bind(("0.0.0.0", 0))

        deadline = time.monotonic() + timeout
        last_send = 0.0

        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_send >= _SEND_INTERVAL:
                sock.sendto(_build_search_packet(), ("255.255.255.255", _DISCOVERY_PORT))
                last_send = now
            try:
                data, _ = sock.recvfrom(4096)
                device = _parse_response(data)
                if device:
                    return device
            except (socket.timeout, TimeoutError):
                pass

    raise TimeoutError(f"No robot found within {timeout}s")


# ── QR-code connection ─────────────────────────────────────────────────────────


def _get_local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def build_qr_content(
    ssid: str,
    password: str,
    local_ip: Optional[str] = None,
    udp_port: int = 12345,
) -> str:
    """Build the WiFi config URI that encodes credentials and UDP return address."""
    return f"WIFI:T:WPA;P:{password};S:{ssid};IP:{local_ip or _get_local_ip()};Port:{udp_port}"


def show_qr_code(
    content: str,
    mode: Literal["terminal", "file", "text"] = "terminal",
    file: Optional[str] = None,
) -> None:
    """Display or save a QR code from a pre-built content string.

    Args:
        content: The WiFi config URI from build_qr_content().
        mode:    "terminal" — print ASCII art to stdout (requires qrcode package).
                 "file"     — save as PNG to *file* (requires qrcode + Pillow).
                 "text"     — print the raw URI string only.
        file:    Output path for PNG when mode="file" (default "qrcode.png").
    """
    if mode == "text":
        print(content)
    elif mode == "file":
        try:
            import qrcode as _qr  # type: ignore[import]
        except ImportError as exc:
            raise ImportError('pip install "clicbot-unofficial[png]"  # or: pip install "qrcode[pil]"') from exc
        path = file or "qrcode.png"
        _qr.make(content).save(path)
        print(f"QR code saved to {path}")
    else:
        try:
            import qrcode as _qr  # type: ignore[import]
        except ImportError as exc:
            raise ImportError("pip install qrcode") from exc
        qr = _qr.QRCode()
        qr.add_data(content)
        qr.make(fit=True)
        print("Hold this QR code in front of the robot's camera:\n")
        qr.print_ascii(invert=True)


def wait_for_robot(udp_port: int = 12345, timeout: float = 60.0) -> DiscoveredDevice:
    """Listen on *udp_port* for the robot's UDP announcement and return its address."""
    print(f"\nListening for robot on port {udp_port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(_RECV_TIMEOUT)
        sock.bind(("0.0.0.0", udp_port))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, addr = sock.recvfrom(4096)
                try:
                    payload = json.loads(data.decode())
                    return DiscoveredDevice(
                        ip=payload.get("IP", addr[0]),
                        port=payload.get("Port", 9632),
                        name=payload.get("name", ""),
                        mode=payload.get("brain_state", 0),
                        invite=payload.get("invite", 0),
                    )
                except Exception:
                    return DiscoveredDevice(ip=addr[0], port=9632, name="", mode=0, invite=0)
            except (socket.timeout, TimeoutError):
                pass
    raise TimeoutError(f"No robot connected within {timeout}s")


def discover_via_qrcode(
    ssid: str,
    password: str,
    local_ip: Optional[str] = None,
    udp_port: int = 12345,
    timeout: float = 60.0,
) -> DiscoveredDevice:
    """Convenience: build QR content, show it in the terminal, then wait for the robot.

    For custom output (file/text) call build_qr_content(), show_qr_code(), and
    wait_for_robot() separately.
    """
    content = build_qr_content(ssid, password, local_ip, udp_port)
    show_qr_code(content)
    return wait_for_robot(udp_port, timeout)
