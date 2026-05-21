
What Is Clawdbot? (And Why People Are Losing Their Minds Over It) 
Imagine if Siri actually worked.
Like, remembered what you told it. Did real tasks. And messaged YOU when something important happened.
That's Clawdbot.
People are losing their minds over this thing - buying Mac Minis, building server setups, overcomplicating everything.
You don't need any of that. Let me break it down simply.

What Is Clawdbot?
Think of it like this:
ChatGPT and Claude live on a website. You go to them, type something, get a response, copy-paste it somewhere else.
Clawdbot lives in your phone.
It's an AI assistant that works inside the apps you already use - WhatsApp, Telegram, iMessage, Slack, Discord. You text it like a friend. It texts you back.
Same conversation whether you're on your phone, laptop, or tablet. It remembers everything you've ever told it.
That's it. That's the core idea.

Why Is Everyone Talking About It?
Three reasons:
1. It Actually Remembers Things
Ask Siri what you told it yesterday. It has no idea.
Clawdbot remembers your last conversation. Your preferences. That random thing you mentioned two weeks ago. It builds context over time and gets better at helping you.
This sounds basic. No mainstream assistant has figured it out until now.
2. It Messages YOU First
This is the big one.
Normal AI waits for you to open it. Clawdbot can reach out proactively:
"Hey, you have 3 urgent emails and a meeting in 20 minutes"
"That stock you're watching just dropped 5%"
"Weather's bad tomorrow - might want to reschedule"
It's like having a personal assistant who actually pays attention.
3. It Can Do Things On Your Computer
Not just answer questions. Actually do stuff.
Fill out forms
Send emails
Move files around
Run programs
Control your browser
One person rebuilt their entire website while watching Netflix in bed. Never opened a laptop. Just texted Clawdbot what to do.

The Mac Mini Myth
Here's where people are going wrong.
I've seen setups with 3 Mac Minis stacked on desks. Raspberry Pis everywhere. People treating this like they need a data center.
You don't.
Clawdbot runs on a $5/month server. That's less than a coffee.
The technical requirements:
A cheap cloud server (or your own computer)
Node.js installed (free software)
A Claude or ChatGPT subscription
That's the whole thing. No Mac Mini farm required.
How Does It Actually Work?
Simple version:
Clawdbot runs on a computer (yours or a $5 cloud server)
It connects to your messaging apps
You text it, it responds
It can also do tasks on that computer
Slightly more technical version:
There's a "Gateway" that runs in the background. Think of it like a switchboard operator. Messages come in from WhatsApp, Telegram, wherever. The Gateway routes them to the AI. The AI thinks, responds, and can also trigger actions - like opening a browser or running a script.
Everything stays on your machine. Your data doesn't go to some company's server (except for the AI calls to Claude/ChatGPT).

What Can You Actually Do With It?
Real examples from people using it:
Morning Briefings Wake up to a summary: your important emails, calendar for the day, tasks you need to handle. Delivered to your phone before you get out of bed.
Health Tracking "Connect to my WHOOP and give me daily summaries." Took someone 5 minutes to set up. Now they get fitness insights automatically.
Email Management "Unsubscribe me from all these newsletters." It logs into your email, finds the junk, handles it.
Research Assistant "Find me the 5 best restaurants near my hotel in Tokyo." It searches, compares, gives you options - all in a text thread.
Task Automation "Every Friday at 5pm, send me a summary of what I accomplished this week." Set it once, it runs forever.
The Wild Stuff One user has Clawdbot write custom meditations, generate audio with AI voices, add ambient music, and deliver them every morning. Fully automated.
Who Made This?
Peter Steinberger - a developer from Vienna who "came back from retirement to mess with AI."
The mascot is a space lobster named Clawd. The community calls it "early AGI." Andrej Karpathy (one of the most respected AI researchers) endorsed it.
It's open source, meaning anyone can see the code, improve it, or build on top of it. The Discord community has 30+ contributions per day.
How Is It Different From ChatGPT?
ChatGPT is a chat window. Clawdbot is an assistant that lives in your life.
How Is It Different From Siri?
Siri has the memory of a goldfish. Clawdbot has a brain.
Do I Need To Be Technical?
Honestly? A little bit.
If you can follow instructions and copy-paste commands, you can set it up. It's not "click a button and done" - but it's not rocket science either.

here all the documentation: 

https://clawd.bot
The install is one line:
curl -fsSL https://clawd.bot/install.sh | bash
Then you follow a setup wizard that walks you through connecting your messaging apps.
If that sounds intimidating, wait a few months. The community is making it easier every week. Or find someone technical to help you set it up once—after that, you just use it like any other messaging app.
What Does It Cost?
The software: Free (open source)
The server: $5-50/month depending on what you use
$5/month Hetzner VPS works for most people
Or just run it on your own computer for $0
The AI: $20-100/month
Claude Pro: $20/month
Claude Max: $100/month (for heavy users)
Or use API keys (pay per use)
Total: $25-150/month for a personal AI assistant that actually works.
Compare that to the "AI consultants" charging $10K to set up a basic chatbot.

Should You Use It?
Yes if:
You want an AI assistant that remembers you
You're tired of copy-pasting between ChatGPT and everything else
You want proactive notifications and automation
You're comfortable with basic technical setup (or know someone who is)
Maybe wait if:
You need something that works perfectly out of the box
You're not comfortable running commands in a terminal
You need enterprise-level support and guarantees
This is early. It's moving fast. Bugs get fixed in hours. Features ship weekly.
But that's also why the people using it now are getting ahead.

The Bottom Line
Clawdbot is the AI assistant we were promised a decade ago.
It lives in your messaging apps. It remembers everything. It messages you first. It does real tasks.
And you don't need a room full of Mac Minis to run it.
$5 server. One install command. Done.
The assistant should come to you - not the other way around.
That's Clawdbot.