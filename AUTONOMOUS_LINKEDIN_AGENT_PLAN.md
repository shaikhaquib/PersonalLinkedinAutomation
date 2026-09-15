# Autonomous LinkedIn Content Agent
## Migration from Postiz to LinkedIN-Post-automation

Repository:
https://github.com/vipinvishal/LinkedIN-Post-automation

Goal:
Replace Postiz with a fully autonomous, self-hosted/open-source LinkedIn
content automation system.

The system must operate without daily human intervention.

Human intervention is required ONLY when:
- API key is missing
- API key is expired
- OAuth authorization is required
- LinkedIn permissions are missing
- LinkedIn repeatedly returns an authentication/authorization error
- An unrecoverable system/configuration error occurs

---

# 1. Primary Objective

Build an autonomous LinkedIn publishing agent for a personal LinkedIn
profile.

The agent should:

1. Discover relevant Android/technology topics.
2. Research and validate the topic.
3. Check whether the topic has already been posted.
4. Generate a LinkedIn post.
5. Make the writing sound natural and human.
6. Validate technical accuracy and content quality.
7. Decide whether an image/infographic is useful.
8. Generate an infographic when appropriate.
9. Publish automatically to the personal LinkedIn profile.
10. Verify that publishing succeeded.
11. Store the published post in persistent history.
12. Avoid duplicate/repetitive content.
13. Recover automatically from temporary failures.
14. Notify the user only when human intervention is genuinely required.

---

# 2. Base Repository

Use this repository as the starting point:

https://github.com/vipinvishal/LinkedIN-Post-automation

DO NOT rewrite the entire repository from scratch.

First inspect and understand:

- existing Python architecture
- LinkedIn authentication
- LinkedIn publishing implementation
- Gemini integration
- infographic generation
- GitHub Actions
- configuration files
- topic management
- logging
- existing error handling

Preserve working components whenever possible.

---

# 3. Target Architecture

```text
                         GitHub Actions
                              |
                         Daily Trigger
                              |
                              v
                    +---------------------+
                    |   Content Agent     |
                    +----------+----------+
                               |
             +-----------------+----------------+
             |                 |                |
             v                 v                v
       Android RSS       Kotlin Sources    GitHub Sources
             |                 |                |
             +-----------------+----------------+
                               |
                               v
                       Topic Analyzer
                               |
                               v
                      Duplicate Checker
                               |
                               v
                       Research Agent
                               |
                               v
                       Writing Agent
                               |
                               v
                     Quality Reviewer
                               |
                       +-------+-------+
                       |               |
                      PASS            FAIL
                       |               |
                       v               v
                 Image Decision      Rewrite
                       |
                 +-----+-----+
                 |           |
                YES          NO
                 |           |
                 v           |
           Image Generator   |
                 |           |
                 +-----+-----+
                       |
                       v
                LinkedIn Publisher
                       |
                       v
                Verify Publication
                       |
                       v
                 Save History
                       |
                       v
                     DONE
```

---

# 4. Posting Frequency

Default:

```text
1 post per day
```

Do NOT publish multiple posts every day unless explicitly configured.

Configuration:

```json
{
  "posts_per_day": 1,
  "preferred_time": "09:00",
  "timezone": "Asia/Kolkata"
}
```

The system must prevent duplicate execution.

If a post has already been successfully published for the current
posting window, do not publish another post.

---

# 5. Content Niche

Primary niche:

```text
Android Development
Kotlin
Jetpack Compose
Android Architecture
Android Security
Android Performance
Fintech Mobile Development
AI + Android
AOSP
Mobile Engineering
Software Engineering
Developer Career
Technical Leadership
```

Secondary topics may be used only when they are relevant to the
primary niche.

Avoid generic AI content unrelated to Android/mobile engineering.

---

# 6. Content Sources

Create:

```text
config/sources.json
```

Recommended sources:

