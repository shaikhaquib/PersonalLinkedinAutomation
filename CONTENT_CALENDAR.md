# LinkedIn Automation Content Calendar

**Owner**: Aquib Rashid Shaikh  
**Timezone**: Asia/Kolkata (IST)  
**Last Synchronized**: 2026-09-13 21:31:52 IST  

---

## Scheduled & Published Queue

| Date | Time (IST) | Archetype | Topic | Visual Template | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **2026-09-14** | 09:00 | `SCALE_INCIDENT_WAR_STORY` | Tuning ExoPlayer LoadControl Buffers for Low-Latency OTT Streaming | `process_infographic_dark.html.j2` | 🟢 Scheduled |

---

## How Scheduling Works

1. **Pre-generation & Quality Gate**: Posts in this calendar have passed all 6 Quality Review metrics and had their visual cards pre-rendered.
2. **Daily Execution Trigger**: GitHub Actions runs daily at `09:00 AM IST` (`cron: '30 3 * * *'`). When the scheduled time arrives, `scripts/main.py` checks this calendar, picks the queued post, publishes it via OAuth, drops the author first comment, and marks the status as Published.
3. **LinkedIn Native UI Alternate**: If you prefer posting via LinkedIn's desktop web scheduler (clock icon), copy the post text, first comment, and pre-rendered image asset directly from the calendar entry.
