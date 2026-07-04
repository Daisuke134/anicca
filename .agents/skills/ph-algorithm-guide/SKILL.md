---
name: ph-algorithm-guide
description: Understand how the Product Hunt ranking algorithm works. Use this skill to optimize your launch strategy based on known algorithm factors and behaviors.
---

# Product Hunt Algorithm Guide

This skill explains how Product Hunt's ranking algorithm works, helping you optimize your launch strategy based on publicly known factors.

## When to Use This Skill

- Planning your launch strategy
- Understanding why rankings change
- Optimizing for algorithm factors
- Diagnosing ranking issues
- Setting realistic expectations

## Algorithm Fundamentals

### Key Insight
**Upvotes ≠ Points**

Product Hunt CTO Mike Kerzhner confirmed: "There is not a 1:1 correspondence between upvotes and points."

### What This Means
- Not all votes count equally
- Account quality matters
- Engagement quality matters
- Timing patterns matter

## Known Ranking Factors

### Factor 1: Vote Weight

**Higher Weight Votes:**
- Older accounts (months/years old)
- Active accounts (regular engagement)
- Diverse activity (not just voting)
- Organic voting pattern

**Lower Weight Votes:**
- New accounts (recently created)
- Inactive accounts (created but unused)
- Single-purpose accounts
- Suspicious patterns

**Potentially Discounted:**
- Brand new accounts
- Accounts created same day
- Bulk votes from same source
- Coordinated voting patterns

---

### Factor 2: Engagement Depth

**Positive Signals:**
- Thoughtful comments
- Discussion threads
- Maker responses
- Question-answer exchanges

**Why It Matters:**
- Comments indicate genuine interest
- Discussions show community value
- Engagement harder to fake than votes

---

### Factor 3: Velocity Pattern

**What Algorithm Watches:**
- Rate of upvote accumulation
- Time distribution of votes
- Spikes vs steady growth
- Natural vs artificial patterns

**Healthy Pattern:**
```
Hour 1: [████████░░] 40 votes
Hour 2: [██████░░░░] 35 votes
Hour 3: [███████░░░] 38 votes
Hour 4: [█████████░] 45 votes
```

**Suspicious Pattern:**
```
Hour 1: [██████████] 150 votes (spike!)
Hour 2: [█░░░░░░░░░] 5 votes
Hour 3: [█░░░░░░░░░] 3 votes
Hour 4: [█░░░░░░░░░] 2 votes
```

---

### Factor 4: First 4 Hours

**Special Period:**
- Rankings randomized initially
- Vote counts hidden publicly
- Algorithm observing patterns
- Critical for initial position

**After 4 Hours:**
- Rankings become vote-based
- Position reflects accumulated strength
- Top positions attract organic traffic
- Momentum becomes visible

---

### Factor 5: Account Relationships

**Flagged Patterns:**
- Votes from connected accounts
- Same IP address votes
- Same device votes
- Employee/team votes (weighted less)

**Clean Patterns:**
- Diverse geographic sources
- Independent account histories
- Organic discovery paths

## How Rankings Are Determined

### The Daily Cycle

```
12:01 AM PST → Day begins
    ↓
Hours 0-4: Randomized ranking
    ↓
Hour 4+: Algorithm-sorted ranking
    ↓
Throughout day: Continuous re-ranking
    ↓
11:59 PM PST → Final rankings locked
    ↓
Awards: POTD, Top 5, etc.
```

### Ranking Formula (Approximate)

```
Score = (Weighted Votes × Quality Multiplier)
      + (Engagement Depth Bonus)
      - (Spam/Manipulation Penalty)
```

Where:
- Weighted Votes = Sum of all votes adjusted by account quality
- Quality Multiplier = Based on product profile completeness
- Engagement Depth = Comments, discussions, maker activity
- Penalty = Deductions for suspicious patterns

## Optimizing for the Algorithm

### Do: Quality Over Quantity

**Instead of:**
Getting 200 votes from low-quality accounts

**Aim for:**
Getting 100 votes from active, established accounts

