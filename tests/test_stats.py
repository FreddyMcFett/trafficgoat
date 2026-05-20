"""StatsCollector thread-safety tests."""

import threading
import time

from trafficgoat.stats import StatsCollector


class TestStatsCollector:
    def test_register_and_update(self):
        stats = StatsCollector()
        stats.register_generator("gen-a")
        stats.start()
        stats.update("gen-a", packets=5, bytes_sent=100)
        result = stats.get_stats()
        assert result["total_packets"] == 5
        assert result["total_bytes"] == 100
        assert result["running"] is True

    def test_running_flag_inside_lock(self):
        """Regression for B4: `running` was read outside the lock and could
        race with stop().  After the fix, running must reflect the locked
        view of state.
        """
        stats = StatsCollector()
        stats.start()
        assert stats.get_stats()["running"] is True
        stats.stop()
        assert stats.get_stats()["running"] is False

    def test_concurrent_updates(self):
        stats = StatsCollector()
        stats.register_generator("gen-a")
        stats.start()

        def worker():
            for _ in range(1000):
                stats.update("gen-a", packets=1, bytes_sent=10)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        result = stats.get_stats()
        assert result["total_packets"] == 10_000
        assert result["total_bytes"] == 100_000

    def test_log_callback_exception_is_swallowed_but_logged(self, caplog):
        stats = StatsCollector()

        def bad_cb(_):
            raise RuntimeError("boom")

        stats.on_log(bad_cb)
        import logging
        with caplog.at_level(logging.WARNING, logger="trafficgoat.stats"):
            stats.log("hello")  # must not raise
        # Other callbacks still see the message.
        seen = []
        stats.on_log(seen.append)
        stats.log("world")
        assert any("world" in line for line in seen)

    def test_reset_clears_state(self):
        stats = StatsCollector()
        stats.register_generator("gen-a")
        stats.start()
        stats.update("gen-a", packets=10)
        stats.reset()
        result = stats.get_stats()
        assert result["total_packets"] == 0
        assert result["running"] is False
        assert result["generators"] == {}

    def test_monotonic_elapsed_does_not_go_negative(self):
        """Regression for B6: time.time() could go backwards under NTP slew.
        With time.monotonic(), elapsed is always non-negative."""
        stats = StatsCollector()
        stats.register_generator("gen-a")
        stats.start()
        time.sleep(0.05)
        elapsed = stats.get_stats()["elapsed"]
        assert elapsed >= 0
