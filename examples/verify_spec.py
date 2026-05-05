"""
Functional Specification Verification: Disruptor Engine Basic Flow
"""

import time

from vnpy.event import EVENT_TIMER, Event

from vnpy_disruptor_engine import DisruptorEventEngine


def on_timer(event: Event):
    print(f"Timer event received at {time.time()}")


def on_custom(event: Event):
    print(f"Custom event received: {event.data}")


def main():
    # 1. Initialization
    engine = DisruptorEventEngine(interval=1)

    # 2. Registration
    engine.register(EVENT_TIMER, on_timer)
    engine.register("eCustom", on_custom)

    # 3. Lifecycle Start
    print("Starting engine...")
    engine.start()

    # 4. Event Publication
    for i in range(5):
        engine.put(Event("eCustom", f"Message {i}"))
        time.sleep(0.5)

    # 5. Non-blocking Publication
    success = engine.try_put(Event("eCustom", "Non-blocking message"))
    print(f"Non-blocking put success: {success}")

    # 6. Lifecycle Stop
    time.sleep(2)
    print("Stopping engine...")
    engine.stop()
    print("Engine stopped.")


if __name__ == "__main__":
    main()
