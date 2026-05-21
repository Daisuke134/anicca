# US-001: Trend Research + Idea Selection

Generated: 2026-03-03
Source: idea-generator SKILL.md (rshankras) + 5 Brainstorming Lenses

---

## Developer Profile (Factory Fixed)

| Item | Value |
|------|-------|
| Platform | iOS, Swift/SwiftUI |
| Skills | Swift, SwiftUI, SwiftData, WidgetKit, PhotosKit, Foundation Models |
| Time | Solo dev, 1-day intensive build |
| Model | Subscription ($4.99–$9.99/mo) |
| Constraints | No backend (or minimal), no external APIs required |

---

## Five Brainstorming Lenses Applied

| Lens | Ideas Generated |
|------|----------------|
| 1: Skills & Interests | Photo journal, habit widgets, breathing coach, SwiftData-powered apps |
| 2: Problem-First | Food waste tracker, screen time coaching, posture reminders |
| 3: Technology-First | Foundation Models reflection, DeviceActivity coaching, WidgetKit live habits |
| 4: Market Gap | Minimal gratitude journal, photo-first diary, focused single-tool utilities |
| 5: Trend-Based | "Quiet flex" wellness apps, on-device AI privacy, daily companion-style tools |

Sources:
- [iOS App Trends 2026 – Apptunix](https://www.apptunix.com/blog/apple-app-store-statistics/)
- [TikTok 2026 Trend Predictions](https://www.tiktok.com/en/trending/detail/tiktok-unveils-2026-trend-predictions)
- [Apple Foundation Models Framework](https://developer.apple.com/documentation/FoundationModels)
- [Top Earning App Categories 2026 – ASO World](https://asoworld.com/en/blog/top-earning-apps-in-2026-which-app-categories-make-the-most-money/)
- [Habit Tracker Complaints 2026 – AFFiNE](https://affine.pro/blog/best-habit-tracker-apps)

---

## Shortlist (5 Ideas Evaluated)

### Rank 1 — MomentLog: 3-Photo Daily Gratitude Journal

| Field | Value |
|-------|-------|
| **idea** | MomentLog |
| **lens** | Market Gap + Trend-Based |
| **one_liner** | Pick 3 photos from today — your day becomes a visual gratitude journal with AI captions |
| **platform** | iOS |
| **problem_statement** | Journaling apps demand writing. Most users quit in days. $1,500+/year food and moment waste because people never pause to notice what was good. Visual-only gratitude has zero dedicated quality apps. |
| **target_user** | 25–35 year olds who know journaling is good for them but find writing a barrier |
| **monetization_model** | Freemium — free for 7-day history, $4.99/mo or $29.99/yr for unlimited history + AI captions + Year-in-Review |
| **competition_notes** | Day One is complex and expensive ($34.99/yr). Gratitude apps are text-heavy. No quality app exists for "3 photos = done". |
| **mvp_scope** | Pick up to 3 photos, SwiftData storage, daily WidgetKit reminder, year timeline view, optional Foundation Models AI caption |
| **next_step** | Implement as primary app |

**Feasibility Scores:**

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Solo Dev Scope | 9 | PhotosKit + SwiftData + WidgetKit — all standard. 3–4 week full build |
| Platform API Fit | 9 | PhotosKit, WidgetKit, Foundation Models, SwiftData — pure Apple stack |
| Monetization Viability | 7 | Visual journals = clear premium tier (Year-in-Review), AI captions justify sub |
| Competition Density | 7 | Day One dominates complex journals; no quality minimal photo journal exists |
| Technical Fit | 9 | All APIs well-documented, no backend, no external dependencies |

**Overall Score: 8.3**
Formula: (1.5×9 + 1.5×9 + 9 + 7 + 7) / 6 = 50/6 = **8.3**

Source: [AI Journaling Apps Compared 2026 – Reflection.app](https://www.reflection.app/blog/ai-journaling-apps-compared) / Key quote: "Most AI journals demand extensive writing — the barrier that kills retention"

---

### Rank 2 — DayPulse: On-Device AI Daily Check-In

| Field | Value |
|-------|-------|
| **idea** | DayPulse |
| **lens** | Technology-First + Trend-Based |
| **one_liner** | Tap once, tell the AI how you feel, get a personalized reflection — no cloud, no data sharing |
| **platform** | iOS |
| **problem_statement** | AI wellness companions use cloud APIs (privacy risk, ongoing cost). Apple Foundation Models enable on-device AI for free — almost no app leverages this for daily check-ins yet. |
| **target_user** | Privacy-conscious 25–35 year olds who want AI guidance without sending data to servers |
| **monetization_model** | $6.99/mo or $39.99/yr. On-device AI justifies premium: "AI that never leaves your phone" |
| **competition_notes** | Rosebud, Mindsera, Reflectly all use cloud. No quality on-device-only AI reflection app exists. |
| **mvp_scope** | Daily check-in prompt → Foundation Models response → SwiftData history → WidgetKit daily prompt |
| **next_step** | Fallback if MomentLog name taken |

**Overall Score: 8.2**

Source: [How developers are using Apple's local AI models – TechCrunch](https://techcrunch.com/2025/10/03/how-developers-are-using-apples-local-ai-models-with-ios-26/) / Key quote: "no API keys, no cloud costs, no internet required"

---

### Rank 3 — FreshCount: Food Expiry Tracker (VisionKit)

| Field | Value |
|-------|-------|
| **idea** | FreshCount |
| **lens** | Problem-First |
| **one_liner** | Scan groceries when you buy them, get reminders before they expire, cut food waste |
| **platform** | iOS |
| **problem_statement** | US households waste $1,500+/year in food. No quality consumer iOS app solves this with VisionKit barcode scanning. |
| **target_user** | Families and budget-conscious 25–40 year olds who grocery shop regularly |
| **monetization_model** | $2.99/mo or $19.99/yr for unlimited items + recipe suggestions |
| **competition_notes** | Fridge Pal and similar apps are outdated (last update 2+ years ago). Market gap is real. |
| **mvp_scope** | VisionKit barcode scan → product name lookup → expiry date set → notification reminders |

**Overall Score: 7.7**

Source: [Best App Ideas 2026 – BigIdeasDB](https://bigideasdb.com/best-app-ideas-2026-for-app-store-google-play) / Key quote: "Home users throw away $1,500+ of food annually"

---

### Rank 4 — HabitWidget: Minimal Habit Tracker with Interactive Widgets

| Field | Value |
|-------|-------|
| **idea** | HabitWidget |
| **lens** | Skills & Interests + Technology-First |
| **one_liner** | Track up to 5 habits directly from your home screen — never open the app |
| **platform** | iOS |
| **problem_statement** | Users quit habit trackers because opening an app is friction. Interactive Widgets (iOS 17+) allow tap-to-complete directly from home screen. No dominant app fully leverages this. |
| **target_user** | 20–35 year olds who want minimal friction habit tracking |
| **monetization_model** | $3.99/mo for unlimited habits + themes + Live Activities |
| **competition_notes** | Streaks ($4.99 one-time) and Habitify ($9.99/mo) exist but don't focus on widget-first UX |

**Overall Score: 7.5**

Source: [Habit Tracker Apps – Fhynix](https://fhynix.com/habit-tracker-apps/) / Key quote: "The pattern repeats: someone sets up 15 habits, uses it a week, never opens again"

---

### Rank 5 — FocusCoach: Screen Time Coaching via DeviceActivity API

| Field | Value |
|-------|-------|
| **idea** | FocusCoach |
| **lens** | Technology-First |
| **one_liner** | Your iPhone's Screen Time data + on-device AI = personalized digital wellness coaching |
| **platform** | iOS |
| **problem_statement** | Screen Time shows data but offers no coaching. DeviceActivity API is underutilized by indie devs. |
| **target_user** | Phone-addicted 20–35 year olds who want to reduce screen time but lack accountability |
| **monetization_model** | $5.99/mo subscription |
| **competition_notes** | No quality coaching app uses DeviceActivity + Foundation Models together |

**Overall Score: 7.2**

Note: DeviceActivity entitlement requires Apple review, adding complexity for 1-day build.

---

## Ideas Filtered Out

| Idea | Lens | Reason |
|------|------|--------|
| AI Therapy App | Trend-Based | Legal/liability risk. Reflection, Rosebud, Mindsera dominate. WEAK competition density. |
| Gym Crowd Tracker | Problem-First | Requires backend + crowdsource mechanics. Solo dev scope = WEAK. |
| AR Try-On Fashion | Technology-First | Requires fashion inventory API. Too complex for 1-day build. |
| AI Personal Trainer | Skills | Fitbod, Future, Hevy dominate. WEAK competition density. 6+ month build. |

---

## Recommendation

**Build MomentLog (Rank 1, Score 8.3).**

MomentLog wins because:
1. **Zero writing barrier** — picking photos takes 10 seconds, not 10 minutes. Solves the #1 reason journaling apps fail.
2. **No backend required** — PhotosKit + SwiftData + WidgetKit = pure on-device Apple stack.
3. **Clear premium tier** — Year-in-Review (like Spotify Wrapped for your life) justifies subscription.
4. **Trend alignment** — "quiet flex" aesthetic, TikTok's 2026 prediction of self-reflection content.
5. **Market gap** — Day One is overpriced/complex, no quality minimal photo journal exists.

Sources:
- [TikTok 2026 Trend Predictions](https://www.tiktok.com/en/trending/detail/tiktok-unveils-2026-trend-predictions) / Key quote: "inner strength and self growth, wellness, healing, moments of self-transformation"
- [AI Journaling Apps 2026 – Holstee](https://www.holstee.com/blogs/mindful-matter/best-journaling-apps) / Key quote: "visual journaling and photo-based reflection remain largely underserved"
- [Apple Foundation Models – Newsroom](https://www.apple.com/newsroom/2025/09/apples-foundation-models-framework-unlocks-new-intelligent-app-experiences/) / Key quote: "AI inference that is free of cost"