```json
{
  "sources": [
    {
      "name": "Android Developers Blog",
      "type": "rss",
      "url": "https://android-developers.googleblog.com/feeds/posts/default?alt=rss"
    },
    {
      "name": "Kotlin Blog",
      "type": "rss",
      "url": "https://blog.jetbrains.com/kotlin/feed/"
    },
    {
      "name": "Google Developers",
      "type": "rss",
      "url": "https://developers.googleblog.com/feeds/posts/default?alt=rss"
    },
    {
      "name": "Android Studio Releases",
      "type": "rss",
      "url": "https://androidstudio.googleblog.com/feeds/posts/default?alt=rss"
    },
    {
      "name": "Firebase Blog",
      "type": "rss",
      "url": "https://firebase.blog/rss.xml"
    },
    {
      "name": "OWASP Mobile",
      "type": "rss",
      "url": "https://github.com/OWASP/owasp-mastg/releases.atom"
    }
  ]
}
```

Use public RSS feeds/APIs whenever possible.

Do not make Exa mandatory.

If one source fails, automatically continue with the remaining sources.

---

# 7. Topic Selection

The agent must score candidate topics.

Example:

```text
relevance_score
freshness_score
technical_value_score
originality_score
personal_relevance_score
```

Calculate an overall score.

Example:

```text
overall_score =
    relevance * 0.30 +
    freshness * 0.20 +
    technical_value * 0.20 +
    originality * 0.15 +
    personal_relevance * 0.15
```

Only topics above the configured threshold should be selected.

Default:

```text
minimum_topic_score = 0.70
```

---

# 8. Duplicate Detection

Create:

```text
data/content_history.json
```

or preferably SQLite (`data/content_history.db`).

Store:

```json
{
  "topic": "...",
  "title": "...",
  "content_hash": "...",
  "published_at": "...",
  "linkedin_post_id": "...",
  "source": "...",
  "status": "published"
}
```

Before creating a post:

1. Compare exact topic.
2. Compare normalized title.
3. Compare semantic similarity.
4. Compare content hash.

If the topic is too similar to previous content:

```text
REJECT
```

and select another topic.

---

# 9. Personal Knowledge Base

Create:

```text
knowledge/
```

Files:

```text
knowledge/android.md
knowledge/kotlin.md
knowledge/fintech.md
knowledge/architecture.md
knowledge/security.md
knowledge/performance.md
knowledge/leadership.md
knowledge/experience.md
```

These files contain verified professional experience and technical
knowledge that the AI may use.

IMPORTANT:

The AI must NEVER invent personal experience.

If the knowledge base does not contain evidence for a personal claim,
do not write it as personal experience.

---

# 10. Persona

Create:

```text
config/persona.json
```

Example:

```json
{
  "role": "Senior Android Developer",
  "experience": "8+ years",
  "specialization": [
    "Android",
    "Kotlin",
    "Jetpack Compose",
    "Fintech",
    "Mobile Architecture",
    "Android Security",
    "Performance"
  ],
  "voice": [
    "natural",
    "conversational",
    "technical",
    "practical",
    "direct",
    "professional"
  ]
}
```

---

# 11. Writing Rules

The generated post must:

* sound like a real developer
* provide useful information
* avoid unnecessary fluff
* use simple language
* be technically accurate
* avoid excessive emojis
* avoid excessive hashtags
* avoid fake personal stories
* avoid engagement bait
* avoid clickbait
* avoid corporate marketing language

Avoid phrases such as:

```text
"In today's rapidly evolving world..."

"Game changer"

"Revolutionary"

"Exciting times ahead"

"Unlock the power of..."

"10x your productivity"

"Here's the ultimate guide..."
```

Do not use generic AI LinkedIn writing patterns.

---

# 12. Post Structure

Prefer:

```text
Hook
↓
Problem / observation
↓
Technical explanation
↓
Practical example
↓
Takeaway
```

Example structure:

