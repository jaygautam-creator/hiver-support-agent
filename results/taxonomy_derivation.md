# Intent taxonomy derivation

TF-IDF (1-2 grams) over 4,000 randomly sampled conversation openers, KMeans k=14, seed=20260909.

Clusters are a **reading aid**, not the taxonomy. They group by surface vocabulary (device names, iOS versions) which cuts across real intents. The taxonomy in `src/taxonomy.py` was written by hand after reading this output, and deliberately does not have k classes.

## Cluster 0  (222 msgs, 5.5%)

**Top terms:** update, new, new update, ios update, ios, new ios, phone, battery, iphone, update phone

- your new update is god awful and fucked up my phone 😤😤😤
- i have a 5s and have latest ios update. Every night i turn off the wifi option, and morning to see the time i press my home button.
- The latest IOS update has left my phone confused, slow and flat. Is there a way to return it to normal @user?
- yo this new update is actually crap brother. Make it stop glitching!!!!!!!!bnnnmkakjsjdnxjdjcjsjkskcksjdjckdkjdndkckjsnkcskxid
- The new Mac update just messed up my computer thanks @user 🙃
- New update causing... over heat problems during charging....
- Ok @user I download the new update, now my battery dies at 20% 🤔
- My phone has died at 50% twice today. When I plugged it in it was magically down to 9%. I really hate the new update, @user. 😡

## Cluster 1  (130 msgs, 3.2%)

**Top terms:** like, phone, url, like url, iphone, update, like user, new, shit, type

- For real @user @user y’all gotta fix this ASAP. I️ look like a fool in emails already but this is another level <url>
- Hi, I keep hearing a random beep like a Fire Alarm noise from my phone. What could this mean?????
- tell me why when I️ type “i” it sends this instead and my phone is updated so like what’s the problem here <url>
- just got my iPhone X today. When I have night shift on and my brightness all the way down, when I swipe down to get to ‘search’ there is a pattern of discoloration under my screen that almost looks like there is some sor
- Why can’t we sort Messages and Photos latest at top to oldest at bottom like Twitter? @user #ux
- Like wtf is this ? @user what’s good. O and this update is trash! <url>
- My iphone 7s keeps on heating up like crazy. provide a solution.
- Don’t like how the battery drains on my #iPhone7Plus after the #ios11update Do something about it @user

## Cluster 2  (927 msgs, 23.2%)

**Top terms:** help, update, user user, app, just, time, sierra, hey, macbook, working

- Wasted 4 hours of my life @user for you all to tell me I have to come back another day to get my screen fixed since the mall was closing 😡
- this feeling of regret for buying the X instead of 8+ is kicking in now lmao fuck u for changing so many functions @user
- still ain’t fixed this whole i situation
- can you please stop turning my Bluetooth on
- Hey @user @user what is going on with the A? instead of capital i in the autocorrect?? It’s very annoying
- Hey @user Mail app on iOS is crashing constantly when searching emails. I can reproduce the bug easily. Almost every time I search my mailboxes it crashes.
- My ⏯ prev, next, music controls are not working since upgrading my MacBook Pro to Mac OS X 13. Any ideas why? @user
- Can I use my wired printer having USB on my MacBook pro which has has c type?..Pls suggest if USB hub and c-type to USB female will work for it?

## Cluster 3  (244 msgs, 6.1%)

**Top terms:** apple, music, apple music, id, apple id, apple watch, watch, store, apple store, url

- another Apple scam... <url>
- my iPhone 7 black color paint is started to chip off. Not expected this from apple. Please help
- Why does my Apple Music stop everytime I get snap chat @user
- Good evening. Does Apple EarPods have a warranty? If I have to get my EarPods replaced or checked out, is there a fee?
- ...........can’t go to Apple Store becuz they don’t c the problem so it doesn’t exist. Thank you Apple for paying a salary for a rep who was clearly wrong. Now I can’t hold my phone while it’s charging becuz it’s extreme
- Non ricordo la password ID Apple.Ho chiesto ripristino giovedì. mi dite che risponderete il 27/10.Cosa posso fare x averla subito?Grz
- how and where can i change my apple watch's name that appears on my iphone?
- Mac OS High Sierra is utterly slow in my mid 2014 iMac. I contacted the customer support @user but they gave flop solutions, made it more worst, two minutes fifty five seconds for system booting. Disappointed apple custo

## Cluster 4  (302 msgs, 7.5%)

**Top terms:** url, help url, help, hey, fix, hey user, fix url, going, happens, time

