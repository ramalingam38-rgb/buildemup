# C3a Manual Accessibility Checklist

> Per S8 SPEC v1.2 LOCKED § 1.3 (i) + round 2 X8 + round 3 R3.6.
>
> Automated axe-core scans (test_c3a_a11y_auto.py) cover **structural
> violations**: missing labels, contrast ratios, ARIA mis-use, heading
> order. They do NOT cover **interaction quality**: keyboard
> navigability through complete flows, screen-reader semantics under
> dynamic content updates, focus management on route changes.
>
> Run this checklist manually before each C3a release.

## Pre-release a11y verification

For each of the 5 C3a pages (`case`, `checklist`, `done`, `aborted`,
`_test_harness`):

### Keyboard navigation
- [ ] Tab traverses all interactive elements in logical reading order.
- [ ] Shift-Tab reverses through the same path with no skipped controls.
- [ ] Enter/Space activates buttons and submits forms as expected.
- [ ] Radio groups use Arrow keys (not Tab) to move between options.
- [ ] Focus is visible at every step (no `outline: none` regressions).

### Screen reader (NVDA / VoiceOver / Orca)
- [ ] Page title is announced on load.
- [ ] Form labels are read correctly when each input gains focus.
- [ ] Error messages (`role="alert"`) are announced when displayed.
- [ ] Loading state changes are announced (or visually conveyed
  redundantly).
- [ ] Status redirects do NOT leave the screen reader confused
  about page state.

### Dynamic content
- [ ] When a 503 retry triggers, the retry state is conveyed (don't
  silently swap content).
- [ ] When a TERMINAL redirect fires, the destination page's heading
  becomes the new focus anchor.
- [ ] When `displayError` injects an alert, focus moves to it (or
  the alert is announced via `aria-live="polite"`).

### Color and contrast
- [ ] All text passes WCAG AA contrast against its background
  (axe-core reports this; spot-check with a tool like Stark for
  status colors over their custom backgrounds).
- [ ] No information is conveyed by color alone (errors have
  text + icon, not just red).

### Forms
- [ ] Required fields are marked with `required` AND a visible asterisk.
- [ ] Validation errors are tied to the specific input via
  `aria-describedby`.
- [ ] Submit buttons have descriptive labels (not "Submit" alone
  on a complex form).

## Sign-off

Reviewer: _____________
Date: _____________
Browsers tested: _____________
Screen reader tested: _____________
Notes: _____________
