"""Structure packet parsing and angle encoding."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List

ANGLE_SCALE = 45 / 512
_RECORD_SIZE = 28


class ModuleType(IntEnum):
    BRAIN = 0
    SERVO_JOINT = 1
    DISTANCE_BAR = 2
    SERVO_WHEEL = 3


@dataclass
class LoopConnection:
    slot: int
    index: int
    iface: int


@dataclass
class RawModuleInfo:
    module_id: int
    depth: int
    port_index: int
    type: ModuleType
    position: int
    direction: int
    parallel: bool
    angle: float
    parent_id: int
    parent_port_index: int
    loop_connections: List[LoopConnection] = field(default_factory=list)
    address: str = ""


def encode_angle(degrees: float) -> int:
    return round(degrees / ANGLE_SCALE)


def parse_structure(data: bytes) -> List[RawModuleInfo]:
    root = RawModuleInfo(
        module_id=0,
        depth=0,
        port_index=0,
        type=ModuleType.BRAIN,
        position=0,
        direction=0,
        parallel=False,
        angle=0.0,
        parent_id=0,
        parent_port_index=0,
    )
    result = [root]

    offset = 0
    while offset + _RECORD_SIZE <= len(data):
        item = data[offset : offset + _RECORD_SIZE]
        offset += _RECORD_SIZE

        type_byte = item[3]
        angle_raw = struct.unpack_from("<h", item, 7)[0]

        try:
            mod_type = ModuleType(type_byte)
        except ValueError:
            mod_type = ModuleType.BRAIN

        m = RawModuleInfo(
            module_id=item[0],
            depth=item[1],
            port_index=item[2],
            type=mod_type,
            position=item[4],
            direction=item[5],
            parallel=(type_byte == 4 or item[6] == 1),
            angle=angle_raw * ANGLE_SCALE,
            parent_id=item[9],
            parent_port_index=item[10],
        )

        for slot, idx_off, iface_off in [(0, 11, 12), (1, 13, 14), (2, 15, 16), (3, 17, 18)]:
            ci_index = item[idx_off]
            if ci_index != 255 and ci_index != m.parent_id:
                m.loop_connections.append(LoopConnection(slot, ci_index, item[iface_off]))

        addr_len = (item[12] + 1) // 2
        m.address = item[13 : 13 + addr_len].hex()

        result.append(m)

    return result


_PORT_COUNTS: dict[ModuleType, int] = {
    ModuleType.BRAIN: 1,
    ModuleType.SERVO_JOINT: 4,
    ModuleType.DISTANCE_BAR: 2,
    ModuleType.SERVO_WHEEL: 1,
}


def to_mermaid(structure: List[RawModuleInfo]) -> str:
    """Return a Mermaid graph diagram string for the given module structure."""
    lines = ["graph TD"]
    for m in structure:
        ports = _PORT_COUNTS.get(m.type, 0)
        lines.append(f"    subgraph {m.type.name} {m.module_id}")
        lines.append("        direction LR")
        for i in range(ports):
            lines.append(f"        {m.module_id}_conn{i}(Port {i})")
        lines.append("    end")
        if m.module_id != 0:
            parent = structure[m.parent_id]
            parent_ports = _PORT_COUNTS.get(parent.type, 1)
            parent_port = m.parent_port_index % parent_ports
            lines.append(f"    {parent.module_id}_conn{parent_port} --> {m.module_id}_conn{m.port_index}")
    return "\n".join(lines)


def parse_angles(data: bytes) -> dict[int, float]:
    if not data or len(data) % 3 != 0:
        return {}
    result: dict[int, float] = {}
    for i in range(len(data) // 3):
        off = i * 3
        module_id = data[off]
        angle_raw = struct.unpack_from("<h", data, off + 1)[0]
        result[module_id] = angle_raw * ANGLE_SCALE
    return result
