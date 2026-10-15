# Wikipedia (iOS) - story map

_Generated from `stories.yaml`. The diagrams below render on GitHub. Screens with real screenshots are in `flows/` (PNG) and `story-map.html`._

**ios · main @ ca8aaeb · checked 2026-10-15**

> Unofficial illustration of the open-source Wikipedia iOS app (MIT); not affiliated with or endorsed by the Wikimedia Foundation. Screenshots captured 2026-10-15 in the iOS simulator from commit ca8aaeb95639ca82105bcd5510277d8dde0e420e; trademarks and content belong to their owners (Wikipedia content CC BY-SA).

Status: 🟢 built · 🟠 partly · 🟣 unverified · ⚪ missing

## Architecture by topic

Each box is a topic area; arrows show how users move between them.

| Topic | Screens | Stories | 🟢 built | 🟠 partly | 🟣 unverified | ⚪ missing | Flows |
|---|---|---|---|---|---|---|---|
| **Onboarding** | 6 | 6 | 5 | 0 | 1 | 0 | 1 · First launch |
| **Login & account access** | 2 | 3 | 2 | 0 | 1 | 0 | 2 · Login |
| **Main user journey** | 9 | 11 | 9 | 0 | 2 | 0 | 3 · Reading |
| **Content & library** | 5 | 5 | 4 | 0 | 1 | 0 | 4 · Search and library |
| **Settings & account** | 6 | 3 | 2 | 0 | 1 | 0 | 5 · Profile and settings, 7 · Dark theme |
| **Donations** | 1 | 1 | 0 | 1 | 0 | 0 | 6 · Donate |
| **Support & legal** | 1 | 0 | 0 | 0 | 0 | 0 |  |

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_t_onboarding["<b>Onboarding</b><br/>6 screens · 6 stories<br/>5 built · 1 unverified"]
  n_t_access["<b>Login & account access</b><br/>2 screens · 3 stories<br/>2 built · 1 unverified"]
  n_t_journey["<b>Main user journey</b><br/>9 screens · 11 stories<br/>9 built · 2 unverified"]
  n_t_library["<b>Content & library</b><br/>5 screens · 5 stories<br/>4 built · 1 unverified"]
  n_t_settings["<b>Settings & account</b><br/>6 screens · 3 stories<br/>2 built · 1 unverified"]
  n_t_payments["<b>Donations</b><br/>1 screens · 1 stories<br/>1 partly"]
  n_t_support["<b>Support & legal</b><br/>1 screens · 0 stories<br/>no stories"]
  n_t_onboarding ==>|"Tap Next (onboarding complete)"| n_t_journey
  n_t_settings ==>|"Tap Log in / Join Wikipedia"| n_t_access
  n_t_journey ==>|"Tap search and type a query +4 more"| n_t_library
  n_t_library ==>|"Tap a result"| n_t_journey
  n_t_journey ==>|"(Tap Activity tab)"| n_t_access
  n_t_journey ==>|"Tap the profile icon"| n_t_settings
  n_t_settings ==>|"(Tap Privacy policy)"| n_t_support
  n_t_settings ==>|"Tap Donate"| n_t_payments
  style n_t_onboarding fill:#EAF9F1,stroke:#31C476,stroke-width:3px,color:#202122
  style n_t_access fill:#EBFAF8,stroke:#3FCFC2,stroke-width:3px,color:#202122
  style n_t_journey fill:#EAF3F9,stroke:#3190C4,stroke-width:3px,color:#202122
  style n_t_library fill:#EBEEFA,stroke:#3F5CCF,stroke-width:3px,color:#202122
  style n_t_settings fill:#EEEAF9,stroke:#5531C4,stroke-width:3px,color:#202122
  style n_t_payments fill:#F5EBFA,stroke:#A23FCF,stroke-width:3px,color:#202122
  style n_t_support fill:#F9EAF7,stroke:#C431B0,stroke-width:3px,color:#202122