```text
I used to think X was enough for Y.

But in real Android applications, Z becomes important.

The reason is...

A better approach is...

The main takeaway:
...
```

Do not force this structure on every post.

The writing agent should vary the structure naturally.

---

# 13. Content Types

The agent should automatically choose one of:

```text
technical_tip
android_news
kotlin_tip
compose_tip
architecture
security
performance
fintech_engineering
ai_android
developer_experience
career_lesson
leadership_lesson
```

Recommended distribution:

```text
40% technical
20% Android/Kotlin news
15% fintech/security
10% AI + Android
10% career/experience
5% leadership
```

---

# 14. Quality Review Agent

Before publishing, run an independent quality check.

Evaluate:

```text
technical_accuracy
naturalness
originality
usefulness
readability
linkedin_fit
repetition
ai_like_language
```

Example:

```json
{
  "technical_accuracy": 9,
  "naturalness": 8,
  "originality": 9,
  "usefulness": 8,
  "linkedin_fit": 8,
  "ai_like_language": 2,
  "publish": true
}
```

Minimum requirements:

```text
technical_accuracy >= 8
naturalness >= 8
originality >= 7
usefulness >= 7
linkedin_fit >= 7
ai_like_language <= 3
```

If the post fails:

```text
FAIL
 ↓
Rewrite
 ↓
Review again
```

Maximum:

```text
3 attempts
```

If all attempts fail:

```text
SKIP POST
```

Do NOT notify the user for normal quality failures.

---

# 15. Image Decision

Do not generate an image for every post.

The agent should decide:

```text
Does an image add meaningful value?
```

Use an infographic for:

* architecture
* comparison
* workflow
* technical concept
* step-by-step explanation
* security concepts
* performance concepts

Do not use an image for:

* simple opinion
* short observation
* personal lesson
* simple announcement

If image generation fails:

```text
publish text-only
```

Do not block the entire workflow.

---

# 16. LinkedIn Publisher

Preserve the existing LinkedIn implementation from the base repository
where possible.

Required secrets:

```text
LINKEDIN_ACCESS_TOKEN
LINKEDIN_PERSON_ID
```

Never hardcode these values.

Use GitHub Secrets.

Publishing flow:

```text
Generate
 ↓
Validate
 ↓
Publish
 ↓
Receive LinkedIn response
 ↓
Verify success
 ↓
Save post ID
```

---

# 17. Duplicate Protection During Publishing

Before retrying a failed LinkedIn request:

```text
CHECK WHETHER THE POST WAS ALREADY CREATED
```

This is extremely important.

Do not blindly retry a POST request because it may create duplicate
LinkedIn posts.

Flow:

```text
LinkedIn timeout
      |
      v
Check publication status
      |
 +----+----+
 |         |
Found     Not found
 |         |
Save      Retry
 |         |
DONE      Verify
```

---

# 18. Error Handling

Errors must be classified.

## Recoverable errors

Examples:

```text
RSS unavailable
temporary network failure
Gemini timeout
image generation failure
temporary LinkedIn timeout
```

Action:

```text
retry
fallback
skip source
continue
```

Do not notify the user immediately.

---

# 19. Authentication Errors

Examples:

```text
401
403
invalid token
expired token
missing OAuth permission
```

Flow:

```text
Detect authentication problem
        ↓
Retry only when appropriate
        ↓
If still failing
        ↓
Stop publishing
        ↓
Notify user
```

Notification example:

```text
LinkedIn automation requires attention.

Reason:
LinkedIn access token appears to be expired or invalid.

No post was published.

Action required:
Refresh LinkedIn authentication.
```

---

# 20. Missing Secrets

At startup validate:

```text
GEMINI_API_KEY
LINKEDIN_ACCESS_TOKEN
LINKEDIN_PERSON_ID
```

Optional:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

If required credentials are missing:

```text
STOP
```

Notify user.

