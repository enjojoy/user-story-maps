# Wikipedia (iOS) - story map

_Generated from `stories.yaml`. The diagrams below render on GitHub. Screens with real screenshots are in `flows/` (PNG) and `story-map.html`._

**ios · main @ ca8aaeb · checked 2026-10-15**

> Unofficial illustration of the open-source Wikipedia iOS app (MIT); not affiliated with or endorsed by the Wikimedia Foundation. Screenshots captured 2026-10-15 in the iOS simulator (app theme dark) from commit ca8aaeb95639ca82105bcd5510277d8dde0e420e; trademarks and content belong to their owners (Wikipedia content CC BY-SA).

Status: 🟢 built · 🟠 partly · 🟣 unverified · ⚪ missing

## Architecture by topic

Each box is a topic area; arrows show how users move between them.

| Topic | Screens | Stories | 🟢 built | 🟠 partly | 🟣 unverified | ⚪ missing | Flows |
|---|---|---|---|---|---|---|---|
| **Onboarding** | 6 | 6 | 5 | 0 | 1 | 0 | 1 · First launch |
| **Login & account access** | 2 | 1 | 1 | 0 | 0 | 0 | 2 · Logged out |
| **Main user journey** | 9 | 12 | 9 | 0 | 3 | 0 | 3 · Reading |
| **Content & library** | 5 | 4 | 3 | 0 | 1 | 0 | 4 · Search and library |
| **Settings & account** | 3 | 4 | 2 | 1 | 1 | 0 | 5 · Account and settings |
| **Donations** | 1 | 0 | 0 | 0 | 0 | 0 |  |
| **Support & legal** | 1 | 0 | 0 | 0 | 0 | 0 |  |

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#000000","primaryTextColor":"#EAECF0","primaryBorderColor":"#719DF4","lineColor":"#719DF4","secondaryColor":"#101418","tertiaryColor":"#1A1A1A"}}}%%
flowchart LR
  n_t_onboarding["<b>Onboarding</b><br/>6 screens · 6 stories<br/>5 built · 1 unverified"]
  n_t_access["<b>Login & account access</b><br/>2 screens · 1 stories<br/>1 built"]
  n_t_journey["<b>Main user journey</b><br/>9 screens · 12 stories<br/>9 built · 3 unverified"]
  n_t_library["<b>Content & library</b><br/>5 screens · 4 stories<br/>3 built · 1 unverified"]
  n_t_settings["<b>Settings & account</b><br/>3 screens · 4 stories<br/>2 built · 1 partly · 1 unverified"]
  n_t_payments["<b>Donations</b><br/>1 screens · 0 stories<br/>no stories"]
  n_t_support["<b>Support & legal</b><br/>1 screens · 0 stories<br/>no stories"]
  n_t_onboarding ==>|"Tap Next"| n_t_journey
  n_t_settings ==>|"Tap Log in / Join Wikipedia"| n_t_access
  n_t_library ==>|"Tap a result"| n_t_journey
  n_t_journey ==>|"Tap Save, then open Saved +2 more"| n_t_library
  n_t_journey ==>|"Tap Activity tab"| n_t_access
  n_t_journey ==>|"Tap the profile icon"| n_t_settings
  n_t_settings ==>|"Tap Privacy policy"| n_t_support
  n_t_settings ==>|"Tap Donate"| n_t_payments
  style n_t_onboarding fill:#09160F,stroke:#5AE299,stroke-width:3px,color:#EAECF0
  style n_t_access fill:#091615,stroke:#5AE2D6,stroke-width:3px,color:#EAECF0
  style n_t_journey fill:#091116,stroke:#5AB2E2,stroke-width:3px,color:#EAECF0
  style n_t_library fill:#090B16,stroke:#5A75E2,stroke-width:3px,color:#EAECF0
  style n_t_settings fill:#0C0916,stroke:#7B5AE2,stroke-width:3px,color:#EAECF0
  style n_t_payments fill:#120916,stroke:#B75AE2,stroke-width:3px,color:#EAECF0
  style n_t_support fill:#160914,stroke:#E25AD0,stroke-width:3px,color:#EAECF0
