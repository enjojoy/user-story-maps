# Wikipedia (iOS) - story map report

_Generated from `stories.yaml` by storymap.py - edit the source, not this file._

ios · main @ ca8aaeb · checked 2026-10-15

The open-source Wikipedia iOS app - read, search and save articles from the free encyclopedia.

> Unofficial illustration of the open-source Wikipedia iOS app (MIT); not affiliated with or endorsed by the Wikimedia Foundation. Screenshots captured 2026-10-15 in the iOS simulator (app theme dark) from commit ca8aaeb95639ca82105bcd5510277d8dde0e420e; trademarks and content belong to their owners (Wikipedia content CC BY-SA).

**27 stories:** 🟢 20 built · 🟠 1 partly · 🟣 6 unverified
Built = checked in code/running app (see Verified); unverified = not checked yet.

[architecture.png](architecture.png) · [one-pager.png](one-pager.png) · [story-map.html](story-map.html)

## Topics

| Topic | Screens | Stories | Status counts | Flows |
|---|---|---|---|---|
| Onboarding | 6 | 6 | 🟢 5 · 🟣 1 | 1 · First launch |
| Login & account access | 2 | 1 | 🟢 1 | 2 · Logged out |
| Main user journey | 9 | 12 | 🟢 9 · 🟣 3 | 3 · Reading |
| Content & library | 5 | 4 | 🟢 3 · 🟣 1 | 4 · Search and library |
| Settings & account | 3 | 4 | 🟢 2 · 🟠 1 · 🟣 1 | 5 · Account and settings |
| Donations | 1 | 0 | - |  |
| Support & legal | 1 | 0 | - |  |

- Onboarding -> Main user journey: Tap Next
- Settings & account -> Login & account access: Tap Log in / Join Wikipedia
- Content & library -> Main user journey: Tap a result
- Main user journey -> Content & library: Tap Save, then open Saved, Tap Tabs, Tap Places tab
- Main user journey -> Login & account access: Tap Activity tab
- Main user journey -> Settings & account: Tap the profile icon
- Settings & account -> Support & legal: Tap Privacy policy
- Settings & account -> Donations: Tap Donate

## Stories

### Onboarding

