# Location, Maps SDK & Geofencing Architecture

## Core Engineering Principles
- **Battery-Conscious Location Tracking**: Direct GPS polling drains battery within hours. Use `FusedLocationProviderClient` with `PRIORITY_BALANCED_POWER_ACCURACY` for routine tracking, reserving `PRIORITY_HIGH_ACCURACY` strictly for active turn-by-turn navigation screens.
- **Geofencing with PendingIntent**: Register geofences with `GeofencingClient.addGeofences()` using a non-wakeful `BroadcastReceiver` and `PendingIntent`. Delegate payload dispatching to `WorkManager` or an immediate `ForegroundService` to respect Android 12+ background launch restrictions.
- **Android 14+ Foreground Service Types**: Background location updates strictly require `foregroundServiceType="location"` declared in `AndroidManifest.xml` and user runtime confirmation of "Allow all the time" or foreground notification visibility.
- **Doze Mode & Standby Buckets**: In deep Doze, network access and standard alarms are cut off. Batching coordinate uploads with `setSmallestDisplacement()` and flushing points only when entering high-speed motion state keeps app in power-efficient Standby Buckets.
- **Map Surface Performance**: In Jetpack Compose (`com.google.maps.android:maps-compose`), excessive recomposition of `GoogleMap` marker clusters causes severe frame drops. Wrap marker state in stable immutable collections and memoize camera position updates.
