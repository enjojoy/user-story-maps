# Plant Waterer - gaps and risks

_Generated from `stories.yaml` (`gaps:`). Ordered by severity._

## High severity

### G-01 - Reminders silently fail when notifications are denied

If the user taps Don't Allow, the app never says reminders are off and offers no in-app fallback.

Where: `src/notifications`

Related stories: US-08

## Medium severity

### G-02 - No undo after Water now

An accidental tap logs a watering and resets the schedule, with no way to reverse it.

Where: `src/screens/PlantDetail`

Related stories: US-05

### G-03 - Empty plant list after Skip for now has no guidance

Users who skip onboarding land on a blank list with no hint to tap +.

Related stories: US-01, US-04

## Low severity

### G-04 - Watering history not captured

The screen needs 30 days of demo data before it can be screenshotted.

Related stories: US-06
