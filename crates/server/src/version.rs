//! The rules-data version guard: which pins this build knows, what a
//! replay against current data yields, and the repair walk for logs that
//! no longer replay. Status is computed at load and never written; every
//! state change goes through an explicit route in `routes.rs`.

use std::collections::BTreeSet;
use std::path::Path;

use engine_core::{EngineError, EngineOps};
use types::{
    ClearedDecision, Decision, ReplayOutcome, Selection, SheetDiff, SheetView, VersionStatus,
};

use crate::persistence::{DocState, Loaded};

/// The version set this build recognizes.
pub struct KnownVersions {
    /// The shipped manifest version — what new characters pin.
    pub current: String,
    /// Versions that are "older known": listed in the manifest's
    /// supersedes chain AND carrying a recorded ID set in
    /// shipped-versions.json (plus any test-support extras).
    pub older_known: BTreeSet<String>,
}

impl KnownVersions {
    /// Intersect the manifest's supersedes chain with the versions that
    /// have a recorded ID set, then merge the test-support extras when the
    /// hidden `--extra-known-versions` flag names a file (same JSON shape
    /// as rules-data/shipped-versions.json). TEST-SUPPORT ONLY: the checks
    /// suite uses the flag to fabricate a prior shipped version; production
    /// never passes it, and its presence is announced on stderr.
    pub fn assemble(
        system: &str,
        current: &str,
        supersedes: &[String],
        shipped_versions_json: &str,
        extra_known_versions: Option<&Path>,
    ) -> Result<KnownVersions, String> {
        let recorded = parse_version_keys(shipped_versions_json)
            .map_err(|e| format!("shipped-versions.json ({system}) is corrupt: {e}"))?;
        let mut older_known: BTreeSet<String> = supersedes
            .iter()
            .filter(|v| recorded.contains(*v))
            .cloned()
            .collect();
        if let Some(path) = extra_known_versions {
            let extra = parse_extra_versions(path, system)?;
            if !extra.is_empty() {
                eprintln!(
                    "TEST-SUPPORT: --extra-known-versions active — treating {} extra {system} version(s) as older-known",
                    extra.len()
                );
            }
            // Extras count as both superseded and recorded.
            older_known.extend(extra);
        }
        older_known.remove(current);
        Ok(KnownVersions {
            current: current.to_string(),
            older_known,
        })
    }
}

/// The test-support extras file is keyed by system: `{"<system>":
/// {"versions": {"<ver>": [ids...]}}}` — each ruleset's set takes only its
/// own key, so a fabricated prior version can never land in another
/// system's guard. Every key must name a shipped system (asserted by the
/// caller over the full registry; here an unknown key is simply not ours).
fn parse_extra_versions(path: &Path, system: &str) -> Result<BTreeSet<String>, String> {
    let text = std::fs::read_to_string(path).map_err(|e| {
        format!(
            "--extra-known-versions file '{}' unreadable: {e}",
            path.display()
        )
    })?;
    let value: serde_json::Value = serde_json::from_str(&text).map_err(|e| {
        format!(
            "--extra-known-versions file '{}' is corrupt: {e}",
            path.display()
        )
    })?;
    let object = value.as_object().ok_or_else(|| {
        format!(
            "--extra-known-versions file '{}' must be an object keyed by system",
            path.display()
        )
    })?;
    if object.contains_key("versions") {
        return Err(format!(
            "--extra-known-versions file '{}' uses the unkeyed shape — key it by system: {{\"<system>\": {{\"versions\": ...}}}}",
            path.display()
        ));
    }
    match object.get(system) {
        None => Ok(BTreeSet::new()),
        Some(entry) => parse_version_keys(&entry.to_string()).map_err(|e| {
            format!(
                "--extra-known-versions file '{}' entry for '{system}' is corrupt: {e}",
                path.display()
            )
        }),
    }
}