- in Mail but can’t see anything about signature in Preferences <url>
- .@user how do I️ stop this absurd autocorrect? <url>
- why does this happen whenever I start a sentence with a capital letter? Mainly “I️”&”A” <url>
- hi, just installed 11.0.2 iOS on iPhone SE. Can’t seem to accept iCloud terms and conditions, page gets stuck, pls help! <url>
- restore from iCloud backup and poof! All my achievements gone. Sigh. <url>
- hi please help me with this? <url>
- .@user are these intentionally there? <url>
- .@user every incoming notification on my Nike 3 watch has no image. Doesn't matter the app. Thoughts? <url>

## Cluster 5  (152 msgs, 3.8%)

**Top terms:** ios11, battery, phone, url, user ios11, user user, iphone, ios11 url, ios11 update, update

- Since I’ve updated my @user 6SPlus to the new IOS11.1 yesterday, its been super slow,unresponsive,freezes all time and no sound at speaker!
- deben solucionar el problema de consumo excesivo de batería con las actualizacion de iOS11 en iPhone.
- Okay @user of all the bugs in iOS11, the one where the alarm doesn’t make any noise needs to get fixed yesterday.
- my phone is slow as shut after ios11
- I️ can’t type a capital “I️” without it turning into some weird emoji (see last tweet). Anyone else having this issue? #iOS11 @user
- Do I need this patch if I don't take my #ipad out of my #house? @user @user #apple #ios #patches #ios11 #ios11.1.2 <url>
- Could you please point me to the exact place where I can find the "Reply with Message" toggle in iOS11? <url>
- #iOS11 and @user; what’s up with my music? Having a seizure. <url>

## Cluster 6  (300 msgs, 7.5%)

**Top terms:** fix, user fix, glitch, problem, fix problem, fix glitch, letter, gonna, going fix, issue

- Yo ya doing bad fix that glitch already @user
- So when is @user gonna fix that “I” glitch? Cause...
- I’m not the only one having this problem! Just called Apple and it’s a glitch in their update or something. Ugh please fix this soon so I️ can type “I️”.🙏🏼 @user <url>
- .@user when is the update coming to fix the issue about the ? Sign replacing the I️???? ANNOYING!!!!!!!
- Ugh if @user doesn’t fix this typing problem
- please please please fix your glitch please it’s this A ? mark nonsense
- please fix your basic app performance. the visual voicemail hangs on every letter i type... UGH!!!
- For real though when is @user going to fix this weird I️ problem. I’m tired of speaking alien 👽

## Cluster 7  (413 msgs, 10.3%)

**Top terms:** ios 11, 11, ios, iphone, battery, 11 update, update, phone, fix, url

- My phone keeps on crashing and the performance has been slow after I upgraded to iOS 11. 🙄 @user @user #iphone
- have you had complaints about iOS 11.1 causing iPhone to enter “data recovery mode’ immediately after installing update?
- can I downgrade my phone OS from iOS 11.0 to iOS 10? #BatteryDrain
- This iOS 11 update has messed with touch ID and my screen sensitivity. I don't get it. @user
- how can if fix this? Installing apps function is grayed out. I restarted the phone and I am using iOS 11.1.1. <url>
- iOS 11.1 on my iPads is already a fail @user screen doesn’t rotate from vertical/horizontal. You iOS continues to get shittier
- please fix the battery issue on iPad air 2. It is much worse after the ios 11 update even though much improved after ios 11.1 but not the same as ios 10.3.3
- fix ios 11!! my phone has dropped 10% in one minute this has never happened before

## Cluster 8  (444 msgs, 11.1%)

**Top terms:** phone, update, updated, update phone, just, new, new phone, updated phone, does, keeps

- I thought @user believed in Customer satisfaction most!But I was mistaken ,1 of the service centers just completely denied to repair/replace a 33 day old under warranty phone!Plz resolve the issue asap as I am having dif
- seriously wtf is up with this update, made my phone into a Nokia
- .... my phone is still having spasms 😩
- Going on a week of having this "I" changing to ? thing on my phone. @user we getting that update anytime soon?
- just updated my phone to the new software now I cant even use my phone without the battery dying. Are you just trying to scam people so they have to buy a new phone? Im so angry. I cant even listen to music without it dy
- the newest update makes my phone’s brightness change on its own. How do I make it stop? It’s so irritating!
- 11.0.3 photos do not open when phone connected to PC. Windows PC can't see phone
- Dear Apple My IPhone 6 spacegrey 64Gb is literally down af I can’t fucking use it without getting a dark display for no reason or that it hangs completely also a lot of apps are shutting down immediately after I opened t

## Cluster 9  (421 msgs, 10.5%)

**Top terms:** iphone, iphone 6s, 6s, new iphone, plus, update, new, help, just, screen

