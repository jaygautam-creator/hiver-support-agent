# Brand deflection analysis

Measured over every brand reply that responds to another tweet.

- **deflection_%** - reply pushes the customer to DM/private channel
- **substantive_%** - reply contains an actionable instruction and is *not* a DM handoff
- **self_serve_url_%** - reply links to a help resource

A brand with a high deflection rate cannot support a grounded-reply agent:
there is no historical resolution to ground in, only a handoff.

| brand           |   n_replies |   deflection_% |   self_serve_url_% |   substantive_% |   median_len |
|:----------------|------------:|---------------:|-------------------:|----------------:|-------------:|
| hulu_support    |       21783 |            0.5 |               54.8 |            24.4 |          132 |
| AppleSupport    |      106719 |           52.5 |               75.4 |            18.1 |          129 |
| XboxSupport     |       24341 |           21   |               40.1 |            17.8 |          115 |
| SpotifyCares    |       43243 |           30.8 |               50.5 |            12.7 |          131 |
| AmazonHelp      |      169287 |            0.7 |               41.3 |             9.5 |          123 |
| British_Airways |       29315 |           14   |                6.7 |             7.6 |          124 |
| AmericanAir     |       36598 |           16.8 |                6.4 |             7.4 |          107 |
| SouthwestAir    |       28889 |           17   |               16   |             6.6 |          118 |
| Delta           |       42197 |           16.5 |               15.2 |             4.4 |          102 |
| Tesco           |       38501 |           26.9 |                8.1 |             4.4 |          134 |
| Uber_Support    |       56261 |           35.9 |               51.3 |             3.9 |          104 |
| TMobileHelp     |       34287 |           81.9 |               48.2 |             2   |          126 |
