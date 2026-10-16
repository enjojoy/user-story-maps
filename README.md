# User Story creator skill for your mobile (and not only) apps

## What it does

A skill for coding agents: it turns an app's screens and user stories into one story map, with real screenshots grouped by topic, plus a report and a one-page overview. It uses free tools only, and nothing leaves your machine.

## Why use it

Most teams can't say quickly which screens their app has, which stories are really built, and where the gaps are. This skill makes your coding agent keep that picture up to date, so you can open one page and see it.

## Examples

![Architecture by topic of the Wikipedia iOS example](examples/wikipedia-ios/generated/architecture.png)

*[Wikipedia iOS](https://github.com/wikimedia/wikipedia-ios): unofficial illustration, not affiliated with the Wikimedia Foundation, MIT ([notices](THIRD-PARTY-NOTICES.md)).*

![Architecture by topic of the Open-Golf iOS example](examples/open-golf/generated/architecture-preview.png)

*[Open-Golf](https://github.com/mgerdes/Open-Golf): unofficial illustration, not affiliated with its author, MIT, art credits in [notices](THIRD-PARTY-NOTICES.md).*

| Example | Contents |
|---|---|
| [`examples/wikipedia-ios/`](examples/wikipedia-ios/) | Wikipedia iOS app, dark theme |
| [`examples/open-golf/`](examples/open-golf/) | Open-Golf game, light theme |

## How to use it

Get a copy of this repo (`git clone https://github.com/enjojoy/user-story-maps`) and point your coding agent at it. Then ask in plain words, for example:

> Make a story map for my app.

The agent reads the skill, looks through your code, takes screenshots, and writes the map into `docs/story-map/`. It also adds a short note to your `AGENTS.md` (or `CLAUDE.md`) so that later changes keep the map current. The agent's instructions are in [`skills/user-story-maps/SKILL.md`](skills/user-story-maps/SKILL.md); you don't need to read them.

You need Python 3.8 or newer. Pillow is optional but recommended, because the images need it.

## Privacy

Screenshots and stories end up in your repo, so use a demo account and fake data. If the app isn't yours, the map says so and you should check the screenshot licence first.

## License

MIT, see [LICENSE](LICENSE). Example screenshots show third-party content under its own terms.
