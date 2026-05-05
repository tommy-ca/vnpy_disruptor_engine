# CLAUDE.md - vnpy_disruptor_engine

High-performance event engine extension for VeighNa.

## UV-Native Workflow (MANDATORY)
This project uses `uv` exclusively. **Do not use `pip`, `uv pip`, or global python.**

- **Setup Environment**: `uv sync` (Creates `.venv` with all dependencies)
- **Build Rust Extension**:
  - Release: `uv run maturin develop --release`
  - Debug: `uv run maturin develop`
- **Execution**: Always prefix commands with `uv run` to use the local venv.

## Package Layout (Institutional Standard)
- **`python/`**: Python source directory.
- **`src/`**: Rust native tier.
- **`tests/`**: TDD suite (Parity, E2E, Perf).
- **`docs/`**: Specs, Design, and Audit.
- **`examples/`**: Verification scenarios.

## Test & Benchmark Commands
- **Rust Unit Tests**: `cargo test --no-default-features`
- **Rust Benchmarks**: `cargo bench --no-default-features`
- **Type Check**: `uv run ty check`
- **Lint & Format**: `uv run ruff check .` and `uv run ruff format .`
- **Parity Tests**: `uv run pytest tests/test_parity.py`
- **Integration Tests**: `uv run pytest tests/test_disruptor_integration.py`
- **Non-Blocking Guards**: `uv run pytest tests/test_non_blocking_guards.py`
- **Performance Specs**: `uv run pytest tests/test_perf_specs.py -s`
- **Memory Leak Check**: `uv run pytest tests/test_memory_leak.py`
- **Full Suite**: `uv run pytest tests/`

## Examples
- **Functional Spec**: `uv run python examples/verify_spec.py`
- **HFT Scenario**: `uv run python examples/hft_disruptor/run_hft.py`
- **Engine Comparison**: `uv run python examples/hft_disruptor/compare_engines.py`

## Coding Standards
- **SOLID**: Maintain clean interfaces, specifically the `EventEngine` abstraction.
- **KISS**: Keep Rust bindings focused on the ring buffer; handle logic in Python where possible.
- **DRY**: Use the `disruptor-rs` native wait strategies rather than reimplementing them.
- **YAGNI**: Don't add multi-consumer support until a concrete use case arises.
- **Memory Safety**: All `PyObject` drops MUST occur while holding the GIL. Use `Mutex` for interior mutability in ring buffer slots.

## Production Settings
- Default Strategy: `blocking` (AdaptiveBlocking in Rust)
- Default Buffer Size: `65536`
- Interface: Must remain 100% compatible with `vnpy.event.EventEngine`.
