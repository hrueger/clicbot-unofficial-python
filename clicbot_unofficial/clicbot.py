"""ClicBot — main SDK entry point."""

from __future__ import annotations

import json
import struct
import threading
from enum import IntEnum
from typing import Callable, Dict, List, Optional

from ._packet import CMD, TCPPacket
from ._socket import ClicBotSocket
from ._structure import ModuleType, RawModuleInfo, encode_angle, parse_angles, parse_structure
from .modules import (
    ClicBotModule,
    ServoJointModule,
    ServoWheelModule,
    _create_module,
)


class BrainState(IntEnum):
    """Robot brain operating mode."""

    CUSTOM = 1  # Custom / interactive control — send this to enable motion commands
    OFFICIAL = 2  # Built-in program mode
    INACTIVE_3 = 3
    PAIRING_ACCEPT = 4
    PAIRING_OR_UPDATING = 5
    INACTIVE_6 = 6
    CLEAR_CACHE = 50


class ClicBot:
    """
    ClicBot SDK.

    Typical usage::

        bot = ClicBot()
        bot.connect("192.168.x.x", 5000)
        bot.send_client_info()
        bot.set_brain_state(BrainState.CUSTOM)

        modules = bot.get_structure()
        for joint in bot.servo_joints:
            joint.rotate_to(90, speed=60)

        time.sleep(60)
        bot.disconnect()

    To react to events, assign a function to any of these attributes::

        def on_battery(level):
            print(f"Battery: {round(level * 100)}%")

        bot.on_battery = on_battery

    Available callbacks
    ~~~~~~~~~~~~~~~~~~~
    ``on_close()``                   – connection closed
    ``on_error(exc)``                – socket error
    ``on_battery(level)``            – battery level 0.0–1.0
    ``on_structure_changed(modules)``– called whenever structure updates
    ``on_angles(angles)``            – dict[module_id, float] angle update
    """

    def __init__(self) -> None:
        self._socket = ClicBotSocket()
        self._socket.on_packet = self._handle_packet
        self._socket.on_close = self._handle_close
        self._socket.on_error = self._handle_error
        self._raw_structure: List[RawModuleInfo] = []
        self._structure_waiters: List[threading.Event] = []
        self.modules: Dict[int, ClicBotModule] = {}
        self.battery_level: Optional[float] = None

        # Assign a function to receive events
        self.on_close: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        self.on_battery: Optional[Callable[[float], None]] = None
        self.on_structure_changed: Optional[Callable[[Dict[int, ClicBotModule]], None]] = None
        self.on_angles: Optional[Callable[[Dict[int, float]], None]] = None

    # ── Connection ─────────────────────────────────────────────────────────────

    def connect(self, host: str, port: int) -> None:
        """Open a TCP connection to the robot."""
        self._socket.connect(host, port)

    def disconnect(self) -> None:
        """Close the TCP connection."""
        self._socket.disconnect()

    def send_client_info(self, **overrides) -> None:
        """Send the client handshake (call once after connect)."""
        payload = {
            "jsonType": 1,
            "userId": 0,
            "userName": "tourist",
            "platform": "Python",
            "appVersion": "1.0.0",
            "brainAppVersion": "1.0",
            "reconnect": 0,
            "invite": 0,
            **overrides,
        }
        self._socket.send_command(CMD.TCP_CLIENT_INFO, json.dumps(payload).encode())

    def set_brain_state(self, state: BrainState | int) -> None:
        """Switch the robot brain mode (use BrainState.CUSTOM for motion control)."""
        self._socket.send_command(CMD.TCP_BRAIN_CONTROL_REQUEST, struct.pack("<h", int(state)))

    # ── Structure ──────────────────────────────────────────────────────────────

    def get_structure(self, timeout: float = 10.0) -> Dict[int, ClicBotModule]:
        """Request the robot's module layout and block until it's received.

        Returns a dict mapping module id → module object.
        Also populates ``bot.servo_joints``, ``bot.servo_wheels``, etc.
        """
        ready = threading.Event()
        self._structure_waiters.append(ready)
        self._socket.send_command(CMD.TCP_STRUCTURE_REQUEST)
        if not ready.wait(timeout):
            raise TimeoutError(f"No structure reply from robot within {timeout}s")
        return self.modules

    def set_structure_watchdog(self, enabled: bool) -> None:
        """Enable or disable continuous structure change notifications."""
        self._socket.send_command(CMD.TCP_STRUCTURE_OBSERVE_REQUEST, bytes([1 if enabled else 0]))

    def request_angles(self, module_ids: Optional[List[int]] = None) -> None:
        """Request current joint angles (fires ``on_angles`` when received)."""
        if module_ids is None:
            module_ids = [m.module_id for m in self._raw_structure if m.type == ModuleType.SERVO_JOINT]
        valid = [i for i in module_ids if 0 < i <= 255]
        if valid:
            self._socket.send_command(CMD.TCP_ANGLES_REQUEST, bytes(valid))

    # ── Structure accessors ────────────────────────────────────────────────────

    @property
    def root(self) -> Optional[ClicBotModule]:
        """Brain module (id=0), available after ``get_structure()``."""
        return self.modules.get(0)

    @property
    def servo_joints(self) -> List[ServoJointModule]:
        """All servo joint modules in the current structure."""
        return [m for m in self.modules.values() if isinstance(m, ServoJointModule)]

    @property
    def servo_wheels(self) -> List[ServoWheelModule]:
        """All servo wheel modules in the current structure."""
        return [m for m in self.modules.values() if isinstance(m, ServoWheelModule)]

    def get_module(self, module_id: int) -> Optional[ClicBotModule]:
        """Look up any module by id."""
        return self.modules.get(module_id)

    # ── Motor control ──────────────────────────────────────────────────────────

    def rotate_start(self, module_id: int, forward: bool, speed: int) -> None:
        """Start continuous rotation on a single module."""
        speed = max(0, min(100, speed))
        self._socket.send_command(
            CMD.TCP_ROTATE_START_REQUEST,
            bytes([module_id & 0xFF, 1 if forward else 0, speed]),
        )

    def rotate_start_many(
        self,
        targets: List[Dict],  # [{"module_id": int, "forward": bool, "speed": int}]
    ) -> None:
        """Start continuous rotation on multiple modules at once."""
        valid = [t for t in targets if 0 < t["module_id"] <= 255]
        if not valid:
            return
        body = bytearray()
        for t in valid:
            body += bytes([t["module_id"] & 0xFF, 1 if t["forward"] else 0, max(0, min(100, t["speed"]))])
        self._socket.send_command(CMD.TCP_ROTATE_START_REQUEST, bytes(body))

    def rotate_stop(self) -> None:
        """Stop continuous rotation on all modules."""
        self._socket.send_command(CMD.TCP_ROTATE_STOP_REQUEST)

    def rotate_to(self, module_id: int, angle: float, speed: int = 50) -> None:
        """Move a servo joint to an absolute angle (degrees)."""
        speed = max(0, min(100, speed))
        body = struct.pack("<BBBBh", module_id & 0xFF, 0x02, speed, 0x00, encode_angle(angle))
        self._socket.send_command(CMD.TCP_SERVO_MOVE_REQUEST, body)

    def rotate_to_many(
        self,
        targets: List[Dict],  # [{"module_id": int, "angle": float, "speed": int?}]
    ) -> None:
        """Move multiple servo joints to absolute angles simultaneously."""
        valid = [t for t in targets if 0 < t["module_id"] <= 255]
        if not valid:
            return
        body = bytearray()
        for t in valid:
            speed = max(0, min(100, t.get("speed", 50)))
            body += struct.pack("<BBBBh", t["module_id"] & 0xFF, 0x02, speed, 0x00, encode_angle(t["angle"]))
        self._socket.send_command(CMD.TCP_SERVO_MOVE_REQUEST, bytes(body))

    def lock(self, module_id: int) -> None:
        """Lock a module (hold its current position)."""
        self._socket.send_command(CMD.TCP_MODULE_LOCK_REQUEST, bytes([module_id & 0xFF, 1]))

    def unlock(self, module_id: int) -> None:
        """Unlock a module (allow free movement)."""
        self._socket.send_command(CMD.TCP_MODULE_LOCK_REQUEST, bytes([module_id & 0xFF, 0]))

    def lock_many(self, module_ids: List[int], locked: bool = True) -> None:
        """Lock or unlock multiple modules at once."""
        valid = [i for i in module_ids if 0 < i <= 255]
        if not valid:
            return
        body = bytearray()
        for i in valid:
            body += bytes([i & 0xFF, 1 if locked else 0])
        self._socket.send_command(CMD.TCP_MODULE_LOCK_REQUEST, bytes(body))

    def lock_all(self, locked: bool = True) -> None:
        """Lock or unlock all servo and wheel modules in the current structure."""
        ids = [m.module_id for m in self._raw_structure if m.module_id > 0 and m.type != ModuleType.DISTANCE_BAR]
        self.lock_many(ids, locked)

    def full_stop(self, lock: bool = False) -> None:
        """Emergency stop all modules."""
        self._socket.send_command(CMD.TCP_FULL_STOP_REQUEST, bytes([1 if lock else 0, 0]))

    # ── Packet dispatch ────────────────────────────────────────────────────────

    def _handle_packet(self, packet: TCPPacket) -> None:
        cmd, body = packet.command, packet.body

        if cmd == CMD.TCP_BATTERY_LEVEL:
            if body:
                self.battery_level = body[0] / 100
                if self.on_battery:
                    self.on_battery(self.battery_level)

        elif cmd == CMD.TCP_STRUCTURE_RESPONSE:
            self._raw_structure = parse_structure(body)
            self._rebuild_modules()
            for w in self._structure_waiters:
                w.set()
            self._structure_waiters.clear()
            if self.on_structure_changed:
                self.on_structure_changed(self.modules)

        elif cmd == CMD.TCP_ANGLES_RESPONSE:
            angles = parse_angles(body)
            for mid, angle in angles.items():
                m = self.modules.get(mid)
                if isinstance(m, ServoJointModule):
                    m._update_angle(angle)
            if self.on_angles:
                self.on_angles(angles)

    def _handle_close(self) -> None:
        if self.on_close:
            self.on_close()

    def _handle_error(self, exc: Exception) -> None:
        if self.on_error:
            self.on_error(exc)

    def _rebuild_modules(self) -> None:
        next_modules: Dict[int, ClicBotModule] = {}
        for raw in self._raw_structure:
            existing = self.modules.get(raw.module_id)
            if existing is not None:
                existing._update(raw)
                next_modules[raw.module_id] = existing
            else:
                next_modules[raw.module_id] = _create_module(raw)

        for m in next_modules.values():
            m._bind(self)
            m.children = []
            m.parent = None

        for m in next_modules.values():
            if m.id != 0:
                parent = next_modules.get(m.parent_id)
                if parent is not None:
                    m.parent = parent
                    parent.children.append(m)

        self.modules = next_modules
