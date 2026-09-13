# Bluetooth Low Energy (BLE) & Hardware Connectivity

## Core Engineering Principles
- **GATT Connection Lifecycle**: `BluetoothGattCallback` is strictly asynchronous and single-threaded. Queuing write/read requests sequentially with Mutex or Coroutine Channels is mandatory; concurrent GATT operations fail silently with `GATT_FAILURE` (status 133).
- **AutoConnect Gotcha**: `connectGatt(context, false, callback, TRANSPORT_LE)` should almost always use `autoConnect = false` for initial connection (direct connection timeout 30s) instead of `true` (passive scan which can take minutes or fail on OEM chipsets).
- **MTU Negotiation**: Default BLE MTU is 23 bytes (effective payload: 20 bytes). Requesting `gatt.requestMtu(517)` immediately after `onConnectionStateChange` increases throughput by 25x for firmware updates or large telemetry bursts.
- **Connection Priority**: Use `gatt.requestConnectionPriority(BluetoothGatt.CONNECTION_PRIORITY_HIGH)` during initial handshake or bulk data sync to drop connection interval to 11.25-15ms, then switch back to `BALANCED` or `LOW_POWER` to prevent battery drain.
- **Android 12+ Permissions**: `BLUETOOTH_SCAN` with `neverForLocation` flag avoids requiring `ACCESS_FINE_LOCATION` when device is not used to infer physical location.
- **Scanning Best Practices**: Always scan with `ScanFilter` (service UUID) and `ScanSettings.SCAN_MODE_LOW_LATENCY` for foreground discovery, throttling scan duration to 10-15s to comply with Android OS scan restrictions.
