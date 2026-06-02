"""TCP packet framing and command constants."""

from __future__ import annotations

import struct


class CMD:
    # Connection
    TCP_CLIENT_INFO = 9

    # Structure observe
    TCP_STRUCTURE_OBSERVE_REQUEST = 100
    TCP_STRUCTURE_OBSERVE_RESPONSE = 101

    # Brain control
    TCP_BRAIN_CONTROL_REQUEST = 103
    TCP_BRAIN_CONTROL_RESPONSE = 104

    # Heartbeat
    TCP_HEARTBEAT = 995

    # Module tree structure
    TCP_STRUCTURE_REQUEST = 1000
    TCP_STRUCTURE_RESPONSE = 1001

    # Joint angles
    TCP_ANGLES_REQUEST = 1002
    TCP_ANGLES_RESPONSE = 1003

    # Continuous rotation
    TCP_ROTATE_START_REQUEST = 1004
    TCP_ROTATE_START_RESPONSE = 1005
    TCP_ROTATE_STOP_REQUEST = 1006
    TCP_ROTATE_STOP_RESPONSE = 1007

    # Absolute servo positioning
    TCP_SERVO_MOVE_REQUEST = 1008
    TCP_SERVO_MOVE_RESPONSE = 1009

    # Push-rotate mode (joint control by hand)
    TCP_PUSH_ROTATE_REQUEST = 1010
    TCP_PUSH_ROTATE_RESPONSE = 1011

    # Module lock / unlock
    TCP_MODULE_LOCK_REQUEST = 1016
    TCP_MODULE_LOCK_RESPONSE = 1017

    # Emergency stop
    TCP_FULL_STOP_REQUEST = 1020
    TCP_FULL_STOP_RESPONSE = 1021

    # Battery level (pushed by robot)
    TCP_BATTERY_LEVEL = 1031


class TCPPacket:
    """8-byte-header TCP frame: [cmd: u16 LE][index: u16 LE][bodyLen: u32 LE][body]."""

    __slots__ = ("command", "index", "body")

    def __init__(self, command: int, body: bytes = b"", index: int = 0) -> None:
        self.command = command
        self.index = index
        self.body = body

    def to_bytes(self) -> bytes:
        return struct.pack("<HHI", self.command, self.index, len(self.body)) + self.body

    @classmethod
    def from_bytes(cls, data: bytes) -> "TCPPacket | None":
        if len(data) < 8:
            return None
        command, index, body_len = struct.unpack_from("<HHI", data)
        if len(data) < 8 + body_len:
            return None
        return cls(command, data[8 : 8 + body_len], index)
