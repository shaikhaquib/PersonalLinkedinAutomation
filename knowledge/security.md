# Android Security Knowledge Base

## Threat Vectors & Defenses (OWASP MASVS / MASTG)
- R8 / ProGuard rules:
  - Code shrinking, optimization, and name obfuscation.
  - Keep rules should be minimal and surgical. Avoid blanket `-keep class com.mycompany.** { *; }`.
- Root & Jailbreak Detection:
  - Check for common su binaries, Magisk hide paths, test-keys build tags, and writable `/system` or `/vendor` partitions.
  - Never rely solely on client-side root checks; combine with Google Play Integrity API for attestation.
- Play Integrity API:
  - Server-side verification of hardware-backed verdict (app licensing, device integrity, basic integrity).
  - Protect against repackaged APKs, tampered builds, and emulated environments.
- Secure Storage:
  - Never store auth tokens, refresh tokens, or user PII in plain `SharedPreferences`.
  - Use `EncryptedSharedPreferences` backed by MasterKey in Android Keystore, or secure Room database with SQLCipher.
  - Disable Android automatic backup for sensitive XML or DB files in `AndroidManifest.xml` (`android:allowBackup="false"`).
- Screen Protection:
  - `window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)` prevents task switcher screenshots and screen recording on sensitive banking screens.