/// The system keys an extras file names (startup validation: every key
/// must be a shipped system).
pub fn extra_versions_systems(path: &Path) -> Result<Vec<String>, String> {
    let text = std::fs::read_to_string(path).map_err(|e| {
        format!(
            "--extra-known-versions file '{}' unreadable: {e}",
            path.display()
        )
    })?;
    let value: serde_json::Value = serde_json::from_str(&text).map_err(|e| {
        format!(
            "--extra-known-versions file '{}' is corrupt: {e}",
            path.display()
        )
    })?;
    Ok(value
        .as_object()
        .map(|o| o.keys().cloned().collect())
        .unwrap_or_default())
}

/// Parse the `{"versions": {"<ver>": [ids...]}}` shape into its key set.
fn parse_version_keys(text: &str) -> Result<BTreeSet<String>, String> {
    let value: serde_json::Value = serde_json::from_str(text).map_err(|e| e.to_string())?;
    let versions = value
        .get("versions")
        .and_then(|v| v.as_object())
        .ok_or_else(|| "missing 'versions' object".to_string())?;
    Ok(versions.keys().cloned().collect())
}

/// Compute a character's version status. Read-only: replays the log in
/// memory, writes nothing.
pub fn status_for(engine: &dyn EngineOps, known: &KnownVersions, loaded: &Loaded) -> VersionStatus {
    if loaded.rules_version == known.current {
        return VersionStatus::Current;
    }
    // A recorded keep-old suppresses re-flagging until the shipped version
    // moves past what it was evaluated against. Drafts never carry a valid
    // keep-old (the route refuses them): a hand-edited one stays flagged.
    if loaded.state == DocState::Finalized {
        if let Some(keep) = &loaded.keep_old {
            if keep.evaluated_against == known.current && keep.pinned == loaded.rules_version {
                return VersionStatus::KeptOld {
                    pinned: loaded.rules_version.clone(),
                    evaluated_against: keep.evaluated_against.clone(),
                };
            }
        }
    }
    if !known.older_known.contains(&loaded.rules_version) {
        return VersionStatus::Unknown {
            pinned: loaded.rules_version.clone(),
            current: known.current.clone(),
        };
    }
    // Only the finalized prefix is judged: a pending tail is never part
    // of the stored sheet (the prefix invariant).
    let outcome = match engine.sheet(loaded.finalized_prefix()) {
        // Identical means the same values: a newer build may word a
        // breakdown differently (the detail text) without any number
        // moving, and that is not a divergence the DM must review.
        Ok(replayed) if sheet_diffs(&loaded.sheet, &replayed).is_empty() => {
            ReplayOutcome::Identical
        }
        Ok(replayed) => ReplayOutcome::Divergent {
            differences: sheet_diffs(&loaded.sheet, &replayed),
        },
        Err(e) => {
            let (failing_decision, slot) = failing_decision(&loaded.log, &e);
            let would_reopen = if loaded.state == DocState::Draft {
                repair_replay(engine, &loaded.log).cleared
            } else {
                Vec::new()
            };
            ReplayOutcome::ReplayError {
                message: e.to_string(),
                failing_decision,
                slot,
                would_reopen,
            }
        }
    };
    VersionStatus::OlderKnown {
        pinned: loaded.rules_version.clone(),
        current: known.current.clone(),
        outcome,
    }
}

/// Name the decision an engine replay error points at.
fn failing_decision(log: &[Decision], e: &EngineError) -> (types::DecisionId, types::SlotId) {
    match e {
        EngineError::UnknownSlot { index, slot }
        | EngineError::InvalidDecision { index, slot, .. } => (
            log.get(*index)
                .map(|d| d.id.clone())
                .unwrap_or_else(|| types::DecisionId::new("<unknown>")),
            slot.clone(),
        ),
        EngineError::NothingToClear { slot } => (types::DecisionId::new("<unknown>"), slot.clone()),
    }
}

