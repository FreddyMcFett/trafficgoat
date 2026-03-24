"""Core traffic engine - orchestrates generators and modes."""

import threading
import time

from trafficgoat.config import TrafficConfig
from trafficgoat.stats import StatsCollector
from trafficgoat.generators.base import BaseGenerator


class TrafficEngine:
    """Central engine that manages traffic generators."""

    def __init__(self, config: TrafficConfig, stats: StatsCollector | None = None):
        self.config = config
        self.stats = stats or StatsCollector()
        self._generators: list[BaseGenerator] = []
        self._running = False
        self._timer_thread: threading.Thread | None = None

    def add_generator(self, generator: BaseGenerator):
        self._generators.append(generator)

    def start(self):
        """Start all generators and the stats timer."""
        if self._running:
            self.stats.log("Engine already running")
            return

        self._running = True
        self.stats.start()
        self.stats.log(f"Engine starting with {len(self._generators)} generator(s)")
        self.stats.log(f"Target: {self.config.target} | Duration: {self.config.duration}s | Dry-run: {self.config.dry_run}")

        for gen in self._generators:
            gen.start()

        # Start duration timer
        if self.config.duration > 0:
            self._timer_thread = threading.Thread(target=self._duration_timer, daemon=True)
            self._timer_thread.start()

        # Start stats emitter
        self._stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        self._stats_thread.start()

    def stop(self):
        """Stop all generators."""
        if not self._running:
            return
        self._running = False
        self.stats.log("Engine stopping...")
        self.stats.stop()
        self.stats.emit_stats()  # Emit immediately so UI updates
        for gen in self._generators:
            gen.stop()
        self.stats.log("Engine stopped")
        self.stats.emit_stats()

    def wait(self):
        """Block until all generators finish or duration expires."""
        try:
            while self._running:
                alive = any(g.is_running() for g in self._generators)
                if not alive:
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            self.stats.log("Interrupted by user")
        finally:
            self.stop()

    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        stats = self.stats.get_stats()
        stats["mode"] = self.config.mode
        stats["target"] = self.config.target
        stats["generator_count"] = len(self._generators)
        return stats

    def _duration_timer(self):
        """Stop engine after configured duration."""
        start = time.time()
        while self._running:
            if time.time() - start >= self.config.duration:
                self.stats.log(f"Duration ({self.config.duration}s) reached")
                self.stop()
                return
            time.sleep(0.5)

    def _stats_loop(self):
        """Periodically emit stats updates every second."""
        while self._running:
            self.stats.emit_stats()
            # Sleep in small increments so we stop promptly
            for _ in range(10):
                if not self._running:
                    break
                time.sleep(0.1)
        # Emit a few final updates after stopping so the UI catches the final state
        for _ in range(3):
            self.stats.emit_stats()
            time.sleep(0.3)

    def clear(self):
        """Remove all generators and reset."""
        self.stop()
        self._generators.clear()
        self.stats.reset()