### Do: Stagger Engagement

**Instead of:**
All supporters voting at 12:01 AM

**Aim for:**
Supporters spread across 5-6 waves over 24 hours

### Do: Encourage Real Comments

**Instead of:**
"Please upvote!"

**Aim for:**
"Would love your honest thoughts in the comments!"

### Do: Respond to Everything

**Why:**
- Shows you're present
- Creates discussion threads
- Signals genuine launch
- Builds engagement depth

## Algorithm Behaviors

### What Triggers Scrutiny

1. **Vote Velocity Spikes**
   - Sudden burst of votes
   - Then dramatic dropoff
   - Unnatural acceleration

2. **Account Patterns**
   - Multiple new accounts
   - Same creation timeframe
   - Similar activity patterns

3. **Geographic Clustering**
   - All votes from one location
   - No geographic diversity
   - Pattern doesn't match product

4. **Timing Uniformity**
   - Votes in exact intervals
   - Automated-looking patterns
   - Unnatural consistency

### What the Algorithm Rewards

1. **Organic Growth**
   - Steady accumulation
   - Natural peaks and valleys
   - Timezone-appropriate waves

2. **Diverse Sources**
   - Various account ages
   - Different activity levels
   - Geographic spread

3. **Deep Engagement**
   - Multiple comments
   - Discussion threads
   - Question-answer pairs

4. **Maker Presence**
   - Quick responses
   - Genuine conversation
   - Helpful attitude

## Featured vs Unfeatured

### Getting Featured

**Requirements (Unofficial):**
- Product is clearly explained
- Meets category standards
- No obvious manipulation
- Complete profile

**Helps Your Chances:**
- Quality visuals
- Clear value proposition
- Active maker engagement
- Previous PH presence

### Getting Unfeatured

**Common Causes:**
- Vote manipulation detected
- Spam reports received
- Policy violations
- Low-quality product

**Recovery:**
- Usually not possible same day
- Contact support (respectfully)
- Learn for next time

## Realistic Expectations

### What You Can Control
- Quality of your product
- Quality of your assets
- Your community engagement
- Your response rate
- Your outreach authenticity

### What You Can't Control
- Competitor strength
- Algorithm behavior
- Vote weighting details
- Featuring decisions
- Final ranking

### Healthy Mindset
```
Focus on: Building something people love
Not on: Gaming the system

Focus on: Genuine community
Not on: Vote numbers

Focus on: Long-term reputation
Not on: One-day ranking
```

## Algorithm Myths Debunked

### Myth: "Having a famous hunter guarantees success"
**Reality:** 79% of featured products are self-hunted. Hunter followers help awareness but don't guarantee votes.

### Myth: "More votes always means higher rank"
**Reality:** Vote quality matters more than quantity. 50 high-weight votes can beat 100 low-weight votes.

### Myth: "The first hour determines everything"
**Reality:** First 4 hours matter, but the entire 24 hours count. Late momentum can overcome slow starts.

### Myth: "Weekend launches are easy wins"
**Reality:** Lower competition, but also lower traffic. Easier badge, fewer users.

### Myth: "The algorithm is random/unfair"
**Reality:** It's designed to surface genuinely interesting products. Work with it, not against it.

## Output Format

```
ALGORITHM OPTIMIZATION CHECK

VOTE QUALITY:
- Expected high-weight votes: [Number]
- Expected low-weight votes: [Number]
- Risk of discounted votes: [Low/Medium/High]

ENGAGEMENT PLAN:
- Comment depth strategy: [Description]
- Maker response plan: [Description]
- Discussion seeding: [Description]

VELOCITY PATTERN:
- Wave 1 timing: [Time]
- Wave 2 timing: [Time]
- Expected distribution: [Natural/Concerning]

RISK FACTORS:
- [Risk 1]: [Mitigation]
- [Risk 2]: [Mitigation]

REALISTIC TARGETS:
- Conservative estimate: [Rank range]
- Optimistic estimate: [Rank range]
```