/// Every sheet value that differs, old → new. Identity lines (name and
/// summary) are diffed alongside section entries; entries present on only
/// one side show "(absent)" on the other.
/// A multi-line explanation scoped to a change: the first line (the rule)
/// plus every later line absent from the old explanation. Single-line
/// explanations pass through untouched.
pub fn scope_explanation(new_detail: &str, old_detail: &str) -> String {
    let mut lines = new_detail.lines();
    let Some(rule) = lines.next() else {
        return String::new();
    };
    let rest: Vec<&str> = lines.collect();
    if rest.is_empty() {
        return new_detail.to_string();
    }
    let old_lines: Vec<&str> = old_detail.lines().collect();
    let mut out = vec![rule];
    out.extend(rest.into_iter().filter(|l| !old_lines.contains(l)));
    out.join("\n")
}

pub fn sheet_diffs(old: &SheetView, new: &SheetView) -> Vec<SheetDiff> {
    sheet_diffs_explained(old, new, old)
}

/// `sheet_diffs` with the explanations scoped against `baseline` rather
/// than `old`: values still compare the stored sheet to the new fold (what
/// the table saw against what it will see), but "which bullets are new" is
/// judged against a fresh fold under today's rules and wording — a stored
/// sheet written by an earlier build keeps its old detail text until the
/// character is re-derived, and must not make every bullet look new.
pub fn sheet_diffs_explained(
    old: &SheetView,
    new: &SheetView,
    baseline: &SheetView,
) -> Vec<SheetDiff> {
    const ABSENT: &str = "(absent)";
    let mut diffs = Vec::new();
    if old.name != new.name {
        diffs.push(SheetDiff {
            section: "Identity".into(),
            label: "Name".into(),
            old: old.name.clone(),
            new: new.name.clone(),
            why: None,
        });
    }
    if old.summary != new.summary {
        diffs.push(SheetDiff {
            section: "Identity".into(),
            label: "Summary".into(),
            old: old.summary.join(" · "),
            new: new.summary.join(" · "),
            why: None,
        });
    }
    // The explanation rides with the value: the new sheet entry's own
    // detail, so a diff reader sees why a number moved. A multi-line
    // detail is a rule line followed by bullet lines (the wire type's
    // shape convention); a diff keeps the rule and only the bullets that
    // are new against the old entry — what changed, not the whole history.
    let why_of = |section: &str, label: &str| -> Option<String> {
        let detail = new.entry(section, label).and_then(|e| e.detail.clone())?;
        let old_detail = baseline
            .entry(section, label)
            .and_then(|e| e.detail.clone())
            .unwrap_or_default();
        Some(scope_explanation(&detail, &old_detail))
    };
    for section in &old.sections {
        for entry in &section.entries {
            let new_value = new
                .entry(&section.title, &entry.label)
                .map(|e| e.value.as_str());
            if new_value != Some(entry.value.as_str()) {
                diffs.push(SheetDiff {
                    section: section.title.clone(),
                    label: entry.label.clone(),
                    old: entry.value.clone(),
                    new: new_value.unwrap_or(ABSENT).to_string(),
                    why: why_of(&section.title, &entry.label),
                });
            }
        }
    }
    for section in &new.sections {
        for entry in &section.entries {
            if old.entry(&section.title, &entry.label).is_none() {
                diffs.push(SheetDiff {
                    section: section.title.clone(),
                    label: entry.label.clone(),
                    old: ABSENT.to_string(),
                    new: entry.value.clone(),
                    why: why_of(&section.title, &entry.label),
                });
            }
        }
    }
    diffs
}

