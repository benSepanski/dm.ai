//! Ancestry kind: the ancestry slot, its heritage and level-1 ancestry
//! feat, and the ancestry free boost(s). Public surface: `registrations`.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{AncestryFeatRecord, Effect, RulesData};
use crate::mechanics::{
    attribute_options, describe_selection, illegal, incomplete, lang_option_id, prereq_description,
    prereq_unavailable, sel_attributes, sel_multi, sel_single, Pf2eState, SLOT_ANCESTRY,
    SLOT_ANCESTRY_FEAT, SLOT_ANCESTRY_FREE_BOOSTS, SLOT_ANCESTRY_LANGUAGES, SLOT_FEAT_GENERAL_FEAT,
    SLOT_FEAT_LORE, SLOT_FEAT_SKILLS, SLOT_HERITAGE, SLOT_HERITAGE_GENERAL_FEAT,
    SLOT_HERITAGE_SKILLS, SLOT_NATURAL_AMBITION, SLOT_REPLACEMENT_1, SLOT_REPLACEMENT_2,
    SLOT_REPLACEMENT_3,
};

const STEP: &str = crate::mechanics::STEP_ANCESTRY;

/// Empty-catalog choosers make the carrying option unpickable, uniformly.
fn chooser_unavailable(data: &RulesData, effects: &[Effect]) -> Option<String> {
    for e in effects {
        if let Effect::ChooseFromCatalog { catalog, .. } = e {
            let empty = match catalog.as_str() {
                "general_feats" => data.general_feats.is_empty(),
                "class_feats" => data.class_feats.is_empty(),
                _ => true, // arcane_cantrips, multiclass_dedications, uncommon_weapons…
            };
            if empty {
                return Some(format!(
                    "requires a choice from '{}', which has no entries in this rules-data version",
                    catalog.replace('_', " ")
                ));
            }
        }
    }
    None
}