```

### Screens grouped by topic

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
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
    n_login["Log in form<br/><i>Unverified</i>"]:::unverified
    n_activity["Activity (logged out)<br/><i>Built</i>"]:::built
  end
  subgraph n_sg_journey["Main user journey"]
    direction TB
    n_home["Explore feed - Community<br/><i>Built</i>"]:::built
    n_home_foryou["Explore feed - For You<br/><i>Built</i>"]:::built
    n_article["Article<br/><i>Unverified</i>"]:::unverified
    n_article_toc["Article - table of contents<br/><i>Built</i>"]:::built
    n_article_theme["Article - reading themes<br/><i>Built</i>"]:::built
    n_article_overflow["Article - more menu<br/><i>Built</i>"]:::built
    n_article_find["Article - find in article<br/><i>Built</i>"]:::built
    n_article_languages["Article - change language<br/><i>Built</i>"]:::built
    n_image_gallery["Lead image viewer<br/><i>Unverified</i>"]:::unverified
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
    n_dark_home["Explore feed (dark)<br/><i>Built</i>"]:::built
    n_dark_search_results["Search results (dark)<br/><i>Built</i>"]:::built
    n_dark_article["Article (dark)<br/><i>Built</i>"]:::built
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
  n_ob_feed ==>|"Tap Next (onboarding complete)"| n_home
  n_profile ==>|"Tap Log in / Join Wikipedia"| n_login
  n_activity -.-> n_login
  n_home --> n_home_foryou
  n_article --> n_article_toc
  n_article --> n_article_theme
  n_article --> n_article_overflow
  n_article --> n_article_find
  n_article --> n_article_languages
  n_article -.-> n_image_gallery
  n_home ==>|"Tap search and type a query"| n_search_results
  n_search --> n_search_results
  n_search_results ==>|"Tap a result"| n_article
  n_article -.->|"(Tap Save, then open Saved)"| n_saved
  n_article -.->|"(Tap Tabs)"| n_tabs_overview
  n_home ==>|"Tap the tabs button"| n_tabs_overview
  n_home -.->|"(Tap Places tab)"| n_places
  n_home -.->|"(Tap Activity tab)"| n_activity
  n_home ==>|"Tap the profile icon"| n_profile
  n_profile --> n_settings
  n_settings --> n_settings_languages
  n_settings -.->|"(Tap Privacy policy)"| n_privacy_policy
  n_profile ==>|"Tap Donate"| n_donate
  n_dark_home --> n_dark_search_results
  n_dark_search_results --> n_dark_article
  style n_sg_onboarding fill:#EEFAF4,stroke:#31C476,stroke-width:2px
  style n_sg_access fill:#EFFBFA,stroke:#3FCFC2,stroke-width:2px
  style n_sg_journey fill:#EEF6FA,stroke:#3190C4,stroke-width:2px
  style n_sg_library fill:#EFF1FB,stroke:#3F5CCF,stroke-width:2px
  style n_sg_settings fill:#F1EEFA,stroke:#5531C4,stroke-width:2px
  style n_sg_payments fill:#F7EFFB,stroke:#A23FCF,stroke-width:2px
  style n_sg_support fill:#FAEEF8,stroke:#C431B0,stroke-width:2px
  classDef built fill:#E3F7F3,stroke:#14866D,stroke-width:3px,color:#202122;
  classDef partly fill:#F7F2E3,stroke:#D9A300,stroke-width:3px,color:#202122;
  classDef unverified fill:#E3EAF7,stroke:#6B8FD6,stroke-width:2px,stroke-dasharray:4 3,color:#202122;
  classDef missing fill:#E3ECF7,stroke:#72777D,stroke-width:2px,stroke-dasharray:5 4,color:#202122;
  classDef portal fill:#E4DEF7,stroke:#5933CC,color:#202122;
```

## Story map (personas x flows)

| Persona | 1 · First launch | 2 · Login | 3 · Reading | 4 · Search and library | 5 · Profile and settings | 7 · Dark theme | 6 · Donate |
|---|---|---|---|---|---|---|---|
| **First-time user** | 🟢 US-01<br/>🟢 US-02<br/>🟢 US-04<br/>🟢 US-05<br/>🟣 US-06 |  |  |  |  |  |  |
| **Curious reader** |  | 🟢 US-09 | 🟢 US-07<br/>🟢 US-11<br/>🟢 US-12<br/>🟢 US-13<br/>🟢 US-14<br/>🟢 US-15<br/>🟢 US-16<br/>🟣 US-18<br/>🟢 US-19 | 🟢 US-20<br/>🟢 US-21<br/>🟢 US-24<br/>🟣 US-25 | 🟣 US-29 | 🟢 US-27 | 🟠 US-28 |
| **Multilingual reader** | 🟢 US-03 |  | 🟢 US-17 |  | 🟢 US-26 |  |  |
| **Offline commuter** |  |  | 🟣 US-22 | 🟢 US-23 |  |  |  |
| **Contributor** |  | 🟢 US-08<br/>🟣 US-10 |  |  |  |  |  |

