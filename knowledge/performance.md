# Android Performance Knowledge Base

## Memory, Jank & App Startup
- App Startup Optimization:
  - Cold start, warm start, hot start.
  - Baseline Profiles: Pre-compiles critical user journeys into AOT machine code upon app installation, eliminating JIT compilation stalls during startup. Often delivers 20-35% startup time reduction.
  - App Startup Library: Consolidate multiple ContentProviders into a single initializer to avoid main-thread blockages before `Application.onCreate()`.
  - Lazy initialization: Do not initialize heavy SDKs (analytics, crash reporting, payment gateways) synchronously on the main thread during `onCreate()`.
- Memory Leaks & OOM:
  - Static references to `Activity` or `Context`.
  - Non-static inner classes / anonymous listeners retaining the outer class.
  - Unregistered broadcast receivers or CoroutineScopes that outlive View lifecycles.
  - Bitmaps: Always downsample with `BitmapFactory.Options.inSampleSize` or use Coil/Glide with memory caching.
- Jank & Frame Drops:
  - Standard 60Hz display gives 16ms per frame; 120Hz display gives 8.3ms per frame.
  - Perfetto & Macrobenchmark: Measure frame timings, jank percentage, and track CPU thread scheduling.
  - Layout hierarchy: Avoid deeply nested layouts; in Compose, avoid redundant measurement and layout passes.
