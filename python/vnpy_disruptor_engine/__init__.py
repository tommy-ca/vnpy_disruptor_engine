from .engine import DisruptorEventEngine


def create_engine(interval: int = 1) -> DisruptorEventEngine:
    """
    Convenience factory to create a DisruptorEventEngine.
    """
    return DisruptorEventEngine(interval)


__all__ = ["DisruptorEventEngine", "create_engine"]
