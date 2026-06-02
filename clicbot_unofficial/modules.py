"""ClicBot module classes — the structure API."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ._structure import ModuleType, RawModuleInfo

if TYPE_CHECKING:
    from .clicbot import ClicBot


class ClicBotModule:
    """Base class for all physical modules in a ClicBot assembly."""

    def __init__(self, raw: RawModuleInfo) -> None:
        self.id: int = raw.module_id
        self.type: ModuleType = raw.type
        self.depth: int = raw.depth
        self.port_index: int = raw.port_index
        self.parent_id: int = raw.parent_id
        self.parent_port_index: int = raw.parent_port_index
        self.position: int = raw.position
        self.direction: int = raw.direction
        self.parallel: bool = raw.parallel
        self.address: str = raw.address
        self.children: List["ClicBotModule"] = []
        self.parent: Optional["ClicBotModule"] = None
        self._bot: Optional["ClicBot"] = None

    # ── Internal ───────────────────────────────────────────────────────────────

    def _bind(self, bot: "ClicBot") -> None:
        self._bot = bot

    def _update(self, raw: RawModuleInfo) -> None:
        self.depth = raw.depth
        self.port_index = raw.port_index
        self.parent_id = raw.parent_id
        self.parent_port_index = raw.parent_port_index
        self.position = raw.position
        self.direction = raw.direction
        self.parallel = raw.parallel
        self.address = raw.address

    @property
    def _cmd(self) -> "ClicBot":
        if self._bot is None:
            raise RuntimeError(f"Module {self.id} is not bound to a bot — call request_structure() first")
        return self._bot

    # ── Shared controls ────────────────────────────────────────────────────────

    def lock(self) -> None:
        """Lock this module (hold position)."""
        self._cmd.lock(self.id)

    def unlock(self) -> None:
        """Unlock this module (free movement)."""
        self._cmd.unlock(self.id)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id} depth={self.depth}>"


class BrainModule(ClicBotModule):
    """The robot brain (root module, id=0)."""


class ServoJointModule(ClicBotModule):
    """A servo joint that can rotate to absolute angles."""

    def __init__(self, raw: RawModuleInfo) -> None:
        super().__init__(raw)
        self.angle: float = raw.angle

    def _update(self, raw: RawModuleInfo) -> None:
        super()._update(raw)
        self.angle = raw.angle

    def _update_angle(self, angle: float) -> None:
        self.angle = angle

    def rotate_to(self, angle: float, speed: int = 50) -> None:
        """Move to an absolute angle (degrees)."""
        self._cmd.rotate_to(self.id, angle, speed)

    def rotate_start(self, forward: bool, speed: int) -> None:
        """Start continuous rotation."""
        self._cmd.rotate_start(self.id, forward, speed)

    def rotate_stop(self) -> None:
        """Stop this joint's rotation (sends rotateStart with speed=0)."""
        self._cmd.rotate_start(self.id, True, 0)

    def set_push_rotate(self, enabled: bool) -> None:
        """Enable or disable push-rotate mode for this joint."""
        self._cmd.set_push_rotate(self.id, enabled)


class DistanceBarModule(ClicBotModule):
    """A passive distance-bar connector module."""


class ServoWheelModule(ClicBotModule):
    """A servo wheel module (continuous rotation only)."""

    def rotate_start(self, forward: bool, speed: int) -> None:
        """Start continuous rotation."""
        self._cmd.rotate_start(self.id, forward, speed)

    def rotate_stop(self) -> None:
        """Stop this wheel's rotation."""
        self._cmd.rotate_start(self.id, True, 0)


def _create_module(raw: RawModuleInfo) -> ClicBotModule:
    if raw.type == ModuleType.BRAIN:
        return BrainModule(raw)
    if raw.type == ModuleType.SERVO_JOINT:
        return ServoJointModule(raw)
    if raw.type == ModuleType.DISTANCE_BAR:
        return DistanceBarModule(raw)
    if raw.type == ModuleType.SERVO_WHEEL:
        return ServoWheelModule(raw)
    return ClicBotModule(raw)
