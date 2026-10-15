# Plant Waterer - story map

_Generated from `stories.yaml`. The diagrams below render on GitHub. Screens with real screenshots are in `flows/` (PNG) and `story-map.html`._

**ios · demo build 1.0 · checked 2026-10-15**

Status: 🟢 built · 🟠 partly · 🟣 unverified · ⚪ missing

## Architecture by topic

Each box is a topic area; arrows show how users move between them.

| Topic | Screens | Stories | 🟢 built | 🟠 partly | 🟣 unverified | ⚪ missing | Flows |
|---|---|---|---|---|---|---|---|
| **Onboarding** | 2 | 3 | 2 | 1 | 0 | 0 | 1 · Getting started |
| **Main user journey** | 4 | 5 | 2 | 3 | 0 | 0 | 2 · Plants and watering |
| **Reminders** | 3 | 3 | 1 | 0 | 1 | 1 | 3 · Reminders |
| **Settings & sharing** | 3 | 5 | 1 | 0 | 1 | 3 | 4 · Settings and sharing |

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#1F2D26","primaryBorderColor":"#3A7D5B","lineColor":"#3A7D5B","secondaryColor":"#F7FAF9","tertiaryColor":"#F0F4F2"}}}%%
flowchart LR
  n_t_onboarding["<b>Onboarding</b><br/>2 screens · 3 stories<br/>2 built · 1 partly"]
  n_t_journey["<b>Main user journey</b><br/>4 screens · 5 stories<br/>2 built · 3 partly"]
  n_t_notifications["<b>Reminders</b><br/>3 screens · 3 stories<br/>1 built · 1 unverified · 1 missing"]
  n_t_settings["<b>Settings & sharing</b><br/>3 screens · 5 stories<br/>1 built · 1 unverified · 3 missing"]
  n_t_onboarding ==>|"Tap Skip for now +1 more"| n_t_journey
  n_t_journey ==>|"Tap +"| n_t_onboarding
  n_t_journey ==>|"Tap Edit reminder"| n_t_notifications
  n_t_notifications ==>|"Tap the notification"| n_t_journey
  n_t_journey ==>|"Tap Settings tab"| n_t_settings
  n_t_settings ==>|"Tap Default reminder time"| n_t_notifications
  style n_t_onboarding fill:#ECF2EB,stroke:#47843D,stroke-width:3px,color:#1F2D26
  style n_t_journey fill:#ECF4EF,stroke:#469660,stroke-width:3px,color:#1F2D26
  style n_t_notifications fill:#EBF2F1,stroke:#3D8476,stroke-width:3px,color:#1F2D26
  style n_t_settings fill:#ECF2F4,stroke:#468196,stroke-width:3px,color:#1F2D26
