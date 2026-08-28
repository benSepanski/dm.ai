//! Ancestry kind: the ancestry slot, its heritage and level-1 ancestry
//! feat, and the ancestry free boost(s). Public surface: `registrations`.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{Effect, RulesData};
use crate::mechanics::{
    attribute_options, describe_selection, illegal, incomplete, sel_attributes, sel_single,
    Pf2eState, SLOT_ANCESTRY, SLOT_ANCESTRY_FEAT, SLOT_ANCESTRY_FREE_BOOSTS,
    SLOT_FEAT_GENERAL_FEAT, SLOT_FEAT_SKILLS, SLOT_HERITAGE, SLOT_HERITAGE_GENERAL_FEAT,
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

/// Prerequisites: evaluable kinds gate availability; the rest annotate.
fn prereq_unavailable(prereqs: &[crate::data::Prerequisite], state: &Pf2eState) -> Option<String> {
    let _ = state;
    for p in prereqs {
        if p.kind == "spellcasting" {
            // No class in this data version has a spellcasting feature.
            return Some(p.text.clone());
        }
    }
    None
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
        ],
        options: Box::new(move |state| {
            let Some(ancestry) = &state.ancestry else {
                return vec![];
            };
            d.heritages
                .iter()
                .filter(|h| &h.ancestry == ancestry)
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
            if state.ancestry.as_deref() != Some(record.ancestry.as_str()) {
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
            state.effects.extend(record.effects.iter().cloned());
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
            SlotId::new(SLOT_REPLACEMENT_1),
            SlotId::new(SLOT_REPLACEMENT_2),
            SlotId::new(SLOT_REPLACEMENT_3),
        ],
        options: Box::new(move |state| {
            let Some(ancestry) = &state.ancestry else {
                return vec![];
            };
            d.ancestry_feats
                .iter()
                .filter(|f| &f.ancestry == ancestry && f.level == 1)
                .map(|f| {
                    let unavailable = prereq_unavailable(&f.prerequisites, state)
                        .or_else(|| chooser_unavailable(&d, &f.effects));
                    let mut details = vec![f.text.clone()];
                    for p in &f.prerequisites {
                        details.push(format!("Prerequisite: {}", p.text));
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
            if state.ancestry.as_deref() != Some(record.ancestry.as_str()) {
                return Err(ApplyError::new(format!(
                    "feat '{}' does not belong to the chosen ancestry",
                    record.name
                )));
            }
            if let Some(reason) = prereq_unavailable(&record.prerequisites, state)
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
                if fixed.contains(&attr) {
                    Some(format!(
                        "{} already has an ancestry boost — boosts gained at the same time must go to different attributes",
                        attr.name()
                    ))
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

    regs
}
