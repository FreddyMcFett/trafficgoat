from trafficgoat.modes.stress import StressMode
from trafficgoat.modes.scan import ScanMode
from trafficgoat.modes.mixed import MixedMode
from trafficgoat.modes.protocol import ProtocolMode
from trafficgoat.modes.stealth import StealthMode
from trafficgoat.modes.custom import CustomMode
from trafficgoat.modes.auto import AutoMode

MODES = {
    "stress": StressMode,
    "scan": ScanMode,
    "mixed": MixedMode,
    "protocol": ProtocolMode,
    "stealth": StealthMode,
    "custom": CustomMode,
    "auto": AutoMode,
}

__all__ = [
    "StressMode",
    "ScanMode",
    "MixedMode",
    "ProtocolMode",
    "StealthMode",
    "CustomMode",
    "AutoMode",
    "MODES",
]
