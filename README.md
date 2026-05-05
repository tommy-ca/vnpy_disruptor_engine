# vnpy_disruptor_engine

High-performance institutional-grade event engine for VeighNa, backed by `disruptor-rs`.

## Features
- **LMAX Disruptor Pattern**: Uses a lock-free ring buffer for ultra-low latency event processing.
- **Rust Implementation**: Core logic implemented in Rust for maximum performance and safety.
- **GIL-Aware Batching**: Minimizes Python GIL contention by processing events in batches.
- **Adaptive Blocking**: 0% CPU usage when idle while maintaining sub-20µs wakeup latency.
- **Out-of-Tree**: Decoupled from `vnpy` core for independent updates.

## Performance
- **P50 Latency**: ~13.7 µs
- **P99 Latency**: ~32.1 µs
- **Throughput**: > 4.5M events/sec

## Installation
Ensure you have `uv` installed.

```bash
uv sync
uv run maturin develop --release
```

## Configuration
Set `event.use_disruptor: true` in your `vt_setting.json`.

## Documentation
See [docs/specifications.md](docs/specifications.md) for technical details.