## Flows overview

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_first_run["<b>1 · First launch</b><br/>6 screens · 6 stories<br/>5 built · 1 unverified"]:::flow
  n_login["<b>2 · Login</b><br/>2 screens · 3 stories<br/>2 built · 1 unverified"]:::flow
  n_reading["<b>3 · Reading</b><br/>9 screens · 11 stories<br/>9 built · 2 unverified"]:::flow
  n_discover["<b>4 · Search and library</b><br/>5 screens · 5 stories<br/>4 built · 1 unverified"]:::flow
  n_preferences["<b>5 · Profile and settings</b><br/>4 screens · 2 stories<br/>1 built · 1 unverified"]:::flow
  n_dark["<b>7 · Dark theme</b><br/>3 screens · 1 stories<br/>1 built"]:::flow
  n_support_money["<b>6 · Donate</b><br/>1 screens · 1 stories<br/>1 partly"]:::flow
  n_first_run -->|"Tap Next (onboarding complete)"| n_reading
  n_preferences -->|"Tap Log in / Join Wikipedia"| n_login
  n_reading -->|"Tap search and type a query"| n_discover
  n_discover -->|"Tap a result"| n_reading
  n_reading -->|"(Tap Activity tab)"| n_login
  n_reading -->|"Tap the profile icon"| n_preferences
  n_preferences -->|"Tap Donate"| n_support_money
  classDef flow fill:#FFFFFF,stroke:#3366CC,stroke-width:3px,color:#202122;
```

## 1 · First launch

Six onboarding pages, then the Explore feed.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_ob_intro["Onboarding - welcome<br/><i>Built</i>"]:::built
  n_ob_privacy["Onboarding - data and privacy<br/><i>Built</i>"]:::built
  n_ob_languages["Onboarding - languages<br/><i>Built</i>"]:::built
  n_ob_personalize["Onboarding - follow your curiosity<br/><i>Unverified</i>"]:::unverified
  n_ob_interests["Onboarding - interests<br/><i>Unverified</i>"]:::unverified
  n_ob_feed["Onboarding - feed preference<br/><i>Unverified</i>"]:::unverified
  n_out_home(["Go to 3 · Reading: Explore feed - Community"]):::portal
  n_ob_intro -->|"Tap Next"| n_ob_privacy
  n_ob_privacy -->|"Tap Next"| n_ob_languages
  n_ob_languages -->|"Tap Next"| n_ob_personalize
  n_ob_personalize -->|"Tap Next"| n_ob_interests
  n_ob_interests -->|"Tap Next"| n_ob_feed
  n_ob_feed -->|"Tap Next (onboarding complete)"| n_out_home
  classDef built fill:#E3F7F3,stroke:#14866D,stroke-width:3px,color:#202122;
  classDef partly fill:#F7F2E3,stroke:#D9A300,stroke-width:3px,color:#202122;
  classDef unverified fill:#E3EAF7,stroke:#6B8FD6,stroke-width:2px,stroke-dasharray:4 3,color:#202122;
  classDef missing fill:#E3ECF7,stroke:#72777D,stroke-width:2px,stroke-dasharray:5 4,color:#202122;
  classDef portal fill:#E4DEF7,stroke:#5933CC,color:#202122;
```

## 2 · Login

Logged-out prompts that lead to the login form.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_activity["Activity (logged out)<br/><i>Built</i>"]:::built
  n_login["Log in form<br/><i>Unverified</i>"]:::unverified
  n_in_profile(["From 5 · Profile and settings: Account menu"]):::portal
  n_in_home(["From 3 · Reading: Explore feed - Community"]):::portal
  n_in_profile -->|"Tap Log in / Join Wikipedia"| n_login
  n_activity -.->|"(Tap Log in / Join Wikipedia)"| n_login
  n_in_home -.->|"(Tap Activity tab)"| n_activity
  classDef built fill:#E3F7F3,stroke:#14866D,stroke-width:3px,color:#202122;
  classDef partly fill:#F7F2E3,stroke:#D9A300,stroke-width:3px,color:#202122;
  classDef unverified fill:#E3EAF7,stroke:#6B8FD6,stroke-width:2px,stroke-dasharray:4 3,color:#202122;
  classDef missing fill:#E3ECF7,stroke:#72777D,stroke-width:2px,stroke-dasharray:5 4,color:#202122;
  classDef portal fill:#E4DEF7,stroke:#5933CC,color:#202122;
