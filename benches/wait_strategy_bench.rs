use criterion::{criterion_group, criterion_main, Criterion};
use vnpy_disruptor::{AdaptiveBlocking, AdaptiveContext, Yielding};
use disruptor::wait_strategies::WaitStrategy;
use disruptor::Sequence;
use std::sync::atomic::AtomicBool;
use parking_lot::Mutex;

fn bench_wait_strategies(c: &mut Criterion) {
    let mut group = c.benchmark_group("wait_strategies");

    group.bench_function("yielding", |b| {
        let strategy = Yielding;
        b.iter(|| strategy.wait_for(Sequence::default()))
    });

    group.bench_function("adaptive_blocking_spin", |b| {
        let ctx = AdaptiveContext {
            is_sleeping: AtomicBool::new(false),
            worker_thread: Mutex::new(None),
        };
        let strategy = AdaptiveBlocking {
            context: &ctx as *const _,
        };
        // We only bench the spin phase (count=0)
        b.iter(|| {
            vnpy_disruptor::WAIT_COUNT.with(|c| c.set(0));
            strategy.wait_for(Sequence::default())
        })
    });

    group.finish();
}

criterion_group!(benches, bench_wait_strategies);
criterion_main!(benches);
