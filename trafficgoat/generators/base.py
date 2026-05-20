"""Base generator class for all traffic generators."""

import threading
import time
from abc import ABC, abstractmethod

from trafficgoat.config import GeneratorConfig
from trafficgoat.stats import StatsCollector


class BaseGenerator(ABC):
    """Abstract base class for traffic generators.

    Subclasses must implement `generate()` which runs the packet generation loop.
    """

    name: str = "base"

    def __init__(self, config: GeneratorConfig, stats: StatsCollector, dry_run: bool = False):
        self.config = config
        self.stats = stats
        self.dry_run = dry_run
        self.target = config.target
        self.ports = config.ports
        self.rate = config.rate
        self.duration = config.duration
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._delay = 1.0 / max(self.rate, 1)

    @abstractmethod
    def generate(self):
        """Main generation loop. Must check self._stop_event.is_set() regularly."""
        ...

    def start(self):
        """Start the generator in a background thread."""
        self._stop_event.clear()
        self.stats.register_generator(self.name)
        self.stats.log(f"{self.name}: Starting (target={self.target}, rate={self.rate} pps, duration={self.duration}s)")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        try:
            self.generate()
        except Exception as e:
            self.stats.log(f"{self.name}: Error - {e}")
            self.stats.update(self.name, errors=1)
        finally:
            self.stats.log(f"{self.name}: Stopped")

    def signal_stop(self):
        """Mark this generator for shutdown without joining its thread."""
        self._stop_event.set()

    def join_thread(self, timeout: float = 5):
        """Wait for the generator thread to terminate."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def stop(self):
        """Signal the generator to stop and join in one call (legacy API)."""
        self.signal_stop()
        self.join_thread()
        self.stats.unregister_generator(self.name)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def throttle(self):
        """Sleep to maintain target rate."""
        if self._delay > 0:
            time.sleep(self._delay)

    def deadline_reached(self, start: float) -> bool:
        """True if `self.duration > 0` and `start` was at least `duration` ago.

        Helper to remove the duplicated
        `if self.duration > 0 and time.monotonic() - start >= self.duration: break`
        boilerplate from every generator's loop. `start` should come from
        `time.monotonic()`.
        """
        return self.duration > 0 and (time.monotonic() - start) >= self.duration
