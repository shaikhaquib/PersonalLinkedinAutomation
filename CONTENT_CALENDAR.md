# LinkedIn Automation Content Calendar

**Owner**: Aquib Rashid Shaikh  
**Timezone**: Asia/Kolkata (IST)  
**Last Synchronized**: 2026-09-15 14:20:03 IST  

---

## Scheduled & Published Queue

| Date | Time (IST) | Archetype | Topic | Visual Template | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2026-09-14** | 09:00 | `SCALE_INCIDENT_WAR_STORY` | Tuning ExoPlayer LoadControl Buffers for Low-Latency OTT Streaming | `process_infographic_dark.html.j2` | ✅ Published |
| **2026-09-15** | 09:00 | `HARDWARE_LOW_LEVEL_DEEP_DIVE` | BLE MTU Negotiation and ATT Layer Caching Traps in Android IoT Apps | `process_infographic_dark.html.j2` | ✅ Published |
| **2026-09-16** | 09:00 | `CODE_AUTOPSY_TEARDOWN` | Silent Coroutine Cancellation Swallowing in Android ViewModel Scopes | `code_card_dark.html.j2` | 🟢 Scheduled |
| **2026-09-17** | 09:00 | `OS_INTERNALS_DEEP_DIVE` | Preparing Native Android Libraries for 16KB Page Size Alignment in Android 15 | `process_infographic_dark.html.j2` | 🟢 Scheduled |
| **2026-09-18** | 09:00 | `CONTRARIAN_ARCHITECTURE_CALLOUT` | The Over-Engineering Trap of 6-Layer Clean Architecture in Android Apps | `code_card_dark.html.j2` | 🟢 Scheduled |

---

## How Scheduling Works

1. **Pre-generation & Quality Gate**: Posts in this calendar have passed all 6 Quality Review metrics and had their visual cards pre-rendered.
2. **Daily Execution Trigger**: GitHub Actions runs daily at `09:00 AM IST` (`cron: '30 3 * * *'`). When the scheduled time arrives, `scripts/main.py` checks this calendar, picks the queued post, publishes it via OAuth, drops the author first comment, and marks the status as Published.
3. **LinkedIn Native UI Alternate**: If you prefer posting via LinkedIn's desktop web scheduler (clock icon), copy the post text, first comment, and pre-rendered image asset directly from the calendar entry.