- I'm thinking of buying an iPhone and I was wondering if watching shows I've downloaded from iTunes, on the iphone is possible?
- i just got the iphone 8 plus last week & it’s freezing so much... @user wtf.. a $900 phone should not be freezing this much..
- every time eye type the letter “i” a box comes up.. eye have iPhone 8 with the latest update #Buggy
- in my iphone 7plus have voice mail bug always coming notifications of voice mail but there is nothing how i fix this?
- Dear @user After several reminders, I updated my 6S and now it hangs 10 times a day. Gone are the days where things were built to last with pride?? @user @user #Disappointed #MissingSteveJobs #Techfraud #FridayFeeling #i
- Hey guys, I got the iPhone X and the previous iPhones I had the special achievements and badges and now they are missing from the activity app. I got the earth day and thanksgiving, but its all missing
- dear @user i used my apple care for my NEW iphone 8 to receive another broken iphone 8 in the mail. 2 phones in 2 weeks. get it together.
- how to reset RAM on iPhone X? (used to be able to hold power until slide to shut down, and then hold home button)

## Cluster 10  (120 msgs, 3.0%)

**Top terms:** user url, url, user user, fix user, fix, help, help user, happening, apple, wtf

- So this “I️ “ thing....fix it @user @user <url>
- Hi apple @user @user @user @user @user <url>
- Wtf is this stupidity @user ? <url>
- k. now my macbook is doing this shit. wtf @user <url>
- Apple I’ve contacted y’all once and it got better but then this started again, it is making me very angry from the annoyance that it causes. WHAT IS WRONG WITH MY PHONE @user <url>
- I don’t understand this but I’m over it. Fix this now. @user <url>
- Like wtf @user what is this !!! <url>
- TWITTER IS DOING IT TOO WHAT IS WRONG WITH IOS 11 @user @user <url>

## Cluster 11  (132 msgs, 3.3%)

**Top terms:** shit, fix shit, fix, shit user, user shit, phone, user fix, fucking, damn, wtf

- my phones being a piece of shit and freaking out, thanks @user
- It’s really pissing me off that uppercase i turns into I️... @user fix that shit
- Anyone facing the same shit? @user help? <url>
- Okay @user how about you get your shit together a fix this!! I️
- your iPhone 7 a piece of shit. Shit won't let me call or connect to the internet where my money at
- explain why I pay 300$ a month for my phone and this shit doesn’t work!!
- Can you fix all these issues with the letter “eye”. Now this “I.T” is happening when you type the word “it”. Fix your shit @user
- Phone has frozen 7+ times since I updated it get your shit together @user

## Cluster 12  (107 msgs, 2.7%)

**Top terms:** question, mark, question mark, question marks, marks, box, mark box, boxes, letter, fix

- wtf going on bro I’m still seeing boxes with question marks and I️ updated my phone 🙄🤦🏾‍♀️
- needs to fix the letter “I️” from changing to a question mark 🙄
- I️ hate when you type the letter I it wants to be a freaking question mark why is that @user @user @user
- why does it auto correct to a box and question mark can you tell me a fix <url>
- Can SOMEONE PLZ fix this!?! Every time I️ type i it alters to stupid question mark box. @user. Crazy ridiculous ha. Atleast alter to 🍆 or.. <url>
- seriously @user wtf is up with the question mark boxes when i’m trying to type i️
- can we talk about how i️ updated my phone twice and i’m still seeing boxes and question marks???? @user
- Wassup with those question mark boxes? @user

## Cluster 13  (86 msgs, 2.1%)

**Top terms:** battery life, life, battery, ios, 11, update, ios 11, iphone, terrible, phone

- Pleease fix battery drainage! I don’t want it to shorten my battery life :( any way to go back to ios10 until ios11 fixed?
- Hey @user, @user are destroying battery life with unwanted background activity again. <url>
- Why is my battery life going backwards when its on the charger? @user tf is that about?!
- I am leaning toward moving to a different phone. Since 11 my phone causes me more problems than good, its way too slow, programs die, battery life is totally unacceptable and forget iPhone X, why would I want more of thi
- 11.0.3 battery life is terrible. my phone is glitching trying to go in and out of Apps, and is super slow. Absolutely awful!
- 11.0.3 battery After upgrading to 11.0.3, battery life decrease. touch id stop working properly. touch screen acts up
- new iOS wrecked my iPhone 6 and iPad. Horrible battery life and slow/glitchy performance. Might make the jump to @user phone
- the latest update stinks, it kills battery life. I don’t use it at work yet it drains 20-30% of my battery during that period.