```

### Screens grouped by topic

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#000000","primaryTextColor":"#EAECF0","primaryBorderColor":"#719DF4","lineColor":"#719DF4","secondaryColor":"#101418","tertiaryColor":"#1A1A1A"}}}%%
flowchart LR
  subgraph n_sg_onboarding["Onboarding"]
    direction TB
    n_ob_intro["Onboarding - welcome<br/><i>Built</i>"]:::built
    n_ob_privacy["Onboarding - data and privacy<br/><i>Built</i>"]:::built
    n_ob_languages["Onboarding - languages<br/><i>Built</i>"]:::built
    n_ob_personalize["Onboarding - follow your curiosity<br/><i>Unverified</i>"]:::unverified
    n_ob_interests["Onboarding - interests<br/><i>Unverified</i>"]:::unverified
    n_ob_feed["Onboarding - feed preference<br/><i>Unverified</i>"]:::unverified
  end
  subgraph n_sg_access["Login & account access"]
    direction TB
    n_login["Log in form<br/><i>Built</i>"]:::built
    n_activity["Activity (logged out)<br/><i>Built</i>"]:::built
  end
  subgraph n_sg_journey["Main user journey"]
    direction TB
    n_home["Explore feed<br/><i>Built</i>"]:::built
    n_foryou["Explore feed - For You<br/><i>Unverified</i>"]:::unverified
    n_article["Article<br/><i>Unverified</i>"]:::unverified
    n_article_toc["Article - table of contents<br/><i>Built</i>"]:::built
    n_article_theme["Article - reading themes<br/><i>Built</i>"]:::built
    n_article_overflow["Article - more menu<br/><i>Built</i>"]:::built
    n_article_find["Article - find in article<br/><i>Built</i>"]:::built
    n_article_languages["Article - change language<br/><i>Built</i>"]:::built
    n_gallery["Lead image viewer<br/><i>Unverified</i>"]:::unverified
  end
  subgraph n_sg_library["Content & library"]
    direction TB
    n_search["Search tab<br/><i>Built</i>"]:::built
    n_search_results["Search results<br/><i>Built</i>"]:::built
    n_saved["Saved (empty)<br/><i>Unverified</i>"]:::unverified
    n_tabs_overview["Article tabs overview<br/><i>Built</i>"]:::built
    n_places["Places map<br/><i>Unverified</i>"]:::unverified
  end
  subgraph n_sg_settings["Settings & account"]
    direction TB
    n_profile["Account menu<br/><i>Partly built</i>"]:::partly
    n_settings["Settings<br/><i>Unverified</i>"]:::unverified
    n_settings_languages["Settings - Wikipedia languages<br/><i>Built</i>"]:::built
  end
  subgraph n_sg_payments["Donations"]
    direction TB
    n_donate["Donation page<br/><i>Partly built</i>"]:::partly
  end
  subgraph n_sg_support["Support & legal"]
    direction TB
    n_privacy_policy["Privacy policy<br/><i>Unverified</i>"]:::unverified
  end
  n_ob_intro --> n_ob_privacy
  n_ob_privacy --> n_ob_languages
  n_ob_languages --> n_ob_personalize
  n_ob_personalize --> n_ob_interests
  n_ob_interests --> n_ob_feed
  n_ob_feed ==>|"Tap Next"| n_home
  n_profile ==>|"Tap Log in / Join Wikipedia"| n_login
  n_activity --> n_login
  n_home --> n_foryou
  n_home --> n_article
  n_article --> n_article_toc
  n_article --> n_article_theme
  n_article --> n_article_overflow
  n_article --> n_article_find
  n_article --> n_article_languages
  n_article --> n_gallery
  n_search --> n_search_results
  n_search_results ==>|"Tap a result"| n_article
  n_article ==>|"Tap Save, then open Saved"| n_saved
  n_article ==>|"Tap Tabs"| n_tabs_overview
  n_home ==>|"Tap Places tab"| n_places
  n_home ==>|"Tap Activity tab"| n_activity
  n_home ==>|"Tap the profile icon"| n_profile
  n_profile --> n_settings
  n_settings --> n_settings_languages
  n_settings ==>|"Tap Privacy policy"| n_privacy_policy
  n_profile ==>|"Tap Donate"| n_donate
  style n_sg_onboarding fill:#07120C,stroke:#5AE299,stroke-width:2px
  style n_sg_access fill:#071211,stroke:#5AE2D6,stroke-width:2px
  style n_sg_journey fill:#070E12,stroke:#5AB2E2,stroke-width:2px
  style n_sg_library fill:#070912,stroke:#5A75E2,stroke-width:2px
  style n_sg_settings fill:#090712,stroke:#7B5AE2,stroke-width:2px
  style n_sg_payments fill:#0E0712,stroke:#B75AE2,stroke-width:2px
  style n_sg_support fill:#120710,stroke:#E25AD0,stroke-width:2px
  classDef built fill:#1B3731,stroke:#00AF89,stroke-width:3px,color:#EAECF0;
  classDef partly fill:#37301B,stroke:#FFCC33,stroke-width:3px,color:#EAECF0;
  classDef unverified fill:#1B2437,stroke:#6699FF,stroke-width:2px,stroke-dasharray:4 3,color:#EAECF0;
  classDef missing fill:#1B2837,stroke:#A2A9B1,stroke-width:2px,stroke-dasharray:5 4,color:#EAECF0;
  classDef portal fill:#1C0D4A,stroke:#9271F4,color:#EAECF0;
```

