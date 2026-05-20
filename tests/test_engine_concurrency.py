"""Engine concurrent-start race tests (B3)."""

import threading

from trafficgoat.config import TrafficConfig
from trafficgoat.engine import TrafficEngine
from trafficgoat.stats import StatsCollector


def test_engine_concurrent_start_only_runs_once():
    """Two threads racing on `start()` must result in a single engine run."""
    config = TrafficConfig(duration=0)  # 0 = run-until-stopped
    stats = StatsCollector()
    engine = TrafficEngine(config, stats)

    start_count = [0]
    original_start = stats.start

    def counting_start():
        start_count[0] += 1
        original_start()

    stats.start = counting_start  # type: ignore[method-assign]

    barrier = threading.Barrier(5)

    def racer():
        barrier.wait()
        engine.start()

    threads = [threading.Thread(target=racer) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    try:
        # Only one thread should have transitioned the engine to running.
        assert start_count[0] == 1, f"expected 1 start, got {start_count[0]}"
        assert engine.is_running()
    finally:
        engine.stop()


def test_engine_stop_is_idempotent():
    config = TrafficConfig(duration=0)
    engine = TrafficEngine(config, StatsCollector())
    engine.start()
    engine.stop()
    engine.stop()  # must not raise or hang
    assert not engine.is_running()
