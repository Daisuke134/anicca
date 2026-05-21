#1 — Most important metric is App Install → Paywall View. If you aren't already tracking this, start ASAP. @Superwall sees revenue move (almost linearly) with this metric. Double this metric, double your revenue.

#2 — Second most important metric? Unsurprisingly, paywall views per unsubscribed user. @Superwall doesn't see diminishing returns until around the 7th paywall view on average.

#3 — Best setup to start with: Paywall BEFORE Onboarding + Paywall AFTER Onboarding + Paywall EVERY App Open.

#4 — Send push / local notifications out daily. Each app open = paywall view if you follow tip #3. More paywall views = more revenue according to tip #2.

#5 — Price testing isn't about being the cheapest. It's about finding the price/retention tradeoff. Usually users you out-price wouldn't have retained anyway

#6 — Web checkout is killer. Not for paid user acquisition, but for marketing discounts to installs who don't subscribe. You should have a URL like appname.com/checkout?app_u... that deep links to your app after purchase

#7 — Run drip campaigns. Lower prices on day 0, day 3, day 7, day 14, day 30. Send reminders via push but also SMS or email (but link to web checkout for those). Offer a 30% discount, and keep decreasing price wrt time.

#8 — To determine the time of your first discount notification, analyze how long it takes for 95% of your trials to come in. Usually it's 1hr. Send a stripe checkout link after this time with 30% off.

#9 — Stripe retention is ~2x that of your IAP. I know, it's crazy. Don't use dark patterns. Add a way to cancel in settings. Email receipts.

#10 — Run sales. They can account for 20% of total revenue. Christmas, Black Friday, New Years, Memorial Day, Labor Day, Spring Sale, Fall Sale, Summer Sale, Father's Day, Mother's Day. 50% off.


#11 — Price testing is useful but don't go overboard. Rarely do you see a revenue boost of > 10%. First test weekly prices. Then monthly. Then annual. Analyze cohorts over time.

#12 — For weekly, test $1.99, $2.99, $3.99, $4.99, $7.99, $9.99. Test 3 and 7 day trials. When you find a winner, go onto monthly.

#13 — For monthly, test $4.99, $7.99, $9.99, $12.49, $14.99, $19.99, $29.99, $49.99. Test 3 or 7 day trials. When you find a winner, go onto yearly.

#14 — For yearly, test $29.99, $39.99, $49.99, $59.99, $89.99, $119.99, $129.99, $149.99, $189.99. Test 3 and 7 day trials.

#15 — Above prices are not random. Not only are they almost always the prices @Superwall sees win, nearly all have a nice weekly or monthly counterpart. $119.99 is only $10/mo. $129.99 is only $2.49/week. Tell this to your users.

#16 — When you find a yearly winner, stick with it. Analyze monthly and weekly cohorts over time. Make a decision yearly subscription starts. Compare 12 months of weekly / monthly v yearly subscription starts.

#17 — If you want to offer multiple products, try a weekly or monthly price that is 2x as expensive as the annual, without a trial. Market the annual trial as 50% off. For ex: $10/mo (no trial) vs $59.99/yr ($5/mo after 7 days free, 50% off).

#18 — For a built-in winback campaign, hide a cheaper priced plan in your subscription group. offer users $89.99/yr in app, but add a $59.99/yr product called Secret Discount. When users go to cancel, they'll see the discount. I've seen setups increase revenue by 10%.

#19 — Surveys are important. you MUST be able to track results over time - otherwise your surveys are pointless. You must also be able to change questions very easily. Here's how...

#20 — Simplest setup is to show typeform surveys on app open. Add app user id as a hidden parameter. This lets you change questions over time.'

#21 — Add a webhook to your typeform to send results to @mixpanel / @amplitude_hq. This lets you track results over time in a tool you already use.

#22 — Send two types of surveys out. (1) trial cancel survey, (2) product market fit survey. Use local notifications or RevenueCat + push notif service for trial cancel surveys.

#23 — For trial cancel survey, ask the following (1) why did you cancel? (Multiple choice) (2) how can we improve (free response). End with a discount via stripe checkout. To analyze free response, use a word cloud.

#24 — For PMF, ask in-app after a 3rd use of a core feature. Use @rahulvohras survey.

