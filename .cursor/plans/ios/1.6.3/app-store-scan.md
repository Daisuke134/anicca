The ultimate guide to App Store rejections
How to avoid App Store rejections and what to do when you get one.

17 min read

The ultimate guide to App Store rejections - blog illustration

Charlie Chapman
Charlie Chapman

PublishedJune 2, 2023
(Last updated)
June 6, 2024
Apple’s App Store enables developers to reach millions of users across the world, but first developers must pass through the often feared App Review process. This process is paramount to maintaining a safe place for users to download apps, but as a developer, its opaque process can make it difficult to navigate.

In this guide, we want to provide you with some tips to avoid rejections entirely or deal with them when they come.

How to avoid rejections in the first placeCopy link to this section
While it’s impossible to completely avoid app store rejections, there are many things you can try to reduce the chances of getting rejected.

Read the App Review Guidelines and Human Interface GuidelinesCopy link to this section
This may sound obvious, but the first place to start is to read Apple’s App Store Review Guidelines. It’s a long read, but all rejections start from here, so it’s useful to be familiar with the rules, so you can avoid obvious violations while building your app before you even submit.

Apple’s Auto-renewable subscription documentation as well as the In-app purchase section of the Human Interface guidelines are also helpful to read before designing a paywall. In particular, the Clearly describing subscriptions section outlines some of the items that must be included in a paywall or App Review may reject the submission.

Test your app thoroughly in TestFlightCopy link to this section
According to Apple, “over 40% of unresolved issues are related to guideline 2.1: App Completeness, which covers crashes, placeholder content, incomplete information, and more”. 

The best way to avoid these issues is to test your app using TestFlight on as many devices as possible. This is the closest way to replicate the environment a reviewer will be using when testing your app. Try to test against as many device types and sizes as you can. This includes smaller devices with the home button such as the iPhone SE, larger devices with no home button and the dynamic island such as the iPhone 14 Pro Max, and multiple sizes of iPad if your app supports the iPad. 

To ensure your subscriptions work correctly, you can find more details in our comprehensive guide to testing subscription apps.

Provide an active demo accountCopy link to this section
If your app requires account creation, you should create a demo account with some reasonable data that your reviewer can log in with. In App Store Connect, you can provide a user name and password by checking the “Sign-in required” checkbox under the “App Review Information” section in your submission.

App Store Connect app review information fields
App Store Connect app review information fields

If your app uses any unusual features like connecting to external devices or 3rd party software, consider recording a video demo and attaching it to the submission via the “Attachment” field. This can help clear up any confusion a reviewer may have that would ultimately lead to a rejection.

Submit early, submit oftenCopy link to this section
This one doesn’t exactly help avoid rejections, but it will help avoid missing a launch target because of a rejection. For new apps or apps with new in-app purchases, we recommend submitting your app at least a week before your target launch date. This will give you time to get through the app review process and try to make any changes required due to a rejection.

Even for normal app updates, we recommend submitting first and then running any manual testing. If you find issues, you can always pull the release and resubmit it, but if you don’t, this will help your app finish app review much sooner.

So you’ve been rejected… Now what?Copy link to this section
There’s no avoiding it forever. If your business lives on the App Store, you’ll eventually get a rejection. When you do, the reviewer should include a description of the issue, the specific guideline that’s been violated, and, if you’re lucky, a screenshot that shows the issue as they see it. 

Step one is to understand the issue App Review is citing. The guidelines are often vague and interpretations between app reviewers are sometimes inconsistent. Read the guideline they’ve specified fully before introducing changes to your app or protesting the rejection. If you still don’t understand, you can ask follow-up questions through App Store Connect, but keep in mind they will not respond immediately, so this will increase the time it takes to resolve the issue.

Next, try to replicate the issue yourself. If they’ve included a screenshot, this can be extremely useful to at least point you to the device type or screen size being used. 

