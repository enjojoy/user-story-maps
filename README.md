# User Story creator skill for your mobile (and not only) apps

[![Architecture by topic of the Open-Golf iOS example (click for full size)](examples/open-golf/generated/architecture-preview.png)](https://github.com/enjojoy/user-story-maps/raw/main/examples/open-golf/generated/architecture.png)

*[Open-Golf](https://github.com/mgerdes/Open-Golf): unofficial illustration, not affiliated with its author, MIT, art credits in [notices](THIRD-PARTY-NOTICES.md). Click the image for full size.*

A skill for coding agents. It turns your app's screens and user stories into one clickable map with real screenshots, a report and a one-page overview. For iOS, Android and web apps.

A user story map lists what users want to do and shows the screens that support it.

## What it does

Your coding agent reads the app's code, takes screenshots and sorts the screens by topic. It marks each story as built, partly built, missing or unverified, and lists the gaps it found. It uses free tools only.

## Why use it

Most teams can't say quickly which screens their app has, which stories are really built, and where the gaps are. The agent keeps that picture current as the app changes, so you open one page and see it.

## Examples

<!-- pages-links:start (remove these lines if the hosted pages are not enabled) -->
- Open-Golf, light theme: [open the clickable map](https://enjojoy.github.io/user-story-maps/examples/open-golf/generated/story-map.html)
- Wikipedia iOS, dark theme: [open the clickable map](https://enjojoy.github.io/user-story-maps/examples/wikipedia-ios/generated/story-map.html)
<!-- pages-links:end -->

The clickable maps work on phones too.

Files for each example: [`examples/open-golf/`](examples/open-golf/) and [`examples/wikipedia-ios/`](examples/wikipedia-ios/).

[![Architecture by topic of the Wikipedia iOS example (click for full size)](examples/wikipedia-ios/generated/architecture.png)](https://github.com/enjojoy/user-story-maps/raw/main/examples/wikipedia-ios/generated/architecture.png)

*[Wikipedia iOS](https://github.com/wikimedia/wikipedia-ios): unofficial illustration, not affiliated with the Wikimedia Foundation, MIT ([notices](THIRD-PARTY-NOTICES.md)). Click the image for full size.*

## How to use it

Get a copy of this repo (`git clone https://github.com/enjojoy/user-story-maps`) and point your coding agent at it. Then ask in plain words, for example:

> Make a story map for my app.

The agent reads the skill, looks through your code, takes screenshots, and writes the map into `docs/story-map/`. It also adds a short note to your `AGENTS.md` (or `CLAUDE.md`) so that later changes keep the map current. The agent's instructions are in [`skills/user-story-maps/SKILL.md`](skills/user-story-maps/SKILL.md); you don't need to read them.

You need Python 3.8 or newer. Pillow is optional but recommended, because the images need it.

## Privacy

Your screenshots and stories are not uploaded. The only network request is an optional font download from Google Fonts, which is off by default.

Screenshots and stories end up in your repo, so use a demo account and fake data. If the app isn't yours, the map says so and you should check the screenshot licence first.

## License

MIT, see [LICENSE](LICENSE). Example screenshots show third-party content under its own terms.