Do not attempt to run partially.

---

# 21. Notifications

Use Telegram as the emergency notification channel.

The user should NOT receive daily approval requests.

Only notify for:

```text
missing credentials
expired credentials
LinkedIn authentication failure
repeated LinkedIn 403
critical configuration failure
repeated system failure
```

Optional daily report:

```text
POSTING REPORT

Status: SUCCESS
Topic: Kotlin Flow...
Published: 09:04 IST
LinkedIn ID: xxxx
```

Make daily reporting configurable:

```json
{
  "daily_report": false
}
```

---

# 22. Autonomous Recovery Policy

Implement:

```python
if credentials_missing:
    notify_user()
    stop()

if source_failed:
    use_next_source()

if topic_duplicate:
    choose_next_topic()

if research_failed:
    use_fallback_source()

if generation_failed:
    retry()

if quality_failed:
    rewrite()

if image_failed:
    continue_without_image()

if linkedin_timeout:
    verify_before_retry()

if linkedin_401:
    notify_user()
    stop()

if linkedin_403:
    retry_once()
    if_failed:
        notify_user()
        stop()

if successful:
    save_history()
```

---

# 23. GitHub Actions

Create:

```text
.github/workflows/linkedin-agent.yml
```

Default:

```yaml
name: Autonomous LinkedIn Agent

on:
  schedule:
    - cron: "30 3 * * *"
  workflow_dispatch:
```

The cron above represents approximately:

```text
09:00 IST
```

The workflow must support manual execution for debugging.

---

# 24. Runtime Flow

Main entry point:

```text
scripts/main.py
```

Execution:

```text
1. Load configuration
2. Validate environment
3. Load history
4. Fetch sources
5. Select topic
6. Check duplicates
7. Research
8. Generate draft
9. Review draft
10. Rewrite if necessary
11. Decide image requirement
12. Generate image if required
13. Publish to LinkedIn
14. Verify publication
15. Save history
16. Log result
17. Exit
```

---

# 25. Logging

Use structured logs.

Example:

```text
[INFO] Agent started
[INFO] Sources loaded: 7
[INFO] Topics discovered: 23
[INFO] Selected topic: ...
[INFO] Duplicate check: PASS
[INFO] Research completed
[INFO] Draft generated
[INFO] Quality score: 8.6
[INFO] Image required: YES
[INFO] Image generated
[INFO] Publishing to LinkedIn
[INFO] LinkedIn publication successful
[INFO] History updated
[INFO] Agent completed
```

Errors:

```text
[ERROR] LinkedIn authentication failed
[ACTION] User intervention required
```

Never log secrets or access tokens.

---

# 26. State Management

The agent must remember previous executions.

Minimum state:

```text
last_successful_run
last_published_post
last_selected_topics
failed_topics
published_topics
```

Recommended:

```text
SQLite
```

instead of JSON when practical.

The system should remain functional even after GitHub Actions starts
on a new runner.

Persistent state must therefore be stored in a persistent location
such as the repository, artifact storage, or another suitable
persistent storage mechanism.

Do NOT rely only on the local GitHub Actions filesystem.

---

# 27. Cost Optimization

Target:

```text
₹0/month whenever possible
```

Use:

```text
GitHub Actions
Gemini free tier where available
RSS
GitHub
Telegram
Open-source Python libraries
```

Do not make paid APIs mandatory.

Exa should be optional.

If Exa is unavailable:

```text
RSS + public sources
```

must still allow the system to operate.

---

# 28. Security

Never commit:

```text
.env
API keys
OAuth tokens
LinkedIn tokens
Telegram tokens
credentials
```

Add to `.gitignore`:

```text
.env
.env.*
*.secret
credentials.json
token.json
```

Use:

```text
GitHub Secrets
```

for production credentials.

---

# 29. Migration from Postiz

Do NOT immediately disable Postiz.

Migration sequence:

