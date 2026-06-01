"""ClicBot Python SDK — motor control and structure API."""

from ._structure import ModuleType, to_mermaid
from .clicbot import BrainState, ClicBot
from .discovery import (
    DiscoveredDevice,
    build_qr_content,
    discover_all,
    discover_first,
    discover_via_qrcode,
    show_qr_code,
    wait_for_robot,
)
from .modules import (
    BrainModule,
    ClicBotModule,
    DistanceBarModule,
    ServoJointModule,
    ServoWheelModule,
)

__all__ = [
    "ClicBot",
    "BrainState",
    "ModuleType",
    "to_mermaid",
    "ClicBotModule",
    "BrainModule",
    "ServoJointModule",
    "DistanceBarModule",
    "ServoWheelModule",
    "DiscoveredDevice",
    "discover_all",
    "discover_first",
    "discover_via_qrcode",
    "build_qr_content",
    "show_qr_code",
    "wait_for_robot",
]
