# Capture details

Long-form detail for `SKILL.md` → Capture. Everything here is optional reading.

## iOS Simulator without deep links
- `simctl` cannot tap. Tap by hand, or drive the app with an XCUITest that attaches `XCUIScreen` / `app.screenshot()` images.
- Export attachments: `xcrun xcresulttool export attachments --path X.xcresult --output-path out`.
- Worked example: `examples/wikipedia-ios/capture/StoryMapShotsUITests.swift`. Open-source apps often ship UI tests with fixtures worth reusing.
- Build open-source apps from a scratch clone: `xcodebuild -scheme <App> -destination id=<simulator> -derivedDataPath <dir> CODE_SIGN_IDENTITY=- build`.
  - Ad-hoc signing keeps app-group entitlements working. `CODE_SIGNING_ALLOWED=NO` can crash at launch.
- Seed demo data first: sign in with the demo account, create sample items.
- System sheets (Apple sign-in, permission alerts): capture while visible.
- Notifications: a device, or `xcrun simctl push booted <bundle-id> payload.json`.

## Documenting a third-party app
- Fill `app.disclaimer` (e.g. "Unofficial illustration; not affiliated with …").
- Publish only public content.
- Withhold screens that reveal device-specific data (map region, locale/country, notifications).

## Web without Playwright
`google-chrome --headless --screenshot=out.png --window-size=1280,800 URL` works for public pages.

## Demo-account checklist before committing screenshots
- Check every screenshot for: real names, emails, phone numbers, addresses, order numbers, location, notifications from other apps, dev URLs/IDs in debug banners.
- Keep session files (`.demo-session.json`) in `.gitignore` (`templates/gitignore-snippet.txt`).
- Never paste secrets into commands or shot lists.

## Raw commands (what the helpers wrap)
```bash
xcrun simctl list devices available
xcrun simctl boot "iPhone 16" && open -a Simulator
xcrun simctl status_bar booted override --time 9:41 --batteryState charged --batteryLevel 100 --wifiBars 3 --cellularBars 4
xcrun simctl openurl booted myapp://settings
xcrun simctl ui booted appearance dark
xcrun simctl io booted screenshot --type=png docs/story-map/screens/settings.png
adb devices
adb shell am start -a android.intent.action.VIEW -d "myapp://settings"
adb exec-out screencap -p > docs/story-map/screens/settings.png
```
Web: `playwright codegen --save-storage=.demo-session.json` creates the demo session once.