## Story map (personas x flows)

| Persona | 1 · First launch | 2 · Logged out | 3 · Reading | 4 · Search and library | 5 · Account and settings |
|---|---|---|---|---|---|
| **First-time user** | 🟢 US-01<br/>🟢 US-02<br/>🟢 US-04<br/>🟢 US-05<br/>🟣 US-06 |  |  |  |  |
| **Curious reader** |  | 🟢 US-09 | 🟢 US-07<br/>🟢 US-10<br/>🟣 US-11<br/>🟢 US-12<br/>🟢 US-13<br/>🟢 US-14<br/>🟢 US-15<br/>🟢 US-17<br/>🟣 US-18<br/>🟢 US-25 | 🟢 US-19<br/>🟢 US-22<br/>🟣 US-23 | 🟢 US-08<br/>🟠 US-26<br/>🟣 US-27 |
| **Multilingual reader** | 🟢 US-03 |  | 🟢 US-16 |  | 🟢 US-24 |
| **Offline commuter** |  |  | 🟣 US-20 | 🟢 US-21 |  |

## Flows overview

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#000000","primaryTextColor":"#EAECF0","primaryBorderColor":"#719DF4","lineColor":"#719DF4","secondaryColor":"#101418","tertiaryColor":"#1A1A1A"}}}%%
flowchart LR
  n_first_run["<b>1 · First launch</b><br/>6 screens · 6 stories<br/>5 built · 1 unverified"]:::flow
  n_logged_out["<b>2 · Logged out</b><br/>2 screens · 1 stories<br/>1 built"]:::flow
  n_reading["<b>3 · Reading</b><br/>9 screens · 12 stories<br/>9 built · 3 unverified"]:::flow
  n_library["<b>4 · Search and library</b><br/>5 screens · 4 stories<br/>3 built · 1 unverified"]:::flow
  n_account["<b>5 · Account and settings</b><br/>5 screens · 4 stories<br/>2 built · 1 partly · 1 unverified"]:::flow
  n_first_run -->|"Tap Next"| n_reading
  n_account -->|"Tap Log in / Join Wikipedia"| n_logged_out
  n_library -->|"Tap a result"| n_reading
  n_reading -->|"Tap Save, then open Saved"| n_library
  n_reading -->|"Tap Activity tab"| n_logged_out
  n_reading -->|"Tap the profile icon"| n_account
  classDef flow fill:#000000,stroke:#719DF4,stroke-width:3px,color:#EAECF0;
```

## 1 · First launch

Six onboarding pages, then the Explore feed.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#000000","primaryTextColor":"#EAECF0","primaryBorderColor":"#719DF4","lineColor":"#719DF4","secondaryColor":"#101418","tertiaryColor":"#1A1A1A"}}}%%
flowchart LR
  n_ob_intro["Onboarding - welcome<br/><i>Built</i>"]:::built
  n_ob_privacy["Onboarding - data and privacy<br/><i>Built</i>"]:::built
  n_ob_languages["Onboarding - languages<br/><i>Built</i>"]:::built
  n_ob_personalize["Onboarding - follow your curiosity<br/><i>Unverified</i>"]:::unverified
  n_ob_interests["Onboarding - interests<br/><i>Unverified</i>"]:::unverified
  n_ob_feed["Onboarding - feed preference<br/><i>Unverified</i>"]:::unverified
  n_out_home(["Go to 3 · Reading: Explore feed"]):::portal
  n_ob_intro -->|"Tap Next"| n_ob_privacy
  n_ob_privacy -->|"Tap Next"| n_ob_languages
  n_ob_languages -->|"Tap Next"| n_ob_personalize
  n_ob_personalize -->|"Tap Next"| n_ob_interests
  n_ob_interests -->|"Tap Next"| n_ob_feed
  n_ob_feed -->|"Tap Next"| n_out_home
  classDef built fill:#1B3731,stroke:#00AF89,stroke-width:3px,color:#EAECF0;
  classDef partly fill:#37301B,stroke:#FFCC33,stroke-width:3px,color:#EAECF0;
  classDef unverified fill:#1B2437,stroke:#6699FF,stroke-width:2px,stroke-dasharray:4 3,color:#EAECF0;
  classDef missing fill:#1B2837,stroke:#A2A9B1,stroke-width:2px,stroke-dasharray:5 4,color:#EAECF0;
  classDef portal fill:#1C0D4A,stroke:#9271F4,color:#EAECF0;
```

