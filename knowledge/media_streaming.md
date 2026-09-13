# OTT Streaming, Media3 & ExoPlayer Architecture

## Core Engineering Principles
- **Player Lifecycle & Surface Management**: Decouple `ExoPlayer` / `MediaSession` from Activity lifecycle using AndroidX `MediaSessionService`. Attaching/detaching `PlayerView` from `SurfaceView` across configuration changes prevents video decoding pipeline teardown.
- **Adaptive Bitrate (ABR) & Bandwidth Metering**: Tune `DefaultTrackSelector` and `DefaultBandwidthMeter` for mobile cell towers. Providing custom initial bitrate estimates prevents the dreaded initial 3-second low-resolution pixelation on high-speed 5G/WiFi.
- **Custom LoadControl Buffer Strategy**: Default ExoPlayer buffer (50s) causes severe memory pressure on low-RAM devices during high-bitrate 1080p/4K streams. Tuning `DefaultLoadControl` with `minBufferMs: 15_000`, `maxBufferMs: 30_000`, and `bufferForPlaybackMs: 2_500` stabilizes playback without OOMs.
- **DRM & License Pre-fetching**: Widevine modular DRM initialization (`MediaDrmCallback`) adds 400-800ms to playback start. Pre-fetching offline DRM keys or executing license requests during feed scroll reduces Time-To-First-Frame (TTFF).
- **HLS/DASH Chunk Pre-caching**: Use `SimpleCache` with an LRU eviction policy (`LeastRecentlyUsedCacheEvictor`) and custom `CacheDataSource.Factory` to prevent duplicate network requests when users scrub back or re-watch short video segments.