Hopefully, the fix is straightforward and you can quickly resubmit and be on your way! But typically, it’s not that clear. Let’s discuss some common rejection reasons and ways to resolve them.

Guideline 5.1.1(i) — Missing Privacy PolicyCopy link to this section
According to Guideline 5.1.1(i): “All apps must include a link to their privacy policy in the App Store Connect metadata field and within the app in an easily accessible manner.” This means you must provide a functional link to the privacy policy both in your App Store metadata and easily accessible within your app binary itself. 

 App Store Connect privacy policy fields
App Store Connect privacy policy fields

To add the Privacy Policy to your App Store metadata, there is a field in App Store Connect in the App Privacy section where you can provide a Privacy Policy URL.

You must also provide a functional link to the Privacy Policy within your application. Placing it within the settings of your app should be enough. After relaxing their rules a few years ago, you should not be required to have this link on your paywall anymore, but we still see rejections for this from time to time.

Missing Terms of UseCopy link to this section
App Review also requires that you include a functional link to the Terms of Use in your app’s metadata and your app binary. Adding it to your app binary is the same as the Privacy Policy. It needs to be easily accessible, but is no longer required on your paywall.

Example of Terms of Use link in the app description field
Example of Terms of Use link in the app description field

For your app metadata, the Terms of Use are a little more confusing because there is not a field in App Store Connect you can fill out. What you can do instead is include the link in your App Store Description field, like seen in the screenshot above. 

Yes, this link is not tappable by users on their iOS devices using the App Store. Hopefully, App Store Connect will add a Terms of Use field in the future, but for now, this should get you through App Review without a rejection.

Guideline 4.2 — Minimum functionalityCopy link to this section
App Review will reject any application that does not appear to be finished, citing Guideline 4.2 Minimum Functionality. If your app appears empty before users have created any data, consider adding sample data during onboarding to show the app in a more normal state. 

Adding a video of your app in action can help clarify that your app is feature complete when being used in its intended use case. This is often a quick way to get around a rejection without needing to update your app binary.

App Review will also reject an app if it appears to simply be a thin wrapper around a website. This does not mean you cannot use web technology like web views or React Native to build your app. You must, however, provide an “app-like” experience by ensuring the app looks and feels at home on a mobile device.

Guideline 4.1 — CopycatsCopy link to this section
A really common rejection we see is a violation of App Review Guideline 4.1 Copycats. If your app functionality and design are too similar to other apps on the App Store, find a way to differentiate it from the crowd.

If your app is not blatantly copying another app design, you may still get this rejection if App Review decides that there are too many apps in the store providing the same functionality. Try finding a new unique feature of your app that you can highlight to App Review in an appeal. You may also look for a new novel feature and resubmit.

Guideline 2.1 — App CompletenessCopy link to this section
Make sure there is no placeholder content in your application before submitting to App Review. If they see “Lorem ipsum” anywhere in your app, they will most likely reject it immediately, citing Guideline 2.1 App Completeness. If your app shows demo data during onboarding, make sure it’s clearly labeled as a demo and consider making the data more realistic looking.

If App Review finds any links in your application that open Safari to a broken web page, they will reject the submission as well. Part of your manual or automated regression testing for each release should ensure that all external links in your app still point to functional web pages.

Forcing users to reviewCopy link to this section
User ratings in the App Store are incredibly valuable for helping your app stand out from the crowd. Apple is very strict about apps attempting to force users into leaving ratings or reviews. 

In addition to keeping the rating system valid and trusted by users, App Review is trying to prevent scam phishing apps on the store whose sole purpose is to collect as much user information as possible before users realize the app itself is low quality or doesn’t function as promised.

Guideline 3.1.2(a) outlines that apps are not allowed to force users to rate or review the app. Apps are also not allowed to force users to download other apps or take other actions such as posting social media or uploading contacts that are often required by these scam apps.