#25 — Get flooded w. written reviews: in your PMF survey, ask users why they love your app. At the end, show them back their answer and ask to paste it as a review.

#26 — Get flooded w. ratings: 1st ask immediately after onboarding. This is a bit of a dark pattern, but users read this as "how is your experience going so far?" and are in a tapping mood by the time they are done with onboarding.

#27 — After your first rating request, only ask for an in app rating after the use of a core feature. Only ask if the app version is different from the last time you asked for a rating.

#28 — Optimizing onboarding is hard. You must balance completion rates and paywall conversion rates. Higher completion rate = more paywall views. Longer onboarding = higher paywall conv rates (due to a sunk cost bias).

#29 — Personal info like name, age, email, phone + any app permissions have the lowest completion rates. Offload as much as possible to after a paywall view.

#30 — To optimize onboarding, sort each step in descending completion rate. For ex, if step 4 → 5 is highest with 99.5% conv rate, make it first. Lowest converting steps will have a higher chance of converting at the end due to their Sunk Cost bias.

#31 — First paywall test should test your messaging. This will inform everything from feature development to later paywall iterations. Start with a headline, small paragraph and a checklist of features. 1 juicy purchase button at the bottom. No images, No scrolling, Nothing else.

#32 — It's much easier to test paywall copy than to build a new feature. Its okay to allude to a new feature that hasnt been built yet in your paywall (like Tesla and their "Full Self Driving"). If you see a lift, prioritize that feature.

#33 — Once you nail messaging, move on to design. Don't test random things. Instead … survey! When your paywall is dismissed w/o paying, ask why in a free response survey. Use responses determine multiple choice Qs. Again, use a word cloud to analyze free responses.

#34 — Take your top 5 answers from #33 and create graphics / images that mitigates those fears. This is how Blinkist arrived at their free trial timeline, and why that timeline doesn't work for every app.

#35 — For example - IDK the difference between free and paid → add a table of differences. IDK when I'll be billed → add a free trial timeline. Test the addition of those elements.

#36 — Something @Superwall sees work every time - video paywall prior to onboarding. Not any video… a screen recording. Show the user exactly what they are getting with a free trial. Add 3d apple-esq graphics. Rotato is great for making them.

#37 — For paywall ideas, use paywallscreens.com — @Superwall has added over 7,200 paywalls of top apps since we acquired it, including sensor tower revenue estimates.

#38 — As you can tell, being able to remotely update your paywall is essential. @Superwall is the easiest way to remotely updated your paywall, but NOT THE ONLY WAY…

#39 — Use Firebase's Remote Config to alter pricing, text and images remotely. You can simulate a fully remotely-configurable paywall by using images as static UI elements. Just add image urls to remote config and have your paywall react accordingly.

#40 — Analytics tools. Stay away from Segment, too expensive. Use SQL and @HightouchData instead, since they let you sync historical data.

#41 — Use @Mixpanel. They charge by monthly users, not # of events like Amplitude. Don't use any analytics tools that limit the data you want to collect.

#42 — Messaging tools. Strongly consider @Intercom, @Braze or @Iterable. Do NOT use a messaging tool unless you can send push, email and SMS from the same tool. For the DIYers, Customer.io is great too.

#43 — Business tools. Use Retool. I repeat. USE RETOOL. It's a low code tool for building dashboards, admin panels and more. I even make them user facing sometimes.

#44 — If you're running UA, one of the best things I ever did was send adspend data to mixpanel with FB's Ads API and Mixpanel's Server API.

#45 — Alternatively you can use Stitch Data to get data from FB → SQL and @HightouchData to get data form SQL → @Mixpanel.

#46 — Use RevenueCat. Send your renewal / cancelation events to Mixpanel and your messaging tool. Configure it to also send revenue data to Mixpanel. This way you can see spend and revenue in one easy to use tool.

#47 — When a user cancels a trial or churns, use that event from RC (or use RC locally) to show your user a special popup. Give them a discount. If there is any sign of involuntary churn (like a credit card expiring) let the user know every app open.

#48 — If the user cancels their trial, add a floating UI above your app's homescreen showing them # of days till their trial expires. Link to a paywall with a discount.

