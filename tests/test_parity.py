import time

from vnpy.event import Event

from vnpy_disruptor_engine import DisruptorEventEngine


def test_engine_initialization():
    """Test engine can be initialized."""
    engine = DisruptorEventEngine(interval=1)
    assert engine is not None
    assert engine._interval == 1
    assert not engine.is_active()


def test_engine_lifecycle():
    """Test engine start and stop."""
    engine = DisruptorEventEngine(interval=1)
    engine.start()
    assert engine.is_active()

    time.sleep(0.1)
    engine.stop()
    assert not engine.is_active()


def test_event_handling():
    """Test event registration and handling."""
    engine = DisruptorEventEngine(interval=1)

    results = []

    def handler(event):
        results.append(event.data)

    engine.register("test_event", handler)
    engine.start()

    event = Event("test_event", "hello")
    engine.put(event)

    # Wait for processing
    time.sleep(0.1)

    assert "hello" in results
    engine.stop()


def test_general_handler():
    """Test general handler registration and handling."""
    engine = DisruptorEventEngine(interval=1)

    results = []

    def general_handler(event):
        results.append(event.type)

    engine.register_general(general_handler)
    engine.start()

    engine.put(Event("type1", 1))
    engine.put(Event("type2", 2))

    time.sleep(0.1)

    assert "type1" in results
    assert "type2" in results
    engine.stop()


def test_try_put():
    """Test non-blocking put."""
    engine = DisruptorEventEngine(interval=1)
    engine.start()

    success = engine.try_put(Event("test", 1))
    assert success is True

    engine.stop()


def test_pre_start_queue():
    """Test events published before start are processed after start."""
    engine = DisruptorEventEngine(interval=1)

    results = []

    def handler(event):
        results.append(event.data)

    engine.register("test", handler)

    # Put event before start
    engine.put(Event("test", "early"))
    assert len(results) == 0

    engine.start()
    time.sleep(0.1)

    assert "early" in results
    engine.stop()