If App Review believes an app is a scam app, they will completely remove it from the App Store and may even remove the account from the Apple Developer Program!

Guideline 3.1.3 — Using purchase methods outside in-app purchasesCopy link to this section
If you’ve been following the App Store for a while, you’ll know that Guideline 3.1.3(a) is one of the most hotly contested guidelines. This is where Apple outlines which apps are allowed to use purchase methods apart from Apple’s native in-app purchase system, and thereby avoid Apple’s 15-30% fee.

If your app is not in one of the categories outlined below, it must use Apple’s native in-app purchases for all payments collected from users. Apple will immediately reject any apps that violate this guideline.

Even if your app is in one of these permitted categories, it still must not include a link directly to your website where users can make purchases. There are now some exceptions to this rule for “reader” apps (outlined below) but otherwise App Review will reject your app if you include links to outside payment methods.

According to App Review, the only apps allowed to use outside payment methods are:

“Reader” Apps
This is an oddly named category that essentially covers any apps that provide access to previously purchased digital content, or entire content catalogs. This includes newspapers, books, music services, and streaming video services. Reader apps were recently granted the ability to include external links to their website for account registration and payments, but it requires a special entitlement and has some restrictions. 

Apple’s External Link Account Entitlement support documentation has more details.

Multiplatform Services
Apps that work across multiple platforms such as Android, the web, or even video game consoles may allow users to access content they’ve purchased on a different platform inside your iOS, iPadOS, or Mac app. You may not, however, reference or link to these other purchasing methods inside your app.

Enterprise Services
Apps sold in bulk to enterprise or education customers may allow users to access content or services inside the app. However, this does not apply to family bulk purchases. Family purchases must use Apple’s native in-app purchase system.

Person-to-Person Services
Apps that enable real-time one-on-one services such as personal fitness trainers, private tutors, or medical consultants may use 3rd party payment processors in their app instead of Apple’s native in-app purchase system.

Goods and Services Outside the App
Apps that provide a storefront for purchased real-world goods and services outside the app are not only permitted, but required, to use a 3rd party payment processor. Apple Pay is an alternative that can be used here to maintain a native-feeling payment flow for users.

Free Stand-alone Apps
If an app is entirely free and acts as a companion to a separate paid tool on the web, such as video conferencing apps, email services, or cloud storage providers do not require the user of Apple’s in-app purchase system. These apps may not use other forms of collecting payments in the app or provide any calls to action for users to purchase outside the app.

Advertising Management Apps
Apps do not need to use Apple’s in-app purchases if the sole purpose of the app is for purchasing and managing advertising campaigns across other media types.

Importantly, this does not include purchases of advertisements intended to be used within that app, such as paid “boosts” for social media posts. These types of purchases must still use Apple’s in-app purchase system.

Monetizing built-in OS capabilitiesCopy link to this section
When designing your paywall tiers, it’s important to note that Apple does not allow you to charge a customer for built-in operating system capabilities such as push notifications or iCloud storage.

Apps often run into this rejection when they’ve added a subscription tier specifically for push notifications because the server infrastructure required to support push notifications represents an ongoing cost for each user. If you are rejected for this, consider finding other value-adding features to include with the subscription tier that are not build-in OS capabilities. This is usually enough to be accepted by App Review.

Guideline 1.3 — Kids appsCopy link to this section
If your app is in the Kids Category on the App Store, there are additional rules that you must follow. You may not include links outside the app, and purchasing opportunities must be behind a parental gate.

Your app must also comply with all privacy laws around the world relating to collecting data from children online. We recommend reading through all of Guideline 1.3 Kids Category in the App Review Guidelines for more details.

Guideline 5.1.3 — Storing personal health information in iCloudCopy link to this section
Apple treats user health information very carefully, so if you have a health app, you must be careful to adhere to all guidelines.

If your app collects personal health information, you must not store that information in iCloud according to Guideline 5.1.3 Health and Health Research(ii). If you are using HealthKit for storing health information, you may not write any false or inaccurate data there.