```text
Week 1

Postiz:
    existing system

New Agent:
    preview/testing only
```

Then:

```text
Week 2

Postiz:
    OFF

New Agent:
    1 post/day
    autonomous
```

Keep the Postiz configuration/export available for rollback.

If the new system fails repeatedly:

```text
Rollback to Postiz
```

---

# 30. Testing Strategy

Before enabling automatic publishing:

## Test 1

Run:

```bash
python scripts/main.py --preview
```

Verify:

* topic selection
* research
* post generation
* quality review
* image generation
* no LinkedIn publication

## Test 2

Run LinkedIn publishing manually.

Publish exactly one test post.

## Test 3

Run GitHub Action manually.

## Test 4

Enable scheduled execution.

## Test 5

Verify duplicate protection.

## Test 6

Simulate expired LinkedIn token.

Expected:

```text
No post
Telegram notification
Workflow stops
```

## Test 7

Simulate Gemini failure.

Expected:

```text
Retry
Fallback
No unnecessary notification
```

## Test 8

Simulate image generation failure.

Expected:

```text
Text-only post
```

---

# 31. Acceptance Criteria

The migration is complete only when all conditions are satisfied:

* [ ] Postiz is no longer required
* [ ] Agent runs through GitHub Actions
* [ ] Personal LinkedIn publishing works
* [ ] One post/day works
* [ ] Android-focused topics are selected
* [ ] Duplicate topics are rejected
* [ ] Personal knowledge is used when relevant
* [ ] AI does not invent personal experience
* [ ] Posts pass quality checks
* [ ] AI-like writing is minimized
* [ ] Images are generated only when useful
* [ ] Image failure does not stop publishing
* [ ] LinkedIn timeout does not create duplicates
* [ ] Authentication errors notify the user
* [ ] Missing keys notify the user
* [ ] Temporary failures recover automatically
* [ ] Secrets are never committed
* [ ] Persistent history survives GitHub Action runs
* [ ] Manual workflow execution works
* [ ] Postiz can be disabled safely
* [ ] Rollback procedure exists

---

# 32. Antigravity Instructions

When implementing this project:

1. Inspect the existing repository first.
2. Do not rewrite working code unnecessarily.
3. Create a migration branch.
4. Make small, testable changes.
5. Run existing tests after every major change.
6. Preserve the current LinkedIn implementation unless there is a
   concrete reason to replace it.
7. Do not hardcode credentials.
8. Do not create fake API keys.
9. Do not assume LinkedIn permissions exist.
10. Detect missing permissions and notify the user.
11. Prefer free/open-source components.
12. Keep paid APIs optional.
13. Implement autonomous recovery.
14. Never publish duplicate posts.
15. Never invent the user's personal experience.
16. Never require daily human approval.
17. Ask the user for intervention only when the system genuinely
    cannot continue without credentials, authorization, or
    configuration.

---

# 33. Definition of "Autonomous"

The system is considered autonomous when:

```text
No daily approval
No daily manual execution
No daily topic selection
No daily writing
No daily image creation
No daily LinkedIn publishing
No daily monitoring
```

The user should only be interrupted when:

```text
Credentials
Authorization
Permissions
Critical unrecoverable errors
```

require human action.

Everything else must be handled automatically.

---

# 34. Final Target

The final system should behave like:

```text
                    YOU
                     |
                     |
             Only when blocked
                     |
                     v
              +-------------+
              | Telegram    |
              | Alert       |
              +-------------+

                     ^
                     |
              Autonomous Agent
                     |
       +-------------+-------------+
       |             |             |
    Research      Writing       Review
       |             |             |
       +-------------+-------------+
                     |
                  Image
                     |
                     v
                 LinkedIn
                     |
                     v
                  History
```

The goal is not simply to automate posting.

The goal is to build a reliable autonomous content agent that can
continuously discover, evaluate, create, publish and remember LinkedIn
content without requiring daily involvement.