```

### Screens grouped by topic

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#1F2D26","primaryBorderColor":"#3A7D5B","lineColor":"#3A7D5B","secondaryColor":"#F7FAF9","tertiaryColor":"#F0F4F2"}}}%%
flowchart LR
  subgraph n_sg_onboarding["Onboarding"]
    direction TB
    n_welcome["Welcome<br/><i>Built</i>"]:::built
    n_add_plant["Add a plant<br/><i>Partly built</i>"]:::partly
  end
  subgraph n_sg_journey["Main user journey"]
    direction TB
    n_plant_list["My plants<br/><i>Partly built</i>"]:::partly
    n_plant_detail["Plant detail<br/><i>Partly built</i>"]:::partly
    n_watered["Watered! (confirmation)<br/><i>Partly built</i>"]:::partly
    n_water_history["Watering history<br/><i>Partly built</i>"]:::partly
  end
  subgraph n_sg_notifications["Reminders"]
    direction TB
    n_reminders["Reminder schedule<br/><i>Partly built</i>"]:::partly
    n_notif_permission["Allow notifications (system alert)<br/><i>Unverified</i>"]:::unverified
    n_push["Reminder notification<br/><i>Partly built</i>"]:::partly
  end
  subgraph n_sg_settings["Settings & sharing"]
    direction TB
    n_settings["Settings<br/><i>Partly built</i>"]:::partly
    n_share_garden["Share my garden<br/><i>Missing</i>"]:::missing
    n_sitter_view["Sitter checklist<br/><i>Missing</i>"]:::missing
  end
  n_welcome --> n_add_plant
  n_welcome ==>|"Tap Skip for now"| n_plant_list
  n_plant_list --> n_plant_detail
  n_plant_list ==>|"Tap +"| n_add_plant
  n_add_plant ==>|"Tap Save"| n_plant_list
  n_plant_detail --> n_watered
  n_watered --> n_plant_list
  n_plant_detail --> n_water_history
  n_plant_detail ==>|"Tap Edit reminder"| n_reminders
  n_reminders --> n_notif_permission
  n_notif_permission -.-> n_push
  n_push ==>|"Tap the notification"| n_plant_detail
  n_plant_list ==>|"Tap Settings tab"| n_settings
  n_settings ==>|"Tap Default reminder time"| n_reminders
  n_settings --> n_share_garden
  n_share_garden --> n_sitter_view
  style n_sg_onboarding fill:#F0F5EF,stroke:#47843D,stroke-width:2px
  style n_sg_journey fill:#F0F6F2,stroke:#469660,stroke-width:2px
  style n_sg_notifications fill:#EFF5F4,stroke:#3D8476,stroke-width:2px
  style n_sg_settings fill:#F0F4F6,stroke:#468196,stroke-width:2px
  classDef built fill:#E3F7ED,stroke:#418B66,stroke-width:3px,color:#1F2D26;
  classDef partly fill:#F7F6E3,stroke:#AEA951,stroke-width:3px,color:#1F2D26;
  classDef unverified fill:#E3F2F7,stroke:#41798B,stroke-width:2px,stroke-dasharray:4 3,color:#1F2D26;
  classDef missing fill:#E3F7EE,stroke:#8B9C94,stroke-width:2px,stroke-dasharray:5 4,color:#1F2D26;
  classDef portal fill:#E3F1F2,stroke:#3A787D,color:#1F2D26;
```

## Story map (personas x flows)

| Persona | 1 · Getting started | 2 · Plants and watering | 3 · Reminders | 4 · Settings and sharing |
|---|---|---|---|---|
| **Busy gardener** |  | 🟢 US-04<br/>🟢 US-05<br/>🟠 US-06<br/>🟠 US-11 | 🟢 US-07<br/>⚪ US-09 | 🟢 US-12<br/>⚪ US-13<br/>🟣 US-16 |
| **Plant beginner** | 🟢 US-01<br/>🟢 US-02<br/>🟠 US-03 | 🟠 US-10 | 🟣 US-08 |  |
| **Plant sitter** |  |  |  | ⚪ US-14<br/>⚪ US-15 |

## Flows overview

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#1F2D26","primaryBorderColor":"#3A7D5B","lineColor":"#3A7D5B","secondaryColor":"#F7FAF9","tertiaryColor":"#F0F4F2"}}}%%
flowchart LR
  n_onboarding["<b>1 · Getting started</b><br/>2 screens · 3 stories<br/>2 built · 1 partly"]:::flow
  n_plants["<b>2 · Plants and watering</b><br/>4 screens · 5 stories<br/>2 built · 3 partly"]:::flow
  n_reminders["<b>3 · Reminders</b><br/>3 screens · 3 stories<br/>1 built · 1 unverified · 1 missing"]:::flow
  n_sharing["<b>4 · Settings and sharing</b><br/>3 screens · 5 stories<br/>1 built · 1 unverified · 3 missing"]:::flow
  n_onboarding -->|"Tap Skip for now"| n_plants
  n_plants -->|"Tap +"| n_onboarding
  n_plants -->|"Tap Edit reminder"| n_reminders
  n_reminders -->|"Tap the notification"| n_plants
  n_plants -->|"Tap Settings tab"| n_sharing
  n_sharing -->|"Tap Default reminder time"| n_reminders
  classDef flow fill:#FFFFFF,stroke:#3A7D5B,stroke-width:3px,color:#1F2D26;
