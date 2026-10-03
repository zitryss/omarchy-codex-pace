# Codex Pace

**Make your Codex subscription last through the week.**

Codex Pace is an Omarchy bar plugin that helps you keep a steady, even pace of AI usage. See how much of your weekly quota you can spend today without eating into the days ahead.

It divides your quota week into seven equal, 24-hour planning buckets, each with one-seventh of the quota (displayed as 14%). Spend less and the surplus is available the next day. Spend more and the next day's quota shrinks. Any unused quota expires at the weekly reset.

![Codex Pace compact quota panel](https://raw.githubusercontent.com/zitryss/omarchy-codex-pace/4b336b3c53194eeb86a35d7b247b7d6be180e681/docs/screenshots/codex-pace-compact.png)

## Reading the display

Four compact bars show your quota and time to reset:

- **Today's quota left** compares your available quota with the daily plan. It can exceed 100% when surplus remains; only the bar is capped.
- **Bucket resets in** counts down from 24 hours to the end of the current planning bucket.
- **Weekly quota left** shows the remaining weekly percentage reported by Codex.
- **Weekly resets in** shows the actual days, hours and minutes until the provider resets your week.

Quota bars drain from green toward red. Countdown bars drain from gray toward green as reset approaches. Buckets follow the provider's reset time, not local midnight.

**Resets available** shows your reported reset-credit count. Readings refresh every five minutes; use the circular-arrow button to refresh now. The footer shows how long ago the quota was updated. Countdown and reading-age updates happen locally.

## Get started

You'll need Omarchy with native plugin support and a Codex CLI signed in with your subscription. Follow the [installation instructions](agents.md#install).

Codex Pace helps you plan; it does not enforce spending limits. Daily usage can be estimated, so use the weekly balance as your reference.