/// The surviving log and cleared decisions after repairing a log that no
/// longer replays: clear the failing decision's slot through the existing
/// cascade (transitive dependents included), refold, repeat until the log
/// folds. Terminates because every pass removes at least one decision.
pub struct ReplayRepair {
    pub log: Vec<Decision>,
    /// What was (or would be) cleared, in the order the repair found it —
    /// render-ready, mirroring the change-ancestry cascade prompt.
    pub cleared: Vec<ClearedDecision>,
    /// The decisions removed, verbatim (for the recorded event).
    pub cleared_decisions: Vec<Decision>,
}

pub fn repair_replay(engine: &dyn EngineOps, log: &[Decision]) -> ReplayRepair {
    let mut current: Vec<Decision> = log.to_vec();
    let mut cleared: Vec<ClearedDecision> = Vec::new();
    let mut cleared_decisions: Vec<Decision> = Vec::new();
    loop {
        let err = match engine.folds(&current) {
            Ok(()) => break,
            Err(e) => e,
        };
        let doomed: BTreeSet<types::SlotId> = match &err {
            EngineError::InvalidDecision { slot, .. } => {
                // The slot is registered (the fold found it): the engine's
                // own cascade preview names everything it takes with it.
                match engine.clear_preview(&current, slot) {
                    Ok(preview) => {
                        let slots = preview.cleared.iter().map(|c| c.slot.clone()).collect();
                        cleared.extend(preview.cleared);
                        slots
                    }
                    Err(_) => std::iter::once(slot.clone()).collect(),
                }
            }
            // An unregistered slot has no cascade graph: remove just its
            // decisions and describe them directly.
            EngineError::UnknownSlot { slot, .. } | EngineError::NothingToClear { slot } => {
                for d in current.iter().filter(|d| d.slot == *slot) {
                    cleared.push(ClearedDecision {
                        slot: d.slot.clone(),
                        slot_label: d.slot.to_string(),
                        selection_label: describe_selection(&d.selection),
                        selection: d.selection.clone(),
                    });
                }
                std::iter::once(slot.clone()).collect()
            }
        };
        cleared_decisions.extend(current.iter().filter(|d| doomed.contains(&d.slot)).cloned());
        let before = current.len();
        current = current
            .into_iter()
            .filter(|d| !doomed.contains(&d.slot))
            .enumerate()
            .map(|(i, mut d)| {
                d.order = i as u32;
                d
            })
            .collect();
        assert!(
            current.len() < before,
            "replay repair must remove at least one decision per pass"
        );
    }
    ReplayRepair {
        log: current,
        cleared,
        cleared_decisions,
    }
}

/// Fallback description for a decision on a slot current data no longer
/// registers (the registration's `describe` is unreachable).
fn describe_selection(selection: &Selection) -> String {
    match selection {
        Selection::Option(id) => id.to_string(),
        Selection::Options(ids) => ids
            .iter()
            .map(|i| i.to_string())
            .collect::<Vec<_>>()
            .join(", "),
        Selection::Text(text) => text.clone(),
        Selection::Rolled(sets) => format!("{} rolled set(s)", sets.len()),
    }
}

#[cfg(test)]
mod scope_tests {
    use super::scope_explanation;

    #[test]
    fn keeps_the_rule_and_only_the_new_bullets() {
        let old = "Rule.\n• Level 1: 10 + 0 = 10";
        let new = "Rule.\n• Level 1: 10 + 0 = 10\n• Level 2: fixed value 6 + 0 = 6";
        assert_eq!(
            scope_explanation(new, old),
            "Rule.\n• Level 2: fixed value 6 + 0 = 6"
        );
        // A rule that itself changed still leads; every bullet is then new.
        let changed = "Rule (+1).\n• Level 1: 10 + 1 = 11\n• Level 2: fixed value 6 + 1 = 7";
        assert_eq!(scope_explanation(changed, old), changed);
        // Single-line explanations pass through; an absent old one too.
        assert_eq!(
            scope_explanation("7 expert + 2 Con", "6 trained + 2 Con"),
            "7 expert + 2 Con"
        );
        assert_eq!(scope_explanation(new, ""), new);
    }
}