```

## 3 · Reading

From the Explore feed into an article and its tools.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_home["Explore feed - Community<br/><i>Built</i>"]:::built
  n_home_foryou["Explore feed - For You<br/><i>Built</i>"]:::built
  n_article["Article<br/><i>Unverified</i>"]:::unverified
  n_article_toc["Article - table of contents<br/><i>Built</i>"]:::built
  n_article_theme["Article - reading themes<br/><i>Built</i>"]:::built
  n_article_overflow["Article - more menu<br/><i>Built</i>"]:::built
  n_article_find["Article - find in article<br/><i>Built</i>"]:::built
  n_article_languages["Article - change language<br/><i>Built</i>"]:::built
  n_image_gallery["Lead image viewer<br/><i>Unverified</i>"]:::unverified
  n_in_ob_feed(["From 1 · First launch: Onboarding - feed preference"]):::portal
  n_out_search_results(["Go to 4 · Search and library: Search results"]):::portal
  n_in_search_results(["From 4 · Search and library: Search results"]):::portal
  n_out_saved(["Go to 4 · Search and library: Saved (empty)"]):::portal
  n_out_tabs_overview(["Go to 4 · Search and library: Article tabs overview"]):::portal
  n_out_places(["Go to 4 · Search and library: Places map"]):::portal
  n_out_activity(["Go to 2 · Login: Activity (logged out)"]):::portal
  n_out_profile(["Go to 5 · Profile and settings: Account menu"]):::portal
  n_in_ob_feed -->|"Tap Next (onboarding complete)"| n_home
  n_home -->|"Tap For You"| n_home_foryou
  n_article -->|"Tap Contents"| n_article_toc
  n_article -->|"Tap Reading themes"| n_article_theme
  n_article -->|"Tap the more menu"| n_article_overflow
  n_article -->|"Tap Find in article"| n_article_find
  n_article -->|"Tap Languages"| n_article_languages
  n_article -.->|"(Tap the lead image)"| n_image_gallery
  n_home -->|"Tap search and type a query"| n_out_search_results
  n_in_search_results -->|"Tap a result"| n_article
  n_article -.->|"(Tap Save, then open Saved)"| n_out_saved
  n_article -.->|"(Tap Tabs)"| n_out_tabs_overview
  n_home -->|"Tap the tabs button"| n_out_tabs_overview
  n_home -.->|"(Tap Places tab)"| n_out_places
  n_home -.->|"(Tap Activity tab)"| n_out_activity
  n_home -->|"Tap the profile icon"| n_out_profile
  classDef built fill:#E3F7F3,stroke:#14866D,stroke-width:3px,color:#202122;
  classDef partly fill:#F7F2E3,stroke:#D9A300,stroke-width:3px,color:#202122;
  classDef unverified fill:#E3EAF7,stroke:#6B8FD6,stroke-width:2px,stroke-dasharray:4 3,color:#202122;
  classDef missing fill:#E3ECF7,stroke:#72777D,stroke-width:2px,stroke-dasharray:5 4,color:#202122;
  classDef portal fill:#E4DEF7,stroke:#5933CC,color:#202122;
```

## 4 · Search and library

Searching, tabs, saved pages, places, activity.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_search["Search tab<br/><i>Built</i>"]:::built
  n_search_results["Search results<br/><i>Built</i>"]:::built
  n_saved["Saved (empty)<br/><i>Unverified</i>"]:::unverified
  n_tabs_overview["Article tabs overview<br/><i>Built</i>"]:::built
  n_places["Places map<br/><i>Unverified</i>"]:::unverified
  n_in_home(["From 3 · Reading: Explore feed - Community"]):::portal
  n_out_article(["Go to 3 · Reading: Article"]):::portal
  n_in_article(["From 3 · Reading: Article"]):::portal
  n_in_home -->|"Tap search and type a query"| n_search_results
  n_search -->|"Type a query"| n_search_results
  n_search_results -->|"Tap a result"| n_out_article
  n_in_article -.->|"(Tap Save, then open Saved)"| n_saved
  n_in_article -.->|"(Tap Tabs)"| n_tabs_overview
  n_in_home -->|"Tap the tabs button"| n_tabs_overview
  n_in_home -.->|"(Tap Places tab)"| n_places
  classDef built fill:#E3F7F3,stroke:#14866D,stroke-width:3px,color:#202122;
  classDef partly fill:#F7F2E3,stroke:#D9A300,stroke-width:3px,color:#202122;
  classDef unverified fill:#E3EAF7,stroke:#6B8FD6,stroke-width:2px,stroke-dasharray:4 3,color:#202122;
  classDef missing fill:#E3ECF7,stroke:#72777D,stroke-width:2px,stroke-dasharray:5 4,color:#202122;
  classDef portal fill:#E4DEF7,stroke:#5933CC,color:#202122;
