# Playtest Pending Items

The running backlog of bugs and usability issues found during
[agentic UI playtests](./README.md). Newest at the top of **Open**. When an item
is fixed, move it to **Resolved** with the commit/PR that closed it.

This file is the durable signal across runs — keep it honest. A growing list is
fine; a list that hides known problems is not.

## Entry format

```
### PT-<n> — <one-line title>
- **Status:** open | resolved
- **Severity:** blocking | major | minor
- **Type:** bug | usability
- **Phase:** <scenario phase, e.g. "6 — Combat">
- **Found:** <run log filename, e.g. runs/2026-06-26-first-pass.md>
- **Steps:** what you did, through the UI.
- **Observed:** what actually happened.
- **Expected:** what should have happened.
- **Evidence:** screenshot reference / API or console error / log excerpt.
- **Notes:** hypotheses, suspected file, workaround if any.
```

`severity`: **blocking** = can't proceed through the UI; **major** = wrong or
broken but routable around; **minor** = cosmetic or small friction.
`type`: **bug** = behaves incorrectly; **usability** = behaves as built but is
hard/confusing/missing an affordance a real player or DM would expect.

`PT-<n>` is a simple incrementing id — next id is **PT-1**.

---

## Open

_No items logged yet. The first playtest run will populate this section._

## Resolved

_None yet._