## 2 · Logged out

Account prompts that lead to the login form.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#000000","primaryTextColor":"#EAECF0","primaryBorderColor":"#719DF4","lineColor":"#719DF4","secondaryColor":"#101418","tertiaryColor":"#1A1A1A"}}}%%
flowchart LR
  n_activity["Activity (logged out)<br/><i>Built</i>"]:::built
  n_login["Log in form<br/><i>Built</i>"]:::built
  n_in_profile(["From 5 · Account and settings: Account menu"]):::portal
  n_in_home(["From 3 · Reading: Explore feed"]):::portal
  n_in_profile -->|"Tap Log in / Join Wikipedia"| n_login
  n_activity -->|"Tap Log in / Join Wikipedia"| n_login
  n_in_home -->|"Tap Activity tab"| n_activity
  classDef built fill:#1B3731,stroke:#00AF89,stroke-width:3px,color:#EAECF0;
  classDef partly fill:#37301B,stroke:#FFCC33,stroke-width:3px,color:#EAECF0;
  classDef unverified fill:#1B2437,stroke:#6699FF,stroke-width:2px,stroke-dasharray:4 3,color:#EAECF0;
  classDef missing fill:#1B2837,stroke:#A2A9B1,stroke-width:2px,stroke-dasharray:5 4,color:#EAECF0;
  classDef portal fill:#1C0D4A,stroke:#9271F4,color:#EAECF0;
```

## 3 · Reading

From the Explore feed into an article and its reading tools.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#000000","primaryTextColor":"#EAECF0","primaryBorderColor":"#719DF4","lineColor":"#719DF4","secondaryColor":"#101418","tertiaryColor":"#1A1A1A"}}}%%
flowchart LR
  n_home["Explore feed<br/><i>Built</i>"]:::built
  n_foryou["Explore feed - For You<br/><i>Unverified</i>"]:::unverified
  n_article["Article<br/><i>Unverified</i>"]:::unverified
  n_article_toc["Article - table of contents<br/><i>Built</i>"]:::built
  n_article_theme["Article - reading themes<br/><i>Built</i>"]:::built
  n_article_overflow["Article - more menu<br/><i>Built</i>"]:::built
  n_article_find["Article - find in article<br/><i>Built</i>"]:::built
  n_article_languages["Article - change language<br/><i>Built</i>"]:::built
  n_gallery["Lead image viewer<br/><i>Unverified</i>"]:::unverified
  n_in_ob_feed(["From 1 · First launch: Onboarding - feed preference"]):::portal
  n_in_search_results(["From 4 · Search and library: Search results"]):::portal
  n_out_saved(["Go to 4 · Search and library: Saved (empty)"]):::portal
  n_out_tabs_overview(["Go to 4 · Search and library: Article tabs overview"]):::portal
  n_out_places(["Go to 4 · Search and library: Places map"]):::portal
  n_out_activity(["Go to 2 · Logged out: Activity (logged out)"]):::portal
  n_out_profile(["Go to 5 · Account and settings: Account menu"]):::portal
  n_in_ob_feed -->|"Tap Next"| n_home
  n_home -->|"Tap For You"| n_foryou
  n_home -->|"Tap an article"| n_article
  n_article -->|"Tap Contents"| n_article_toc
  n_article -->|"Tap Reading themes"| n_article_theme
  n_article -->|"Tap the more menu"| n_article_overflow
  n_article -->|"Tap Find in article"| n_article_find
  n_article -->|"Tap Languages"| n_article_languages
  n_article -->|"Tap the lead image"| n_gallery
  n_in_search_results -->|"Tap a result"| n_article
  n_article -->|"Tap Save, then open Saved"| n_out_saved
  n_article -->|"Tap Tabs"| n_out_tabs_overview
  n_home -->|"Tap Places tab"| n_out_places
  n_home -->|"Tap Activity tab"| n_out_activity
  n_home -->|"Tap the profile icon"| n_out_profile
  classDef built fill:#1B3731,stroke:#00AF89,stroke-width:3px,color:#EAECF0;
  classDef partly fill:#37301B,stroke:#FFCC33,stroke-width:3px,color:#EAECF0;
  classDef unverified fill:#1B2437,stroke:#6699FF,stroke-width:2px,stroke-dasharray:4 3,color:#EAECF0;
  classDef missing fill:#1B2837,stroke:#A2A9B1,stroke-width:2px,stroke-dasharray:5 4,color:#EAECF0;
  classDef portal fill:#1C0D4A,stroke:#9271F4,color:#EAECF0;
```

