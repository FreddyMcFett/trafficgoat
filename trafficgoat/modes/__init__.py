from trafficgoat.modes.stress import StressMode
from trafficgoat.modes.scan import ScanMode
from trafficgoat.modes.mixed import MixedMode
from trafficgoat.modes.protocol import ProtocolMode
from trafficgoat.modes.stealth import StealthMode
from trafficgoat.modes.custom import CustomMode

MODES = {
    "stress": StressMode,
    "scan": ScanMode,
    "mixed": MixedMode,
    "protocol": ProtocolMode,
    "stealth": StealthMode,
    "custom": CustomMode,
}

__all__ = [
    "StressMode",
    "ScanMode",
    "MixedMode",
    "ProtocolMode",
    "StealthMode",
    "CustomMode",
    "MODES",
]
