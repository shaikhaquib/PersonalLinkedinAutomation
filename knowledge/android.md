# Android SDK & Internals Knowledge Base

## Core Principles
- Process lifecycle: Foreground, visible, service, cached/background. Android kills processes silently from cached LRU buckets under low memory (LMK).
- Lifecycle-aware components: ViewModel, LifecycleOwner, SavedStateHandle. Always restore critical state across process death, not just configuration changes.
- Jetpack Compose Recomposition:
  - Compose is a declarative UI toolkit built on runtime snapshots.
  - Stability system (`@Stable`, `@Immutable`, primitives, data classes with immutable fields). Unstable parameters force recomposition even when values have not changed.
  - DerivedStateOf: Use when reading a state that changes more frequently than the UI needs to update (e.g. scroll position > threshold).
  - SnapshotMutationPolicy: structuralEqualityPolicy, referentialEqualityPolicy.
  - Avoid heavy computations in composable functions; push to ViewModels or remember with proper keys.
- WorkManager vs Foreground Services:
  - Deferrable, guaranteed background work belongs in WorkManager (JobScheduler / AlarmManager fallback).
  - Use Foreground Services strictly for active user-facing tasks (playback, live navigation, active sensor tracking).
- IPC & Binder:
  - Binder transaction limit: 1MB transaction buffer shared across all ongoing binder calls in the process. Never pass large Bitmaps or heavy JSON payloads across AIDL/Intents.
