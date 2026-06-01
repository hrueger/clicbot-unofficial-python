"""ClicBot Python SDK — motor control and structure API."""
from .clicbot import BrainState, ClicBot
from .discovery import DiscoveredDevice, discover_all, discover_first, discover_via_qrcode, build_qr_content, show_qr_code, wait_for_robot
from .modules import (
    BrainModule,
    ClicBotModule,
    DistanceBarModule,
    ServoJointModule,
    ServoWheelModule,
)
from ._structure import ModuleType, to_mermaid

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
