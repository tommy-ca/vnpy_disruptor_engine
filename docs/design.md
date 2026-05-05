# High-Performance Event Engine Design

## 1. Architecture Overview

The Disruptor Event Engine replaces the standard Python `queue.Queue` with a high-performance, zero-copy ring buffer implemented in Rust.

### Data Flow
1. **Producer (Python)**: Calls `engine.put(event)`.
2. **Binding Layer (PyO3)**: Increments the reference count of the Python object and stores it as an `Arc<PyObject>` in the ring buffer.
3. **Wait Strategy (Rust)**: The background worker thread polls/waits for new events according to the selected strategy (`blocking`, `busy_spin`, etc.).
4. **Consumer (Managed Worker)**: Batches available events and acquires the GIL once per batch.
5. **Dispatcher (Python)**: Iterates through the batch and executes registered handlers.

## 2. Data & Code Flows

### Event Publication Flow
```mermaid
sequenceDiagram
    participant App as Python App
    participant Engine as DisruptorEventEngine
    participant RS as Rust Producer
    participant RB as Ring Buffer

    App->>Engine: put(event)
    Engine->>RS: publish(event)
    RS->>RB: claim_sequence()
    RB-->>RS: sequence
    RS->>RB: store(Arc<PyObject>)
    RS->>RB: commit(sequence)
```

### Event Consumption Flow (Managed Worker)
```mermaid
sequenceDiagram
    participant RB as Ring Buffer
    participant Worker as Rust Worker
    participant GIL as Python GIL
    participant Handler as Python Handler

    Worker->>RB: waitFor(sequence)
    RB-->>Worker: batch_available
    Worker->>GIL: acquire()
    loop For each event in batch
        Worker->>Handler: execute(event)
    end
    Worker->>GIL: release()
    Worker->>RB: update_consumer_cursor()
```

## 3. Component Design

### 3.1 Rust Native Extension (`vnpy_disruptor`)
- **Core**: Uses the `disruptor-rs` crate for high-performance ring buffer management.
- **Worker**: A dedicated thread that manages the event loop, ensuring low latency by staying "hot" or parking efficiently.
- **Batching**: Implements a GIL-aware batching logic that minimizes the overhead of switching between Rust and Python.

### 3.2 Python Wrapper (`DisruptorEventEngine`)
- **Lifecycle**: Manages the instantiation of the native producer and worker.
- **Pre-start Queue**: Implements an `OrderedDict` to buffer events until `start()` is called, ensuring no events are lost during initialization.
- **Factory Integration**: Integrated into `MainEngine` via the `create_engine()` factory.

## 4. Concurrency & Sync
- **GIL Management**: The worker thread only holds the GIL when calling back into Python handlers.
- **Thread Pinning**: Supports optional CPU affinity for the worker thread to minimize context switching in high-performance scenarios.

## 5. Queue Pattern & Concurrency Model

| Pattern | Application in VeighNa | Rationale |
| :--- | :---: | :--- |
| **MPSC** | **Primary** | **Multi-Producer**: Gateways, Timer, and Apps. **Single-Consumer**: Sequential worker thread for state consistency. |
| **MPMC** | **Capability** | Technically supported by the underlying Disruptor architecture, enabling future parallel consumption models. |

### Producer-Consumer Analysis
- **Producers**: Multiple independent threads (Gateways, MainEngine, Timer) publish events simultaneously. Lock-free `MultiProducer` ensures non-blocking publication even under high contention.
- **Consumer**: A single managed worker thread dispatches events to Python handlers. This maintains the sequential consistency required by legacy trading logic while offloading the queue management to native Rust.

## 6. Interface Parity: `try_put` vs. `put`

The Disruptor implementation introduces a non-blocking `try_put()` method, which has been backported to the standard `EventEngine` for interface parity.

### 6.1 Rationale: The "Log Sinking" Problem
Standard `put()` operations block when the ring buffer (or queue) is full. This is desirable for market data (providing backpressure) but catastrophic for logging in two specific scenarios:

1. **Self-Deadlock**: If a registered handler (running in the EventEngine worker thread) generates a log message while the buffer is saturated, a blocking `put()` will wait for space to be cleared. However, space can only be cleared by the worker thread itself, resulting in a permanent deadlock.
2. **UI Responsiveness**: If the Main/GUI thread attempts to write a log during a high-volatility tick burst, a blocking `put()` will freeze the user interface until the engine catches up.

### 6.2 Solution
`MainEngine.write_log()` and other components now use `try_put(event)`. If the buffer is full, the log is dropped (with an optional console fallback), ensuring the system remains responsive and deadlock-free.

## 8. Deep Dive: `disruptor-rs` Native Behavior

### 8.1 Native Blocking Mechanics
The underlying `disruptor-rs` crate implements a **bounded, zero-copy ring buffer**. When the buffer is full:
- The **`MultiProducer`** natively blocks the calling thread during a `publish()` operation.
- It uses a **Busy-Spin** (or configured wait strategy) to wait until the consumer sequence has progressed far enough to permit claiming a new slot.
- This provides essential **backpressure**, ensuring that upstream systems (like market data gateways) slow down rather than overwhelming the downstream consumer.

### 8.2 The `try_publish` Primitive
`disruptor-rs` also provides a `try_publish()` primitive which returns immediately with a `Full` error if no slots are available. We expose this as the foundational primitive for `try_put()`.

