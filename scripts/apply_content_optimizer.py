#!/usr/bin/env python3
"""
Applies the universal linkedin-content-optimizer format to all scheduled posts.
Rules:
1. 3-line cutoff rule (problem-driven hook, no filler).
2. Dwell-time layout architecture (whitespace, 1️⃣ 2️⃣ anchors, bold lead-ins).
3. CTA consolidation (single thought-provoking 💡 prompt).
4. Sanitized formatting (zero in-body links, period-spaced bottom hashtags).
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.services.calendar_manager import CalendarManager
from scripts.services.text_formatter import format_linkedin_text

OPTIMIZED_POSTS = {
    "post_2026-09-16_0900": """Catching generic Exception inside your ViewModel coroutines silently destroys structured concurrency in production.

When a screen closes or a ViewModel clears, child jobs throw CancellationException to abort background execution.

1️⃣ **The Silent Memory Trap**: A blanket try-catch consumes CancellationException, keeping orphaned database and network flows executing indefinitely.

2️⃣ **The State Inconsistency Hazard**: Dead coroutines attempt to update UI state flows after navigation, triggering unpredictable crashes and phantom recompositions.

**The Core Fixes / Takeaways:**
• Always rethrow CancellationException immediately: `if (e is CancellationException) throw e`.
• Wrap domain operations in sealed Result interfaces at the repository boundary rather than swallowing exceptions.
• Inspect `result.exceptionOrNull()` when using `runCatching` to guarantee cancellation signals bubble up.

💡 How does your engineering team enforce coroutine cancellation safety across multi-module codebases?

.
.
.
#AndroidDev #Kotlin #JetpackCompose #MobileArchitecture #SoftwareArchitecture""",

    "post_2026-09-17_0900": """Android 15's 16KB memory page size support will immediately crash unaligned native C/C++ libraries at process startup.

Legacy Android devices strictly ran on 4KB memory pages.

1️⃣ **The Linker Failure Mode**: If an ELF shared object (.so) in your APK lacks 16KB alignment, the Linux dynamic linker aborts with a fatal UnsatisfiedLinkError before your first Activity even launches.

2️⃣ **The Hidden Transitive Risk**: Even if your first-party NDK code is aligned, legacy closed-source third-party binaries (audio engines, video decoders, C++ analytics) will silently crash your release builds.

**The Core Fixes / Takeaways:**
• Compile all native C/C++ targets with `-Wl,-z,max-page-size=16384` in your CMake / NDK build configurations.
• Audit native ELF segments locally using readelf: `readelf -l libnative.so | grep -E 'LOAD|ALIGN'`.
• Enforce automated CI linting on merged AAR dependencies to reject unaligned .so binaries before QA distribution.

💡 How is your mobile team auditing closed-source native dependencies for 16KB alignment ahead of Android 15?

.
.
.
#AndroidDev #Kotlin #Android15 #MobileArchitecture #TechLeadership""",

    "post_2026-09-18_0900": """Mandating a dedicated UseCase class for every single Repository method is the most costly cargo-cult anti-pattern in Android engineering.

When simple CRUD reads require a one-line passthrough UseCase, your codebase drowns in single-method boilerplate and redundant object mappers.

1️⃣ **The Abstraction Debt**: Every artificial layer doubles the maintenance burden, slows IDE indexing, and obscures business logic behind useless delegate calls.

2️⃣ **The Testing Overhead**: Engineers end up writing trivial unit tests that mock the UseCase to test a mock of the Repository to test a mock of the DAO.

**The Core Fixes / Takeaways:**
• Delete passthrough UseCases that only do `return repository.getData()` and inject the Repository straight into your ViewModel.
• Restrict UseCases strictly to orchestration logic spanning multiple independent repositories or complex business computations.
• Modularize by business vertical and user journey rather than dogmatic horizontal layers.

💡 Where does your engineering leadership draw the line between architectural purity and pragmatic productivity?

Scaling high-impact mobile platforms or modernizing your Android stack? Open to exchanging notes with mobile engineering leaders — feel free to reach out via DM.

.
.
.
#AndroidDev #Kotlin #MobileArchitecture #CleanCode #TechLeadership""",

    "post_2026-09-21_0900": """Hardware-isolated Android Keystore keys in a TEE cannot prevent duplicate financial charges when mobile networks drop mid-flight.

Cryptographic security and network idempotency are entirely different failure domains.

1️⃣ **The Post-Signature Disconnect**: BiometricPrompt authenticates hardware key access, but if the OS kills the process before backend ACK arrives, a blind retry double-charges the customer.

2️⃣ **The Ephemeral UUID Trap**: Generating transaction idempotency tokens in memory guarantees that process death or ViewModel recreation spawns a duplicate charge.

**The Core Fixes / Takeaways:**
• Persist a client-generated transaction UUID to Room database before invoking `BiometricPrompt.CryptoObject` hardware signing.
• Enforce `WorkManager.enqueueUniqueWork` with `ExistingWorkPolicy.KEEP` to survive abrupt process termination.
• Never regenerate idempotency tokens during network retries or automatic exponential backoff routines.

💡 How does your mobile team safeguard transaction idempotency when hardware cryptographic signatures survive process death on flaky networks?

Building or scaling high-stakes mobile apps (FinTech / Android)? Open to exchanging notes with mobile engineering leaders — feel free to reach out via DM.

.
.
.
#AndroidDev #Kotlin #MobileArchitecture #Security #TechLeadership"""
}

def main():
    calendar = CalendarManager()
    items = calendar._load_items()
    updated = 0

    for item in items:
        pid = item.get("id")
        if pid in OPTIMIZED_POSTS and item.get("status") == "scheduled":
            item["post_text"] = format_linkedin_text(OPTIMIZED_POSTS[pid])
            updated += 1
            print(f"Updated post text for {pid} ({item.get('topic')})")

    calendar._save_items(items)
    print(f"\n✅ Successfully updated {updated} scheduled posts in calendar and markdown!")

if __name__ == "__main__":
    main()