First launch - what Wikipedia is, privacy, languages, interests, feed choice.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-01 | As a first-time user, I want to be told what Wikipedia is when I first open the app so that I know what I am getting. | [Onboarding - welcome](../screens/ob-intro.png) | 🟢 built | verified: simulator, onboarding UI test, 2026-10-15; where: `WikipediaUITests/AppOnboardingUITests`; note: Welcome page with a Learn more link. |
| US-02 | As a first-time user, I want to read how my data is handled before I go on so that I can decide whether I am comfortable. | [Onboarding - data and privacy](../screens/ob-privacy.png) | 🟢 built | verified: simulator, 2026-10-15; where: `WMFComponents (onboarding views)`; note: Links to the privacy policy and terms of use sit on this page; they were not opened. |
| US-03 | As a multilingual reader, I want to pick the languages I read in so that the feed and search use them. | [Onboarding - languages](../screens/ob-languages.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/AppOnboardingCoordinator.swift`; note: Shows the device language as primary with "Add or edit your languages". |
| US-04 | As a first-time user, I want to choose topics I am interested in so that the feed can be personalised. | [Onboarding - follow your curiosity](../screens/ob-personalize.png), [Onboarding - interests](../screens/ob-interests.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/AppOnboardingCoordinator.swift`; note: The interests page has a search box and article suggestions. |
| US-05 | As a first-time user, I want to choose between community-based and personalised feed content so that I control how the feed is built. | [Onboarding - feed preference](../screens/ob-feed.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/AppOnboardingCoordinator.swift`; note: The page says personalised content needs interests to be added. |
| US-06 | As a first-time user, I want to skip the personalisation steps so that I reach the feed faster. | [Onboarding - follow your curiosity](../screens/ob-personalize.png), [Onboarding - interests](../screens/ob-interests.png), [Onboarding - feed preference](../screens/ob-feed.png) | 🟣 unverified | note: A Skip button is visible on these pages; it was not tapped in this run. |

### Login & account access

Logged-out prompts and the login form. The app is fully usable without an account.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-09 | As a curious reader, I want to know why the Activity tab is empty without an account so that I understand what logging in unlocks. | [Activity (logged out)](../screens/activity.png), [Log in form](../screens/login.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Activity tab`; note: The tab shows a prompt with a Log in / Join Wikipedia button instead of content. |

### Main user journey

Reading - the Explore feed and the article view with its reading tools.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-07 | As a curious reader, I want to use the app without an account so that I can read straight away. | [Explore feed](../screens/home.png), [Article](../screens/article.png), [Search results](../screens/search-results.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/WMFAppViewController.swift`; note: Every captured screen was reached logged out. |
| US-10 | As a curious reader, I want to browse a feed of articles and picks on the Explore tab so that I find something to read without searching. | [Explore feed](../screens/home.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/ExploreViewController.swift`; note: Content in the screenshots is the app's bundled UI-test fixture data. |
| US-11 | As a curious reader, I want to switch the feed to a personalised "For You" view so that suggestions follow my interests. | Explore feed - For You | 🟣 unverified | note: The For You tab opens but showed an empty feed and a server error in the offline run. |
| US-12 | As a curious reader, I want to read an article with its lead image and text so that I get the answer to my question. | [Article](../screens/article.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/ArticleViewController.swift` |
| US-13 | As a curious reader, I want to jump to a section from a table of contents so that I skip to the part I need. | [Article - table of contents](../screens/article-toc.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/ArticleViewController+TableOfContents.swift`; note: The contents panel opened; jumping to a section was not tapped. |
| US-14 | As a curious reader, I want to change text size and reading theme so that the article is comfortable to read. | [Article - reading themes](../screens/article-theme.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/ReadingThemesControlsViewController.swift`; note: The panel shows a brightness slider, text-size slider and theme chips. |
| US-15 | As a curious reader, I want to find a word inside an article so that I can locate a passage quickly. | [Article - find in article](../screens/article-find.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/ArticleViewController+FindInPage.swift`; note: Searching "wolf" highlighted matches in the text. |
| US-16 | As a multilingual reader, I want to open the same article in another language so that I can read it in the language I prefer. | [Article - change language](../screens/article-languages.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/WMFLanguagesViewController.m`; note: The picker lists languages; picking one was not tested. |
| US-17 | As a curious reader, I want to find article tools (share, watch, talk page, history, edit source) in a menu so that I can use them without leaving the article. | [Article - more menu](../screens/article-overflow.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/ArticleViewController+ArticleToolbarHandling.swift`; note: The menu lists the actions; none of them was run. |
| US-18 | As a curious reader, I want to view the lead image full screen so that I can see the picture properly. | Lead image viewer | 🟣 unverified | note: Needs a live-network run; the offline viewer opened empty. |
| US-20 | As a commuter with patchy signal, I want to save an article for later so that I can read it without a connection. | [Article](../screens/article.png), [Saved (empty)](../screens/saved.png) | 🟣 unverified | note: The Saved tab was captured empty only; saving an article and offline reading were not captured. |
| US-25 | As a curious reader, I want to use the app in a dark theme so that reading is easy on the eyes at night. | [Explore feed](../screens/home.png), [Article](../screens/article.png), [Settings](../screens/settings.png) | 🟢 built | verified: simulator (UI-test configuration English (Dark)), 2026-10-15; where: `UI-test launch option -WMFAppThemeName dark`; note: Every screenshot in this map was captured with the dark theme. |

### Content & library

Finding and keeping content - search, saved pages, tabs, places.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-19 | As a curious reader, I want to search Wikipedia and get matching articles so that I can look something up. | [Search tab](../screens/search.png), [Search results](../screens/search-results.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/SearchViewController.swift`; note: A search for "Dog" returned the article, and the previous search showed under History. |
| US-21 | As a commuter with patchy signal, I want to see an explanation when nothing is saved yet so that I know how the list fills up. | [Saved (empty)](../screens/saved.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/SavedViewController.swift`; note: Empty state reads "No saved pages yet". |
| US-22 | As a curious reader, I want to keep several articles open in tabs so that I can switch between them. | [Article tabs overview](../screens/tabs-overview.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/TabsOverviewCoordinator.swift`; note: The overview shows one tab card; switching and closing were not tested. |
| US-23 | As a curious reader, I want to find articles near a place on a map so that I can explore my surroundings. | Places map | 🟣 unverified | note: The Places tab opens a map; its screenshot is withheld and nearby results need location access that was not granted. |

### Settings & account

Profile menu, settings and languages.

| ID | Story | Screens | Status | Evidence |
|---|---|---|---|---|
| US-08 | As a curious reader, I want to log in or join Wikipedia when I choose to so that I can use account features. | [Account menu](../screens/profile.png), [Log in form](../screens/login.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/WMFLoginViewController.swift`; note: The form was opened but nothing was typed or submitted. |
| US-24 | As a multilingual reader, I want to manage the languages used by the app so that the feed and search match how I read. | [Settings](../screens/settings.png), [Settings - Wikipedia languages](../screens/settings-languages.png) | 🟢 built | verified: simulator, 2026-10-15; where: `Wikipedia/Code/WMFSettingsViewController.m` |
| US-26 | As a curious reader, I want to find the donate option in the account menu so that I can support Wikipedia. | [Account menu](../screens/profile.png), Donation page | 🟠 partly | note: The Donate row opens an in-app web view of the donation form; that page is outside the app UI and was not exercised beyond opening it. |
| US-27 | As a curious reader, I want to read the privacy policy and terms of use so that I know the rules. | [Settings](../screens/settings.png), Privacy policy | 🟣 unverified | note: Settings lists Privacy policy and Terms of use rows; the pages were not opened. |

## Gaps and risks

### Medium

- **G-01 - Logged-out Activity tab is only a login prompt** - Without an account the Activity tab offers no content, so a fifth of the tab bar is empty for readers who never sign in. Where: `Activity tab`. Stories: US-09.
- **G-02 - For You feed and lead image viewer need live network** - In the offline UI-test run the For You tab showed an empty feed with "The app received an unexpected response from the server", and the image viewer opened empty. Where: `Explore feed, article lead image`. Stories: US-11, US-18.

### Low

- **G-03 - Places map is empty without location permission** - The Places tab showed a map with "No results found" until location access is granted. Where: `Places tab`. Stories: US-23.
- **G-04 - Saved-with-article state not captured** - Only the empty Saved list was verified; the capture step that saves an article timed out, so the filled state has no screenshot. Where: `Saved tab`. Stories: US-20.
- **G-05 - Screenshots use fixture content** - Feed and article content comes from the app's bundled UI-test fixtures, not live Wikipedia data, so it may differ from what users see today. Where: `Explore feed, article`. Stories: US-10, US-12.