/// Ancestry-feat catalog membership under the union rule: a feat is in
/// the catalog when its key names the chosen ancestry, or the chosen
/// heritage lists the key in feat_ancestries (versatile-heritage union).
fn feat_in_catalog(data: &RulesData, state: &Pf2eState, feat: &AncestryFeatRecord) -> bool {
    let Some(ancestry) = &state.ancestry else {
        return false;
    };
    if &feat.ancestry == ancestry {
        return true;
    }
    state
        .heritage
        .as_ref()
        .and_then(|id| data.heritage(id))
        .map(|h| h.feat_ancestries.contains(&feat.ancestry))
        .unwrap_or(false)
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();

    // --- Ancestry ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_ANCESTRY),
        step: StepId::new(STEP),
        label: "Ancestry".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![
            SlotId::new(SLOT_HERITAGE),
            SlotId::new(SLOT_ANCESTRY_FEAT),
            SlotId::new(SLOT_ANCESTRY_FREE_BOOSTS),
            SlotId::new(SLOT_ANCESTRY_LANGUAGES),
        ],
        options: Box::new(move |_| {
            d.ancestries
                .iter()
                .map(|a| OptionView {
                    id: OptionId::new(&a.id),
                    label: a.name.clone(),
                    summary: format!(
                        "HP {} · {} · Speed {} ft",
                        a.hp,
                        crate::mechanics::capitalize(&a.size),
                        a.speed
                    ),
                    details: {
                        let mut lines = Vec::new();
                        let boosts: Vec<&str> = a.boosts.iter().map(|b| b.name()).collect();
                        let mut boost_line = String::from("Boosts: ");
                        if !boosts.is_empty() {
                            boost_line.push_str(&boosts.join(", "));
                            boost_line.push_str(", ");
                        }
                        boost_line.push_str(&format!("{} free", a.free_boosts));
                        lines.push(boost_line);
                        if !a.flaws.is_empty() {
                            lines.push(format!(
                                "Flaw: {}",
                                a.flaws
                                    .iter()
                                    .map(|f| f.name())
                                    .collect::<Vec<_>>()
                                    .join(", ")
                            ));
                        }
                        if !a.senses.is_empty() {
                            lines.push(a.senses.join(", "));
                        }
                        lines.push(format!("Languages: {}", a.languages.join(", ")));
                        lines
                    },
                    available: true,
                    unavailable_reason: None,
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .ancestry(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown ancestry '{id}'")))?;
            state.ancestry = Some(record.id.clone());
            state
                .boost_batches
                .insert("ancestry".into(), record.boosts.clone());
            state.flaws = record.flaws.clone();
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.ancestry.is_none() {
                vec![incomplete(
                    SLOT_ANCESTRY,
                    STEP,
                    "Ancestry",
                    "Choose an ancestry",
                    "character creation",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Heritage ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_HERITAGE),
        step: StepId::new(STEP),
        label: "Heritage".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|state| match state.ancestry {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose an ancestry first".into(),
            },
        }),
        dependents: vec![
            SlotId::new(SLOT_HERITAGE_SKILLS),
            SlotId::new(SLOT_HERITAGE_GENERAL_FEAT),
            // The ancestry-feat catalog derives from the heritage too
            // (versatile-heritage union), so a heritage change clears it.
            SlotId::new(SLOT_ANCESTRY_FEAT),
            SlotId::new(SLOT_FEAT_LORE),
        ],
        options: Box::new(move |state| {
            let Some(ancestry) = &state.ancestry else {
                return vec![];
            };
            // The chosen ancestry's own heritages ∪ the versatile ones
            // (ancestry: null), selectable under any ancestry.
            d.heritages
                .iter()
                .filter(|h| h.ancestry.as_ref() == Some(ancestry) || h.is_versatile())
                .map(|h| {
                    let unavailable = chooser_unavailable(&d, &h.effects);
                    OptionView {
                        id: OptionId::new(&h.id),
                        label: h.name.clone(),
                        summary: h.text.clone(),
                        details: vec![],
                        available: unavailable.is_none(),
                        unavailable_reason: unavailable,
                    }
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .heritage(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown heritage '{id}'")))?;
            // A versatile heritage applies under any ancestry; a bound one
            // only under its own.
            if !record.is_versatile() && state.ancestry != record.ancestry {
                return Err(ApplyError::new(format!(
                    "heritage '{}' does not belong to the chosen ancestry",
                    record.name
                )));
            }
            if let Some(reason) = chooser_unavailable(&d_apply, &record.effects) {
                return Err(ApplyError::new(format!(
                    "'{}' is not available: {reason}",
                    record.name
                )));
            }
            state.heritage = Some(record.id.clone());
            // Fold grant effects exactly as feat apply does — a heritage's
            // skill/Lore grants (Battle-Ready Orc) train on the sheet and
            // feed the same collision/replacement machinery.
            for e in &record.effects {
                match e {
                    Effect::GrantSkills {
                        skills,
                        source_label,
                    } => {
                        for s in skills {
                            state.skill_grants.push(crate::mechanics::SkillGrant {
                                skill: s.clone(),
                                source: source_label.clone(),
                            });
                        }
                    }
                    Effect::GrantLore { name } => {
                        state.lores.push((name.clone(), record.name.clone()));
                    }
                    _ => {}
                }
                state.effects.push(e.clone());
            }
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.ancestry.is_some() && state.heritage.is_none() {
                vec![incomplete(
                    SLOT_HERITAGE,
                    STEP,
                    "Heritage",
                    "Choose a heritage",
                    "from Ancestry",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Ancestry feat ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_ANCESTRY_FEAT),
        step: StepId::new(STEP),
        label: "Ancestry feat".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|state| match state.ancestry {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose an ancestry first".into(),
            },
        }),
        dependents: vec![
            SlotId::new(SLOT_FEAT_SKILLS),
            SlotId::new(SLOT_FEAT_GENERAL_FEAT),
            SlotId::new(SLOT_NATURAL_AMBITION),
            SlotId::new(SLOT_FEAT_LORE),
            SlotId::new(SLOT_REPLACEMENT_1),
            SlotId::new(SLOT_REPLACEMENT_2),
            SlotId::new(SLOT_REPLACEMENT_3),
        ],
        options: Box::new(move |state| {
            if state.ancestry.is_none() {
                return vec![];
            };
            d.ancestry_feats
                .iter()
                .filter(|f| f.level == 1 && feat_in_catalog(&d, state, f))
                .map(|f| {
                    let unavailable = prereq_unavailable(&d, &f.prerequisites, state)
                        .or_else(|| chooser_unavailable(&d, &f.effects));
                    let mut details = vec![f.text.clone()];
                    for p in &f.prerequisites {
                        details.push(format!("Prerequisite: {}", prereq_description(&d, p)));
                    }
                    OptionView {
                        id: OptionId::new(&f.id),
                        label: f.name.clone(),
                        summary: String::new(),
                        details,
                        available: unavailable.is_none(),
                        unavailable_reason: unavailable,
                    }
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .ancestry_feat(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown ancestry feat '{id}'")))?;
            if !feat_in_catalog(&d_apply, state, record) {
                return Err(ApplyError::new(format!(
                    "feat '{}' is not in the feat catalog for the chosen \
                     ancestry and heritage",
                    record.name
                )));
            }
            if let Some(reason) = prereq_unavailable(&d_apply, &record.prerequisites, state)
                .or_else(|| chooser_unavailable(&d_apply, &record.effects))
            {
                return Err(ApplyError::new(format!(
                    "'{}' is not available: {reason}",
                    record.name
                )));
            }
            state.ancestry_feat = Some(record.id.clone());
            for e in &record.effects {
                match e {
                    Effect::GrantSkills {
                        skills,
                        source_label,
                    } => {
                        for s in skills {
                            state.skill_grants.push(crate::mechanics::SkillGrant {
                                skill: s.clone(),
                                source: source_label.clone(),
                            });
                        }
                    }
                    Effect::GrantLore { name } => {
                        state.lores.push((name.clone(), record.name.clone()));
                    }
                    _ => {}
                }
                state.effects.push(e.clone());
            }
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.ancestry.is_some() && state.ancestry_feat.is_none() {
                vec![incomplete(
                    SLOT_ANCESTRY_FEAT,
                    STEP,
                    "Ancestry feat",
                    "Choose a level-1 ancestry feat",
                    "from Ancestry",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Ancestry free boost(s) ---
    let d = data.clone();
    let d_desc = data.clone();
    let d_validate = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_ANCESTRY_FREE_BOOSTS),
        step: StepId::new(STEP),
        label: "Ancestry free boost".into(),
        required: true,
        presentation_hint: Some("attribute-boosts".into()),
        kind: Box::new(move |state| {
            let count = state
                .ancestry
                .as_ref()
                .and_then(|id| d.ancestry(id))
                .map(|a| a.free_boosts)
                .unwrap_or(1);
            SlotViewKind::Multi { count }
        }),
        unlock: Box::new(|state| match state.ancestry {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose an ancestry first".into(),
            },
        }),
        dependents: vec![],
        options: Box::new(|state| {
            let fixed = state
                .boost_batches
                .get("ancestry")
                .cloned()
                .unwrap_or_default();
            attribute_options(move |attr| {
                // Kept short: this renders inside <option> text. The full
                // rule lives in the checklist when it actually trips.
                if fixed.contains(&attr) {
                    Some("already has an ancestry boost".to_string())
                } else {
                    None
                }
            })
        }),
        apply: Box::new(|state, decision| {
            let attrs = sel_attributes(&decision.selection)?;
            state
                .boost_batches
                .entry("ancestry".into())
                .or_default()
                .extend(attrs);
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(ancestry_id) = &state.ancestry else {
                return vec![];
            };
            let expected = d_validate
                .ancestry(ancestry_id)
                .map(|a| a.free_boosts as usize)
                .unwrap_or(1);
            let record = d_validate.ancestry(ancestry_id);
            let fixed_count = record.map(|a| a.boosts.len()).unwrap_or(0);
            let batch = state
                .boost_batches
                .get("ancestry")
                .cloned()
                .unwrap_or_default();
            let picked = batch.len().saturating_sub(fixed_count);
            let mut out = Vec::new();
            if decision.is_none() || picked < expected {
                let left = expected - picked.min(expected);
                out.push(incomplete(
                    SLOT_ANCESTRY_FREE_BOOSTS,
                    STEP,
                    "Attribute boosts",
                    &format!("{} free ancestry boost(s) left", left.max(1)),
                    "from Ancestry",
                ));
            }
            let mut sorted = batch.clone();
            sorted.sort();
            let mut deduped = sorted.clone();
            deduped.dedup();
            if sorted.len() != deduped.len() {
                out.push(illegal(
                    SLOT_ANCESTRY_FREE_BOOSTS,
                    STEP,
                    "Attribute boosts",
                    "Boosts gained at the same time must go to different attributes",
                    "from Ancestry",
                ));
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Additional languages ---
    // Multi-select from the ancestry's additional_languages list; the count
    // is dynamic — max(0, Int modifier) + bonus-language effects — and
    // recomputed on every projection, like the trained-skills count. With
    // no list, or a count of zero and nothing picked, the slot is absent
    // (never blocks finalize); it stays visible while stale picks exist so
    // the over-pick flag can point at them.
    let d = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_ANCESTRY_LANGUAGES),
        step: StepId::new(STEP),
        label: "Additional languages".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(move |state| SlotViewKind::Multi {
            count: state.language_count(),
        }),
        unlock: Box::new(move |state| {
            let list_present = state
                .ancestry
                .as_ref()
                .and_then(|id| d.ancestry(id))
                .map(|a| !a.additional_languages.is_empty())
                .unwrap_or(false);
            if list_present && (state.language_count() > 0 || !state.chosen_languages.is_empty()) {
                Availability::Open
            } else {
                Availability::Hidden
            }
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(a) = state.ancestry.as_ref().and_then(|id| d_opts.ancestry(id)) else {
                return vec![];
            };
            a.additional_languages
                .iter()
                .map(|lang| OptionView {
                    id: OptionId::new(lang_option_id(lang)),
                    label: lang.clone(),
                    summary: String::new(),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            let Some(a) = state.ancestry.as_ref().and_then(|id| d_apply.ancestry(id)) else {
                return Err(ApplyError::new("choose an ancestry first"));
            };
            let mut chosen = Vec::new();
            for id in ids {
                let lang = a
                    .additional_languages
                    .iter()
                    .find(|lang| lang_option_id(lang) == id.as_str())
                    .ok_or_else(|| {
                        ApplyError::new(format!(
                            "'{id}' is not in this ancestry's additional languages"
                        ))
                    })?;
                chosen.push(lang.clone());
            }
            state.chosen_languages = chosen;
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let expected = state.language_count() as usize;
            let picked = state.chosen_languages.len();
            let mut out = Vec::new();
            if expected > 0 && (decision.is_none() || picked < expected) {
                out.push(incomplete(
                    SLOT_ANCESTRY_LANGUAGES,
                    STEP,
                    "Languages",
                    &format!(
                        "{} additional language choice(s) left",
                        expected - picked.min(expected)
                    ),
                    "from Ancestry",
                ));
            }
            if picked > expected {
                out.push(illegal(
                    SLOT_ANCESTRY_LANGUAGES,
                    STEP,
                    "Languages",
                    &format!(
                        "{picked} languages selected but only {expected} allowed \
                         (did Intelligence change?)"
                    ),
                    "from Ancestry",
                ));
            }
            let mut sorted = state.chosen_languages.clone();
            sorted.sort();
            let mut deduped = sorted.clone();
            deduped.dedup();
            if sorted.len() != deduped.len() {
                out.push(illegal(
                    SLOT_ANCESTRY_LANGUAGES,
                    STEP,
                    "Languages",
                    "Each additional language must be different",
                    "from Ancestry",
                ));
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}