Apps are also not allowed to use any health information from HealthKit for the purposes of targeted advertising, marketing, or data mining.

Missing account deletion functionalityCopy link to this section
In 2022, App Review began requiring all apps that support account creation to also allow users to delete their account within the app. Apple has detailed documentation about this requirement that is worth reading. 

Using a private APICopy link to this section
Private APIs are undocumented functions of Apple’s frameworks. App Review runs automated tests against app submissions that may flag the use of private APIs and trigger a rejection.

Using a private API is a dangerous practice because their functionality is not guaranteed and can be removed or changed by Apple at any time. We recommend using officially documented APIs instead.

Guideline 1.2 — User-generated contentCopy link to this section
Apps that contain user-generated content, such as apps with social features, have unique requirements in App Review under Guideline 1.2 User-Generated Content. The 4 requirements outlined by App Review state your app must include:

A method for filtering objectionable material from being posted to the app
A mechanism to report offensive content and timely responses to concerns
The ability to block abusive users from the service
Published contact information so users can easily reach you
We’ve also heard reports from developers that App Review has told them their age rating in the store must be set to 17+. This isn’t specifically outlined in App Review however. While many social networking apps such as Twitter and Reddit are marked as 17+, others such as Instagram and TikTok are marked as 12+, so there may be a way to avoid this requirement.

Guideline 3.1.2 — Subscription paywall designCopy link to this section
If your app has a subscription, you may run into a 3.1.2 – Business – Payments – Subscriptions rejection. App review seems to treat this section as a catch-all for paywall design violations. This is where App Review can be somewhat subject and, quite frankly, frustrating at times. These violations aren’t always outlined in the App Store Review Guidelines, and you may find examples of other apps in the store with the same violation as yours. 

If making the requested changes would be a major burden, you may appeal the rejection through App Store Connect, however it’s often faster to just make the changes and move on.

One common rejection we see is issues with the paywall display of subscription price and length information. App Review can be very strict about ensuring that these are both prominent and legible in a paywall design. If you get a rejection stating that the price and length are not prominent enough, try increasing the contrast or the font size and resubmit. Many times, this is the only change needed and won’t disrupt the existing design.

Issues fetching subscription productsCopy link to this section
If your in-app purchases are working fine in the Sandbox and TestFlight environment, but App Store Review is failing to retrieve your products for your paywall, your in-app purchases may not have been approved yet. You will need to ensure your new in-app purchases are included in the app submission in App Store Connect. 

App Store Connect in-app purchase submission section (bottom)
App Store Connect in-app purchase submission section (bottom)

If you have submitted your in-app purchases with your app submission and App Store Review is still unable to fetch products, there is likely an issue with the reviewer’s environment. You may simply have to resubmit the same build to review. If you are using RevenueCat to manage your in-app purchases, you can find more information on resolving issues fetching products in our Developer Docs.

Error during in-app purchasesCopy link to this section
If App Review is receiving an error during a purchase, it could be an issue with Apple’s sandbox environment. In this case, your app will receive a STORE_PROBLEM – “There was a problem with the App Store” error. You can check our status page at status.revenuecat.com to see if there have been any major outages recently, but there are sometimes momentary outages in sandbox as well. We recommend either re-submitting your app or trying to explain the situation to the review to trigger a new review.

If you are using RevenueCat to manage your in-app purchases and you encounter any other errors during the purchase process, see our guide on Error Handling for more information.

Final thoughtsCopy link to this section
This hardly covers every rejection you might get from App Review, but we hope this is useful for helping you get your app or update through review and into customers’ hands. Is there something we’ve missed? Please don’t hesitate to Tweet us or contact us via the website.

If you’re struggling with implementing in-app subscriptions, check out our open source SDKs. They handle the pain points of in-app subscriptions, so you can get back to building your app.