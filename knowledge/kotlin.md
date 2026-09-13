# Kotlin & Coroutines Knowledge Base

## Coroutines & Structured Concurrency
- `CoroutineScope`: Defines lifecycle boundaries. Never use `GlobalScope` in production Android apps.
- Cancellation is cooperative: Coroutines must check `isActive` or call suspending functions (which throw `CancellationException`). Never catch `Throwable` or `Exception` without rethrowing `CancellationException`.
- Context switching: `withContext(Dispatchers.IO)` or `Dispatchers.Default` for CPU work. Keep Main thread free of any I/O or JSON parsing.
- Exception handling:
  - `launch` propagates exceptions to the parent job unless caught or using `SupervisorJob`.
  - `async` captures exceptions in the `Deferred` object; calling `.await()` re-throws.
- StateFlow vs SharedFlow:
  - `StateFlow`: Conflated state holder. Always has an initial value. Replays 1. Emits only when `!equals()`.
  - `SharedFlow`: Event bus / stream. Configurable replay, extraBufferCapacity, and bufferOverflow policy.
  - In Compose, collect with `collectAsStateWithLifecycle()` to avoid resource waste when the app is in the background.
- Kotlin 2.0+ & K2 Compiler:
  - Smarter smart casts, faster compilation, integrated Compose compiler plugin.
