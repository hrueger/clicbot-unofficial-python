"""TCP socket with automatic heartbeat, backed by a background thread."""

from __future__ import annotations

import socket
import struct
import threading
from typing import Callable, Optional

from ._packet import CMD, TCPPacket

_HEARTBEAT_INTERVAL = 5.0
_HEARTBEAT_MAX_MISSED = 2


class ClicBotSocket:
    def __init__(self) -> None:
        self._sock: Optional[socket.socket] = None
        self._recv_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._missed_pulses = 0

        self.on_packet: Optional[Callable[[TCPPacket], None]] = None
        self.on_close: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    def connect(self, host: str, port: int) -> None:
        self._stop_event.clear()
        self._missed_pulses = 0
        self._sock = socket.create_connection((host, port))
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        self._send_pulse()

    def disconnect(self) -> None:
        self._stop_event.set()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def send_command(self, command: int, body: bytes = b"", index: int = 0) -> None:
        if self._sock is None:
            return
        try:
            self._sock.sendall(TCPPacket(command, body, index).to_bytes())
        except Exception:
            pass

    def _send_pulse(self) -> None:
        self.send_command(CMD.TCP_HEARTBEAT)

    def _feed_pulse(self) -> None:
        self._missed_pulses = 0

    def _heartbeat_loop(self) -> None:
        while not self._stop_event.wait(_HEARTBEAT_INTERVAL):
            self._missed_pulses += 1
            if self._missed_pulses > _HEARTBEAT_MAX_MISSED:
                self.disconnect()
                if self.on_close:
                    self.on_close()
                return
            self._send_pulse()

    def _recv_loop(self) -> None:
        buf = b""
        try:
            while not self._stop_event.is_set() and self._sock:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while len(buf) >= 8:
                    body_len = struct.unpack_from("<I", buf, 4)[0]
                    frame_len = 8 + body_len
                    if len(buf) < frame_len:
                        break
                    frame, buf = buf[:frame_len], buf[frame_len:]
                    packet = TCPPacket.from_bytes(frame)
                    if packet is None:
                        continue
                    self._feed_pulse()
                    if self.on_packet:
                        self.on_packet(packet)
        except Exception as exc:
            if not self._stop_event.is_set() and self.on_error:
                self.on_error(exc)
        finally:
            if not self._stop_event.is_set() and self.on_close:
                self.on_close()
