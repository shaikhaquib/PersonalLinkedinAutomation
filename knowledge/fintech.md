# Fintech Mobile Development Knowledge Base

## Core Fintech Engineering Realities
- Double-spend & Network Idempotency:
  - Mobile networks drop connections silently. Every critical transaction (transfers, payments, order execution) MUST send a unique, server-validated idempotency key (UUID generated on the client before request dispatch).
  - Retries must reuse the identical idempotency key so the payment gateway never double-charges.
- Zero Cleartext in Memory:
  - Sensitive data (PIN, CVV, passwords) should ideally use `CharArray` or secure byte arrays that can be zeroed out (`Arrays.fill(arr, '\0')`) immediately after use, rather than immutable `String` objects that persist in JVM heap memory until Garbage Collection.
- Certificate Pinning & MitM Defense:
  - Network Security Config (`res/xml/network_security_config.xml`) with SHA-256 backup pins.
  - OkHttp `CertificatePinner` for dynamic pinning validation.
  - Implement certificate rotation strategies with at least two backup root/intermediate keys to prevent bricking clients.
- Android Keystore & Biometric Authentication:
  - Use `AndroidKeyStore` provider.
  - Keys encrypted using `KeyGenParameterSpec.Builder(..., KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)` with `setUserAuthenticationRequired(true)`.
  - Pair with `BiometricPrompt.CryptoObject` so biometric authorization is cryptographically tied to the cipher operation.