```

## 1 · Getting started

First launch up to the first plant.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#1F2D26","primaryBorderColor":"#3A7D5B","lineColor":"#3A7D5B","secondaryColor":"#F7FAF9","tertiaryColor":"#F0F4F2"}}}%%
flowchart LR
  n_welcome["Welcome<br/><i>Built</i>"]:::built
  n_add_plant["Add a plant<br/><i>Partly built</i>"]:::partly
  n_out_plant_list(["Go to 2 · Plants and watering: My plants"]):::portal
  n_in_plant_list(["From 2 · Plants and watering: My plants"]):::portal
  n_welcome -->|"Tap Add my first plant"| n_add_plant
  n_welcome -->|"Tap Skip for now"| n_out_plant_list
  n_in_plant_list -->|"Tap +"| n_add_plant
  n_add_plant -->|"Tap Save"| n_out_plant_list
  classDef built fill:#E3F7ED,stroke:#418B66,stroke-width:3px,color:#1F2D26;
  classDef partly fill:#F7F6E3,stroke:#AEA951,stroke-width:3px,color:#1F2D26;
  classDef unverified fill:#E3F2F7,stroke:#41798B,stroke-width:2px,stroke-dasharray:4 3,color:#1F2D26;
  classDef missing fill:#E3F7EE,stroke:#8B9C94,stroke-width:2px,stroke-dasharray:5 4,color:#1F2D26;
  classDef portal fill:#E3F1F2,stroke:#3A787D,color:#1F2D26;
```

## 2 · Plants and watering

Day-to-day use - see plants, water them, check history.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#1F2D26","primaryBorderColor":"#3A7D5B","lineColor":"#3A7D5B","secondaryColor":"#F7FAF9","tertiaryColor":"#F0F4F2"}}}%%
flowchart LR
  n_plant_list["My plants<br/><i>Partly built</i>"]:::partly
  n_plant_detail["Plant detail<br/><i>Partly built</i>"]:::partly
  n_watered["Watered! (confirmation)<br/><i>Partly built</i>"]:::partly
  n_water_history["Watering history<br/><i>Partly built</i>"]:::partly
  n_in_welcome(["From 1 · Getting started: Welcome"]):::portal
  n_out_add_plant(["Go to 1 · Getting started: Add a plant"]):::portal
  n_in_add_plant(["From 1 · Getting started: Add a plant"]):::portal
  n_out_reminders(["Go to 3 · Reminders: Reminder schedule"]):::portal
  n_in_push(["From 3 · Reminders: Reminder notification"]):::portal
  n_out_settings(["Go to 4 · Settings and sharing: Settings"]):::portal
  n_in_welcome -->|"Tap Skip for now"| n_plant_list
  n_plant_list -->|"Tap a plant card"| n_plant_detail
  n_plant_list -->|"Tap +"| n_out_add_plant
  n_in_add_plant -->|"Tap Save"| n_plant_list
  n_plant_detail -->|"Tap Water now"| n_watered
  n_watered -->|"Tap Done"| n_plant_list
  n_plant_detail -->|"Tap History"| n_water_history
  n_plant_detail -->|"Tap Edit reminder"| n_out_reminders
  n_in_push -->|"Tap the notification"| n_plant_detail
  n_plant_list -->|"Tap Settings tab"| n_out_settings
  classDef built fill:#E3F7ED,stroke:#418B66,stroke-width:3px,color:#1F2D26;
  classDef partly fill:#F7F6E3,stroke:#AEA951,stroke-width:3px,color:#1F2D26;
  classDef unverified fill:#E3F2F7,stroke:#41798B,stroke-width:2px,stroke-dasharray:4 3,color:#1F2D26;
  classDef missing fill:#E3F7EE,stroke:#8B9C94,stroke-width:2px,stroke-dasharray:5 4,color:#1F2D26;
  classDef portal fill:#E3F1F2,stroke:#3A787D,color:#1F2D26;
