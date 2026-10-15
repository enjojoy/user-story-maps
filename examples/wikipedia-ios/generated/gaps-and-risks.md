# Wikipedia (iOS) - gaps and risks

_Generated from `stories.yaml` (`gaps:`). Ordered by severity._

> Unofficial illustration of the open-source Wikipedia iOS app (MIT); not affiliated with or endorsed by the Wikimedia Foundation. Screenshots captured 2026-10-15 in the iOS simulator (app theme dark) from commit ca8aaeb95639ca82105bcd5510277d8dde0e420e; trademarks and content belong to their owners (Wikipedia content CC BY-SA).

## Medium severity

### G-01 - Logged-out Activity tab is only a login prompt

Without an account the Activity tab offers no content, so a fifth of the tab bar is empty for readers who never sign in.

Where: `Activity tab`

Related stories: US-09

### G-02 - For You feed and lead image viewer need live network

In the offline UI-test run the For You tab showed an empty feed with "The app received an unexpected response from the server", and the image viewer opened empty.

Where: `Explore feed, article lead image`

Related stories: US-11, US-18

## Low severity

### G-03 - Places map is empty without location permission

The Places tab showed a map with "No results found" until location access is granted.

Where: `Places tab`

Related stories: US-23

### G-04 - Saved-with-article state not captured

Only the empty Saved list was verified; the capture step that saves an article timed out, so the filled state has no screenshot.

Where: `Saved tab`

Related stories: US-20

### G-05 - Screenshots use fixture content

Feed and article content comes from the app's bundled UI-test fixtures, not live Wikipedia data, so it may differ from what users see today.

Where: `Explore feed, article`

Related stories: US-10, US-12