#49 — When a user taps X on your paywall, ask for their email or phone if you don't already have it. Tell them you'll use it to send them discounts in the future. Yes, Apple allows this.

#50 — For ASO, use Apple Search Ads (ASA). The key is finding out what keywords yield high intent users, not necessarily running profitable campaigns. ASA makes this possible with keyword attribution. First use @appfigures or @apptweak to make a list of 100-200 related keywords.

#51 — Add all these keywords to campaigns and overpay for clicks if you need to. Again, don't worry about profitability, that isnt the point. Send keyword attribution to @Mixpanel and see which have highest install to paid conversion and 30d retention rates.

#52 — Keyword matches at the beginning of your Title and Subtitle carry far more weight than those at the end. That's why so many apps frontload keywords. This is the time to care LESS about your brand and MORE about being practical.

#53 — Take the top result of #51, and change your app's title to "Keyword - App Name". For example, "Personal Trainer - FitnessAI".

#54 — Use top results 2 through N in your subtitle. Don't worry about grammar, "weight lifting exercise workout" is fine.

#55 — To determine your keyword list, device a scoring formula that gives a higher score for short keywords since they make more room for others. No spaces, just commas. Place them in order.

#56 — Here's an example: ( install to paid conv rate * d30 retention * popularity ) / (keyword length * competitiveness). In general for any scoring algo, maximizing inputs go in numerator, minimizing in denominator.

#57 — Create in-app events via App Store Connect. Titles you use can rank organically in search results. BTW - if you choose a start date of around 1hr after you submit for review, your app review will be expidited.

#58 — If you change your app's title, you often times keep old ranking for keywords. Change often but not too often. 1 time a quarter until you see diminishing returns.

#59 — If you're lucky enough to have an App Store story written about your app, use this to your advantage. When you change your app's title, it changes the story's title as well. Stories continue to rank for old keywords just like your app does.

#60 — Love your users and speak to them. Add in-app chat and support. You need to understand who they are. @Intercom and @papercups_io are great. Email not so great. When users ask for refunds, help them. Offer Stripe customers discounts and free no-qs-asked refunds.

#61 — Paid UA. If you're new to ads, set aside $15K for testing. I know it's a lot - just remember, the greatest risk is taking no risk at all. Start with $500/day in spend and aim for $500/day in revenue.

#62 — Use native ad SDKs when you can. No need to use Appsflyer for facebook ads.

#63 — With FB, stick to Automated App Ads (AAA). They let you upload 50 images or videos and 5 sets of text. They handle the rest (including audience). Optimize for trial starts.

#64 — Create two AAA campaigns to begin with. Tier 1 targeting only the US. Tier 2 targeting Canada, UK, Australia and Germany. Split spend 90% Tier 1 and 10% Tier 2 countries.

#65 — Hiring influencers via TikTok is essential... but not for the reasons you think. The best creators on the planet are on TikTok right now. Use them to create content for ads, not for an ROI positive influencer campaign.

#66 — Pay out influencers based on performance if you can. Again, this isn't to make sure you're ROI positive, it's to make sure interests are aligned so their videos make for great ads.

#67 — Buy / negotiate the right to use your influencer's videos in your ads. Don't use them without asking! Use them in your AAA campaigns.

#68 — Your users write marketing copy better than yourself. Take survey responses for "what do you love most about your app?" and use it as captions for your ads.

#69 — Target users with ad creatives, not with ad settings. Its always cheaper to cast a wider net with open targeting – videos & text will attract users who resonate with the problem your solving and the solution you are advertising.

#70 — You can get a sense of what ads your competitors are running with Facebook Ads Library. All ads are public. Look at oldest running ads.

#71 — Many companies run fb ads → web onboarding → app install. They do this because attribution is better going from web conversion → fb than app → fb. They use these web conversions to create lookalike campaign to later use in trial start campaigns.

#72 — These companies are sophisticated and always run tests. Use fb ads library to grab the URL. Usually you can reverse engineer the URL to get all their experiments.

#73 — Take responses from survey question "who do you think would benefit most from using your app?" These responses are your personas. Make ad creatives for each of your personas. Your users know themselves better than you do.

#74 — If you're a conspiracy theorist, you'd agree that FB would charge higher CPMs if you report proceeds to them. Try reporting proceeds / 10 to be safe.