## 4 · Search and library

Searching, saved pages, tabs and places.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#000000","primaryTextColor":"#EAECF0","primaryBorderColor":"#719DF4","lineColor":"#719DF4","secondaryColor":"#101418","tertiaryColor":"#1A1A1A"}}}%%
flowchart LR
  n_search["Search tab<br/><i>Built</i>"]:::built
  n_search_results["Search results<br/><i>Built</i>"]:::built
  n_saved["Saved (empty)<br/><i>Unverified</i>"]:::unverified
  n_tabs_overview["Article tabs overview<br/><i>Built</i>"]:::built
  n_places["Places map<br/><i>Unverified</i>"]:::unverified
  n_out_article(["Go to 3 · Reading: Article"]):::portal
  n_in_article(["From 3 · Reading: Article"]):::portal
  n_in_home(["From 3 · Reading: Explore feed"]):::portal
  n_search -->|"Type a query"| n_search_results
  n_search_results -->|"Tap a result"| n_out_article
  n_in_article -->|"Tap Save, then open Saved"| n_saved
  n_in_article -->|"Tap Tabs"| n_tabs_overview
  n_in_home -->|"Tap Places tab"| n_places
  classDef built fill:#1B3731,stroke:#00AF89,stroke-width:3px,color:#EAECF0;
  classDef partly fill:#37301B,stroke:#FFCC33,stroke-width:3px,color:#EAECF0;
  classDef unverified fill:#1B2437,stroke:#6699FF,stroke-width:2px,stroke-dasharray:4 3,color:#EAECF0;
  classDef missing fill:#1B2837,stroke:#A2A9B1,stroke-width:2px,stroke-dasharray:5 4,color:#EAECF0;
  classDef portal fill:#1C0D4A,stroke:#9271F4,color:#EAECF0;
```

## 5 · Account and settings

Profile menu, settings, languages, legal links.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#000000","primaryTextColor":"#EAECF0","primaryBorderColor":"#719DF4","lineColor":"#719DF4","secondaryColor":"#101418","tertiaryColor":"#1A1A1A"}}}%%
flowchart LR
  n_profile["Account menu<br/><i>Partly built</i>"]:::partly
  n_settings["Settings<br/><i>Unverified</i>"]:::unverified
  n_donate["Donation page<br/><i>Partly built</i>"]:::partly
  n_settings_languages["Settings - Wikipedia languages<br/><i>Built</i>"]:::built
  n_privacy_policy["Privacy policy<br/><i>Unverified</i>"]:::unverified
  n_out_login(["Go to 2 · Logged out: Log in form"]):::portal
  n_in_home(["From 3 · Reading: Explore feed"]):::portal
  n_profile -->|"Tap Log in / Join Wikipedia"| n_out_login
  n_in_home -->|"Tap the profile icon"| n_profile
  n_profile -->|"Tap Settings"| n_settings
  n_settings -->|"Tap My languages"| n_settings_languages
  n_settings -->|"Tap Privacy policy"| n_privacy_policy
  n_profile -->|"Tap Donate"| n_donate
  classDef built fill:#1B3731,stroke:#00AF89,stroke-width:3px,color:#EAECF0;
  classDef partly fill:#37301B,stroke:#FFCC33,stroke-width:3px,color:#EAECF0;
  classDef unverified fill:#1B2437,stroke:#6699FF,stroke-width:2px,stroke-dasharray:4 3,color:#EAECF0;
  classDef missing fill:#1B2837,stroke:#A2A9B1,stroke-width:2px,stroke-dasharray:5 4,color:#EAECF0;
  classDef portal fill:#1C0D4A,stroke:#9271F4,color:#EAECF0;
```