```

## 5 · Profile and settings

Profile menu, settings and languages.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_profile["Account menu<br/><i>Partly built</i>"]:::partly
  n_settings["Settings<br/><i>Unverified</i>"]:::unverified
  n_settings_languages["Settings - Wikipedia languages<br/><i>Built</i>"]:::built
  n_privacy_policy["Privacy policy<br/><i>Unverified</i>"]:::unverified
  n_out_login(["Go to 2 · Login: Log in form"]):::portal
  n_in_home(["From 3 · Reading: Explore feed - Community"]):::portal
  n_out_donate(["Go to 6 · Donate: Donation page"]):::portal
  n_profile -->|"Tap Log in / Join Wikipedia"| n_out_login
  n_in_home -->|"Tap the profile icon"| n_profile
  n_profile -->|"Tap Settings"| n_settings
  n_settings -->|"Tap My languages"| n_settings_languages
  n_settings -.->|"(Tap Privacy policy)"| n_privacy_policy
  n_profile -->|"Tap Donate"| n_out_donate
  classDef built fill:#E3F7F3,stroke:#14866D,stroke-width:3px,color:#202122;
  classDef partly fill:#F7F2E3,stroke:#D9A300,stroke-width:3px,color:#202122;
  classDef unverified fill:#E3EAF7,stroke:#6B8FD6,stroke-width:2px,stroke-dasharray:4 3,color:#202122;
  classDef missing fill:#E3ECF7,stroke:#72777D,stroke-width:2px,stroke-dasharray:5 4,color:#202122;
  classDef portal fill:#E4DEF7,stroke:#5933CC,color:#202122;
```

## 7 · Dark theme

The same screens with the app theme set to dark.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_dark_home["Explore feed (dark)<br/><i>Built</i>"]:::built
  n_dark_search_results["Search results (dark)<br/><i>Built</i>"]:::built
  n_dark_article["Article (dark)<br/><i>Built</i>"]:::built
  n_dark_home -->|"Tap search and type a query"| n_dark_search_results
  n_dark_search_results -->|"Tap a result"| n_dark_article
  classDef built fill:#E3F7F3,stroke:#14866D,stroke-width:3px,color:#202122;
  classDef partly fill:#F7F2E3,stroke:#D9A300,stroke-width:3px,color:#202122;
  classDef unverified fill:#E3EAF7,stroke:#6B8FD6,stroke-width:2px,stroke-dasharray:4 3,color:#202122;
  classDef missing fill:#E3ECF7,stroke:#72777D,stroke-width:2px,stroke-dasharray:5 4,color:#202122;
  classDef portal fill:#E4DEF7,stroke:#5933CC,color:#202122;
```

## 6 · Donate

The Donate row in the profile menu.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#202122","primaryBorderColor":"#3366CC","lineColor":"#3366CC","secondaryColor":"#F8F9FA","tertiaryColor":"#F0F2F4"}}}%%
flowchart LR
  n_donate["Donation page<br/><i>Partly built</i>"]:::partly
  n_in_profile(["From 5 · Profile and settings: Account menu"]):::portal
  n_in_profile -->|"Tap Donate"| n_donate
  classDef built fill:#E3F7F3,stroke:#14866D,stroke-width:3px,color:#202122;
  classDef partly fill:#F7F2E3,stroke:#D9A300,stroke-width:3px,color:#202122;
  classDef unverified fill:#E3EAF7,stroke:#6B8FD6,stroke-width:2px,stroke-dasharray:4 3,color:#202122;
  classDef missing fill:#E3ECF7,stroke:#72777D,stroke-width:2px,stroke-dasharray:5 4,color:#202122;
  classDef portal fill:#E4DEF7,stroke:#5933CC,color:#202122;
```