```

## 3 · Reminders

Set a schedule and get nudged.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#1F2D26","primaryBorderColor":"#3A7D5B","lineColor":"#3A7D5B","secondaryColor":"#F7FAF9","tertiaryColor":"#F0F4F2"}}}%%
flowchart LR
  n_reminders["Reminder schedule<br/><i>Partly built</i>"]:::partly
  n_notif_permission["Allow notifications (system alert)<br/><i>Unverified</i>"]:::unverified
  n_push["Reminder notification<br/><i>Partly built</i>"]:::partly
  n_in_plant_detail(["From 2 · Plants and watering: Plant detail"]):::portal
  n_out_plant_detail(["Go to 2 · Plants and watering: Plant detail"]):::portal
  n_in_settings(["From 4 · Settings and sharing: Settings"]):::portal
  n_in_plant_detail -->|"Tap Edit reminder"| n_reminders
  n_reminders -->|"Tap Turn on reminders"| n_notif_permission
  n_notif_permission -.->|"(Time passes) reminder arrives"| n_push
  n_push -->|"Tap the notification"| n_out_plant_detail
  n_in_settings -->|"Tap Default reminder time"| n_reminders
  classDef built fill:#E3F7ED,stroke:#418B66,stroke-width:3px,color:#1F2D26;
  classDef partly fill:#F7F6E3,stroke:#AEA951,stroke-width:3px,color:#1F2D26;
  classDef unverified fill:#E3F2F7,stroke:#41798B,stroke-width:2px,stroke-dasharray:4 3,color:#1F2D26;
  classDef missing fill:#E3F7EE,stroke:#8B9C94,stroke-width:2px,stroke-dasharray:5 4,color:#1F2D26;
  classDef portal fill:#E3F1F2,stroke:#3A787D,color:#1F2D26;
```

## 4 · Settings and sharing

App settings and handing the plants to a sitter.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Helvetica","fontSize":"16px","primaryColor":"#FFFFFF","primaryTextColor":"#1F2D26","primaryBorderColor":"#3A7D5B","lineColor":"#3A7D5B","secondaryColor":"#F7FAF9","tertiaryColor":"#F0F4F2"}}}%%
flowchart LR
  n_settings["Settings<br/><i>Partly built</i>"]:::partly
  n_share_garden["Share my garden<br/><i>Missing</i>"]:::missing
  n_sitter_view["Sitter checklist<br/><i>Missing</i>"]:::missing
  n_in_plant_list(["From 2 · Plants and watering: My plants"]):::portal
  n_out_reminders(["Go to 3 · Reminders: Reminder schedule"]):::portal
  n_in_plant_list -->|"Tap Settings tab"| n_settings
  n_settings -->|"Tap Default reminder time"| n_out_reminders
  n_settings -->|"Tap Share my garden"| n_share_garden
  n_share_garden -->|"Send invite"| n_sitter_view
  classDef built fill:#E3F7ED,stroke:#418B66,stroke-width:3px,color:#1F2D26;
  classDef partly fill:#F7F6E3,stroke:#AEA951,stroke-width:3px,color:#1F2D26;
  classDef unverified fill:#E3F2F7,stroke:#41798B,stroke-width:2px,stroke-dasharray:4 3,color:#1F2D26;
  classDef missing fill:#E3F7EE,stroke:#8B9C94,stroke-width:2px,stroke-dasharray:5 4,color:#1F2D26;
  classDef portal fill:#E3F1F2,stroke:#3A787D,color:#1F2D26;
```