#75 — Making videos for ads is annoying. You don't need a fancy tool. I was spending hundreds of thousands a month on videos I made with … Keynote! Adjust canvas size, add animations, export as video.

#76 — App install attribution. Forget it. Look at blended CAC. Periodically pull back spend to see where organic is. If you're building a cash cow, consider shutting off ads when you rank for strong keywords.

#77 — Only test ads that point to web checkout if you're prepared to wager a TON of money. You'll need to spend ~100k -$1M/mo to figure out what works. Remember, web checkout works best as a tool for win-back and drip campaigns, consider sitting this one out.

#78 — Many of your competitors are TestFlight dorks. Usually you can find public betas just by googling "Competitor name testflight". You can also try joining competitor fb / reddit pages and searching "testflight" in the group.

#79 — You can use Charles to intercept competitor network traffic. Understanding their API can inform you on how to build yours. Also look for static JSON files stored on CDNs. These usually dictate A/B tests.

#80 — I've decompiled many apps in my days you can use iMazing or the mac app store to get an app on your desktop. Right click → view contents. Plists, text files and a few more are public. You'd be surprised at how much you can learn!

#81 — If you do your homework but don't hand it in, you get an F. If you build a feature but don't tell your users, you too get an F. Many apps include a CHANGELOG.md in their app bundle.

#82 — Don't hide old feature releases from new users. They aren't as curious as you think. Take screen recordings of new features as you release them. Send email + push notification tips on how to use them. Send every 48 hrs.

#83 — When talking about a feature, either in your ads, paywalls or notifications, start with the Why and how the user will feel. Colgate doesn't sell toothpaste. They sell a perfect smile, and all the confidence that comes with it.

#84 — Be personal. Make sure users know your name and your story. Add a headshot and signature in your messaging. Don't try to seem like a big faceless company. The better they know you, the more they open up.

#85 — If users feel like they know you, they will open up more about their problems. Make them feel special — you're focused on helping them personally after all.

#86 — Always listen to your customer's problems, not their solutions. This is tricky - users tend to lead with solutions to try and make your life easier. Just remember, they pay you to solve their problems, not implement their solutions.

#87 — When you solve a problem a user has with a solution they never could have thought of → you create a magical moment. Optimize for magical moments.

#88 — For example, users asked FitnessAI for gym equipment profiles for years so they can organize their equipment for different gyms. Instead we used their GPS to determine where they are, and auto-changed equipment to what they used at that gym last time.

#89 — Focus on building two types of features (1) features for your best users. Solve magically and they will become your best salespeople. (2) features that expand your problem space.

#90 — All the best indie developers i know build in public. I have a few theories why. Likely social pressure to improve and perhaps they wouldn't organize their thoughts without it? Give it a shot.

#91 — Make best friends with another indie. Get an office together. Share your ideas with one another. Be generous with tips like these and people will share their tips with you — easiest way to 2x your learnings.

#92 — I speak with indie customers everyday @Superwall and am so surprised to learn (1) how few have other indie friends and (2) how many want more indie friends! Its such a shame! Join @SubClubHQ, look at who liked this tweet and make friends!

#93 — Never be afraid to ask direct personal questions. What's your revenue? How do you grow? How do you hire? Most times people will answer. Share your tips along the way. You'll become friends if you're both passionate.

#94 — Go to San Jose every WWDC, even without an invite. Afterparties are where it's at. Don't worry, everyone is as nerdy as you are, I promise. My first dub dub is the first place I ever felt truly at home with peers.

#95 — Hiring. Is. Hard. Accept this and don't give up early. I tried to hire for ~2 yrs without any success. @briansangles and I have formed a few realizations.

#96 — Don’t ask questions that lead to big decisions. “Want to quit your job and join my risky startup?” Nobody says yes to that. That’s a scary question. “Want to help our startup on the weekends?” That’s a small decision and derisks everyone.

#97 — Don't do live coding questions. Ask to see prior projects and offer a take home interview instead. Pay potential hires their going rate when you give them a take home assignment. It forces you to think carefully about who you interview.

#98 — Be up front with equity, salary and benefits. This info should come before the job description, its what's on everyone's mind anyway.