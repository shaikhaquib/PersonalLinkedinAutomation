# Technical Leadership & Engineering Culture Knowledge Base

## Senior Engineering Mindset
- Code Reviews:
  - Focus on architecture, safety, edge cases, and maintainability, not nitpicks that can be automated via KtLint/Detekt.
  - Ask clarifying questions instead of making authoritative demands.
- Technical Debt vs Shipping Speed:
  - Technical debt is borrowed time with interest. Consciously identify when taking short-term technical debt is acceptable, and explicitly ticket refactoring work.
  - Never rebuild an entire app from scratch without an incremental migration plan (Strangler Fig pattern).
- Mentorship:
  - Encourage junior and mid-level engineers to debug down to root causes rather than applying temporary patches.
  - Teach system thinking: How does a mobile change affect backend servers, battery life, and network bandwidth?
- Incident Management & Post-Mortems:
  - Blameless post-mortems. Focus on systemic failures, missing safeguards, and broken CI pipelines rather than human error.