## 9. Rationale for `try_put` Architecture

While backpressure is vital for market data, it is detrimental for **telemetry (logging)** and **recursive calls**.

### 9.1 Self-Deadlock Immunity
In a bounded buffer system, the worker thread (consumer) is the only entity that can free up space. If a handler running on the worker thread calls a blocking `put()` while the buffer is full, it will wait for itself to clear the buffer—a classic **self-deadlock**. By using `try_put()`, we ensure that handlers never block the consumer loop.

### 9.2 UI Thread Safety
The Main thread in VeighNa handles the GUI. A blocking `put()` during a high-volatility burst would freeze the user interface. `try_put()` allows the UI to attempt logging and "fire-and-forget" if the system is under extreme pressure, maintaining operational control.

## 10. Audit Results (Hardened - 2026-05-04)

- **Memory Stability**: Pass (10M events, ~10MB baseline delta).
- **Concurrency Safety**: Pass (No deadlocks under buffer overflow).
- **API Parity**: Pass (Drop-in replacement for standard `EventEngine`).
- **Telemetry Safety**: Pass (Logging via `try_put` prevents UI freezes).

## 11. Decoupled Architecture (Out-of-Tree)

To maintain the purity of the VeighNa core while providing institutional-grade extensions, the Disruptor engine is structured as an **independent package**.

### 11.1 Integration Pattern
The engine integrates via the **Factory Pattern** in `vnpy.event.create_engine()`. This factory performs a **duck-typed discovery**:
1. Checks if `event.use_disruptor` is enabled.
2. Attempts to import `vnpy_disruptor_engine`.
3. Falls back to the internal `EventEngine` if the extension is unavailable.

### 11.2 Component Decoupling
```mermaid
graph TD
    A[VeighNa Core] --> B[EventEngine Interface]
    B --> C[Standard EventEngine]
    B --> D[DisruptorEventEngine Package]
    D --> E[Python Wrapper]
    E --> F[Rust Native Extension]
    F --> G[disruptor-rs]
```

This decoupling allows for:
- **Fast Iteration**: Updating the engine without re-releasing the entire framework.
- **Platform Specifics**: Isolating the Rust compilation requirements to a specialized package.
- **Selective Adoption**: Professional users can opt-in to the high-performance stack while casual users maintain a light dependency footprint.

## 12. Performance Analysis: Native vs. Bindings

A significant performance gap exists between the native Rust core and the Python-accessible engine. Understanding this gap is essential for institutional-grade tuning.

| Layer | P50 Latency (Wait Phase) | Throughput (Raw) | Responsibility |
| :--- | :--- | :--- | :--- |
| **Native Rust** | **~4.2 ns** | **> 100M/s** | Ring buffer sequencing, atomics, thread parking. |
| **PyO3/Python** | **~16.9 µs** | **~4.5M/s** | Object ref-counting, GIL management, FFI bridge. |

### 12.1 The "Bridge" Tax (~20µs Gap)
The ~20µs latency observed in the Python engine is primarily consumed by:
1.  **FFI Boundary Crossing**: Each `put()` call must transition from the Python interpreter to the Rust binary.
2.  **GIL Management**: The worker thread must acquire the Python Global Interpreter Lock (GIL) before executing handlers. Even with optimized batching, the acquisition delay is the dominant latency factor.
3.  **Reference Counting**: Python objects must have their reference counts incremented when entering the ring buffer and decremented when exiting, which are atomic operations but add up across millions of events.

### 12.2 Why Use Disruptor?
Despite the 20µs bridge cost, the Disruptor engine provides:
- **2x Latency Reduction**: Standard Python `queue.Queue` typically exhibits ~35-50µs P50 latency.
- **5x Throughput Increase**: Lock-free MPSC sequencing allows for significantly higher event density than mutex-based Python queues.
- **Deterministic Backpressure**: Unlike the standard engine, the Disruptor engine provides hardware-level backpressure that slows down producers before the system hits OOM (Out of Memory) conditions.

## 13. MPSC Data Flow Analysis

The engine is primarily designed for the **Multi-Producer, Single-Consumer (MPSC)** pattern, which matches the architectural requirements of most quantitative trading systems.

```mermaid
graph LR
    subgraph Producers [Python Producers]
        P1[Gateway A]
        P2[Strategy B]
        P3[Timer]
    end
    
    subgraph Core [Rust Disruptor Core]
        RB((Ring Buffer))
        WS[Wait Strategy]
    end
    
    subgraph Consumer [Python Consumer]
        W[Worker Thread]
        H1[Log Handler]
        H2[Trade Handler]
    end
    
    P1 -- put --> RB
    P2 -- put --> RB
    P3 -- put --> RB
    
    RB -- sequence --> WS
    WS -- wake --> W
    W -- acquire GIL --> W
    W -- dispatch --> H1
    W -- dispatch --> H2
```

### Flow Characteristics
1.  **Concurrent Ingestion**: Multiple gateways and strategies can publish simultaneously without a global lock, utilizing atomic CAS for slot claiming.
2.  **Serialized Dispatch**: A single worker thread ensures that event handlers are executed in the exact order they were committed to the buffer, preserving causal consistency for state-sensitive trading logic.
