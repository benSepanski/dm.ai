//! Spells kind: the spellcasting build slots (arcane thesis, arcane school,
//! spellbook) and the scoped preparation slots. All of it is data + slot
//! definitions over the class record's printed spellcasting entry — the
//! engine stays game-word-free, and prep slots go through the engine's
//! scoped set, never the decision log.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{MeterState, MeterView, OptionId, OptionView, Selection, SlotId, SlotViewKind, StepId};

use crate::data::{RulesData, SpellRecord, SpellcastingDef};
use crate::mechanics::{
    describe_selection, illegal, incomplete, sel_multi, sel_single, Pf2eState, SLOT_PREP_CANTRIPS,
    SLOT_PREP_RANK1, SLOT_PREP_SCHOOL, SLOT_PREP_SCHOOL_CANTRIP, SLOT_SCHOOL,
    SLOT_SPELLBOOK_CANTRIPS, SLOT_SPELLBOOK_CURRICULUM, SLOT_SPELLBOOK_RANK1, SLOT_THESIS,
    STEP_CLASS,
};

const STEP: &str = STEP_CLASS;

/// The chosen class's spellcasting entry, when it has one.
fn caster<'a>(state: &Pf2eState, data: &'a RulesData) -> Option<&'a SpellcastingDef> {
    state
        .class
        .as_ref()
        .and_then(|id| data.class(id))
        .and_then(|c| c.spellcasting.as_ref())
}

/// Hidden for non-casters (a Fighter never sees spell slots), open for
/// casters.
fn caster_unlock(state: &Pf2eState, data: &RulesData) -> Availability {
    match caster(state, data) {
        Some(_) => Availability::Open,
        None => Availability::Hidden,
    }
}

fn spell_option(s: &SpellRecord) -> OptionView {
    let mut details = vec![format!("Actions: {}", s.actions)];
    if let Some(d) = &s.defense {
        details.push(format!("Defense: {d}"));
    }
    if let Some(r) = &s.range {
        details.push(format!("Range: {r}"));
    }
    if let Some(t) = &s.targets {
        details.push(format!("Targets: {t}"));
    }
    if let Some(d) = &s.duration {
        details.push(format!("Duration: {d}"));
    }
    details.push(format!("Traits: {}", s.traits.join(", ")));
    OptionView {
        id: OptionId::new(&s.id),
        label: s.name.clone(),
        summary: s.text.clone(),
        details,
        available: true,
        unavailable_reason: None,
    }
}

/// Arcane spells of one rank, spellbook-eligible (never focus spells).
fn arcane_by_rank(data: &RulesData, rank: u32) -> Vec<OptionView> {
    data.spells
        .spells
        .iter()
        .filter(|s| s.rank == rank && !s.focus && s.traditions.iter().any(|t| t == "arcane"))
        .map(spell_option)
        .collect()
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();

    // --- Arcane thesis ---
    let d = data.clone();
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_THESIS),
        step: StepId::new(STEP),
        label: "Arcane thesis".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| caster_unlock(state, &d_unlock)),
        dependents: vec![],
        options: Box::new(move |_| {
            d.spells
                .theses
                .iter()
                .map(|t| OptionView {
                    id: OptionId::new(&t.id),
                    label: t.name.clone(),
                    summary: t.text.clone(),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .thesis(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown arcane thesis '{id}'")))?;
            state.thesis = Some(record.id.clone());
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            if caster(state, &d_val).is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_THESIS,
                    STEP,
                    "Arcane thesis",
                    "Choose your arcane thesis",
                    "from Class",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Arcane school ---
    let d = data.clone();
    let d_unlock = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_SCHOOL),
        step: StepId::new(STEP),
        label: "Arcane school".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(move |state| caster_unlock(state, &d_unlock)),
        // Everything curriculum-derived dies with the school: the two
        // spellbook curriculum additions and both school preparations (the
        // cascade the spec's "changed mind" story walks).
        dependents: vec![
            SlotId::new(SLOT_SPELLBOOK_CURRICULUM),
            SlotId::new(SLOT_PREP_SCHOOL_CANTRIP),
            SlotId::new(SLOT_PREP_SCHOOL),
        ],
        options: Box::new(move |_| {
            d.spells
                .schools
                .iter()
                .map(|s| {
                    let focus = d
                        .spell(&s.focus_spell)
                        .map(|f| f.name.clone())
                        .unwrap_or_default();
                    OptionView {
                        id: OptionId::new(&s.id),
                        label: s.name.clone(),
                        summary: s.text.clone(),
                        details: vec![
                            format!("Focus spell: {focus}"),
                            format!(
                                "Curriculum (rank 1): {}",
                                s.curriculum_rank1
                                    .iter()
                                    .map(|id| d
                                        .spell(id)
                                        .map(|r| r.name.clone())
                                        .unwrap_or_else(|| id.clone()))
                                    .collect::<Vec<_>>()
                                    .join(", ")
                            ),
                        ],
                        available: true,
                        unavailable_reason: None,
                    }
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .school(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown arcane school '{id}'")))?;
            state.school = Some(record.id.clone());
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            if caster(state, &d_val).is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_SCHOOL,
                    STEP,
                    "Arcane school",
                    "Choose your arcane school",
                    "from Class",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Spellbook ---
    for (slot, label, rank, state_get) in [
        (
            SLOT_SPELLBOOK_CANTRIPS,
            "Spellbook: cantrips",
            0u32,
            (|s: &Pf2eState| s.spellbook_cantrips.clone()) as fn(&Pf2eState) -> Vec<String>,
        ),
        (
            SLOT_SPELLBOOK_RANK1,
            "Spellbook: rank-1 spells",
            1u32,
            |s| s.spellbook_rank1.clone(),
        ),
    ] {
        let d = data.clone();
        let d_kind = data.clone();
        let d_unlock = data.clone();
        let d_apply = data.clone();
        let d_val = data.clone();
        let d_desc = data.clone();
        let book_count = move |sc: &SpellcastingDef| {
            if rank == 0 {
                sc.spellbook_cantrips
            } else {
                sc.spellbook_rank1
            }
        };
        regs.push(SlotRegistration::<Pf2eState> {
            id: SlotId::new(slot),
            step: StepId::new(STEP),
            label: label.into(),
            required: true,
            presentation_hint: Some("spell-list".into()),
            kind: Box::new(move |state| SlotViewKind::Multi {
                count: caster(state, &d_kind).map(book_count).unwrap_or(0),
            }),
            unlock: Box::new(move |state| caster_unlock(state, &d_unlock)),
            // Preparation comes from the book: a changed book clears the
            // dependent prepared picks. (The school preparations derive
            // from the curriculum, not the book, so they survive.)
            dependents: if rank == 0 {
                vec![SlotId::new(SLOT_PREP_CANTRIPS)]
            } else {
                vec![SlotId::new(SLOT_PREP_RANK1)]
            },
            options: Box::new(move |_| arcane_by_rank(&d, rank)),
            apply: Box::new(move |state, decision| {
                let ids = sel_multi(&decision.selection)?;
                let mut picked = Vec::new();
                for id in ids {
                    let record = d_apply
                        .spell(id.as_str())
                        .ok_or_else(|| ApplyError::new(format!("unknown spell '{id}'")))?;
                    if record.rank != rank
                        || record.focus
                        || !record.traditions.iter().any(|t| t == "arcane")
                    {
                        return Err(ApplyError::new(format!(
                            "'{}' is not an arcane rank-{rank} spell",
                            record.name
                        )));
                    }
                    picked.push(record.id.clone());
                }
                if rank == 0 {
                    state.spellbook_cantrips = picked;
                } else {
                    state.spellbook_rank1 = picked;
                }
                Ok(())
            }),
            validate: Box::new(move |state, decision| {
                let Some(sc) = caster(state, &d_val) else {
                    return vec![];
                };
                let count = book_count(sc) as usize;
                let picked = state_get(state);
                let mut out = vec![];
                if decision.is_none() || picked.len() < count {
                    out.push(incomplete(
                        slot,
                        STEP,
                        "Spellbook",
                        &format!(
                            "{} spell(s) left to inscribe",
                            count.saturating_sub(picked.len()).max(1)
                        ),
                        "from Class: spellbook",
                    ));
                }
                if picked.len() > count {
                    out.push(illegal(
                        slot,
                        STEP,
                        "Spellbook",
                        &format!("the spellbook holds {count} at this rank — remove some"),
                        "from Class: spellbook",
                    ));
                }
                let mut seen = std::collections::BTreeSet::new();
                if picked.iter().any(|p| !seen.insert(p.clone())) {
                    out.push(illegal(
                        slot,
                        STEP,
                        "Spellbook",
                        "each spell appears in the book once",
                        "from Class: spellbook",
                    ));
                }
                out
            }),
            meters: Box::new(|_, _| vec![]),
            describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
        });
    }

    // --- Spellbook: the school's curriculum additions ---
    // The printed rule: "You also add two 1st-rank spells from the
    // curriculum of your arcane school."
    let d_kind = data.clone();
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_SPELLBOOK_CURRICULUM),
        step: StepId::new(STEP),
        label: "Spellbook: curriculum spells".into(),
        required: true,
        presentation_hint: Some("spell-list".into()),
        kind: Box::new(move |state| SlotViewKind::Multi {
            count: caster(state, &d_kind)
                .map(|sc| sc.spellbook_curriculum_rank1)
                .unwrap_or(0),
        }),
        unlock: Box::new(move |state| match caster(state, &d_unlock) {
            None => Availability::Hidden,
            Some(_) if state.school.is_none() => Availability::Locked {
                reason: "choose your arcane school first".into(),
            },
            Some(_) => Availability::Open,
        }),
        dependents: vec![SlotId::new(SLOT_PREP_RANK1)],
        options: Box::new(move |state| {
            let Some(school) = state.school.as_ref().and_then(|id| d_opts.school(id)) else {
                return vec![];
            };
            school
                .curriculum_rank1
                .iter()
                .filter_map(|id| d_opts.spell(id))
                .map(|s| {
                    let mut view = spell_option(s);
                    if state.spellbook_rank1.contains(&s.id) {
                        view.available = false;
                        view.unavailable_reason = Some("already in your spellbook".to_string());
                    }
                    view
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            let Some(school) = state.school.as_ref().and_then(|s| d_apply.school(s)) else {
                return Err(ApplyError::new("no arcane school chosen"));
            };
            let mut picked = Vec::new();
            for id in ids {
                let record = d_apply
                    .spell(id.as_str())
                    .ok_or_else(|| ApplyError::new(format!("unknown spell '{id}'")))?;
                if !school.curriculum_rank1.contains(&record.id) {
                    return Err(ApplyError::new(format!(
                        "'{}' is not in the {} curriculum",
                        record.name, school.name
                    )));
                }
                picked.push(record.id.clone());
            }
            state.spellbook_curriculum = picked;
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(sc) = caster(state, &d_val) else {
                return vec![];
            };
            if state.school.is_none() {
                return vec![];
            }
            let count = sc.spellbook_curriculum_rank1 as usize;
            let picked = &state.spellbook_curriculum;
            let mut out = vec![];
            if decision.is_none() || picked.len() < count {
                out.push(incomplete(
                    SLOT_SPELLBOOK_CURRICULUM,
                    STEP,
                    "Spellbook",
                    &format!(
                        "{} curriculum spell(s) left to add",
                        count.saturating_sub(picked.len()).max(1)
                    ),
                    "from Arcane school",
                ));
            }
            if picked.len() > count {
                out.push(illegal(
                    SLOT_SPELLBOOK_CURRICULUM,
                    STEP,
                    "Spellbook",
                    &format!("the school adds {count} — remove some"),
                    "from Arcane school",
                ));
            }
            let mut seen = std::collections::BTreeSet::new();
            if picked.iter().any(|p| !seen.insert(p.clone()))
                || picked.iter().any(|p| state.spellbook_rank1.contains(p))
            {
                out.push(illegal(
                    SLOT_SPELLBOOK_CURRICULUM,
                    STEP,
                    "Spellbook",
                    "each spell appears in the book once",
                    "from Arcane school",
                ));
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}

/// The scoped preparation slots. Same registration contract as wizard
/// slots; the engine validates them against the folded build state and the
/// choice set is replaceable wholesale (never log entries). Apply performs
/// membership checks only and writes nothing into the fold — the
/// materialized sheet stays a pure function of the log.
pub fn scoped_registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();

    // Cantrips and rank-1 slots: prepare from the book, repeats allowed
    // (the printed rule: the same spell may fill several slots).
    for (slot, label, rank) in [
        (SLOT_PREP_CANTRIPS, "Prepared cantrips", 0u32),
        (SLOT_PREP_RANK1, "Prepared rank-1 spells", 1u32),
    ] {
        let d_unlock = data.clone();
        let d_opts = data.clone();
        let d_apply = data.clone();
        let d_val = data.clone();
        let d_desc = data.clone();
        let d_meter = data.clone();
        let slot_count = move |sc: &SpellcastingDef| {
            if rank == 0 {
                sc.cantrips_prepared
            } else {
                sc.rank1_slots
            }
        };
        let book = move |state: &Pf2eState| -> Vec<String> {
            if rank == 0 {
                state.spellbook_cantrips.clone()
            } else {
                // The rank-1 book is the free picks plus the school's
                // curriculum additions.
                let mut all = state.spellbook_rank1.clone();
                all.extend(state.spellbook_curriculum.iter().cloned());
                all
            }
        };
        regs.push(SlotRegistration::<Pf2eState> {
            id: SlotId::new(slot),
            step: StepId::new(STEP),
            label: label.into(),
            required: true,
            presentation_hint: Some("spell-prep".into()),
            // List, not Multi: preparing the same spell in two slots is
            // legal; the count rule lives in validate + the meter.
            kind: Box::new(|_| SlotViewKind::List),
            unlock: Box::new(move |state| match caster(state, &d_unlock) {
                None => Availability::Hidden,
                Some(_) if book(state).is_empty() => Availability::Locked {
                    reason: "inscribe your spellbook first".into(),
                },
                Some(_) => Availability::Open,
            }),
            dependents: vec![],
            options: Box::new(move |state| {
                book(state)
                    .iter()
                    .filter_map(|id| d_opts.spell(id))
                    .map(spell_option)
                    .collect()
            }),
            apply: Box::new(move |state, decision| {
                let ids = sel_multi(&decision.selection)?;
                let book = book(state);
                for id in ids {
                    let record = d_apply
                        .spell(id.as_str())
                        .ok_or_else(|| ApplyError::new(format!("unknown spell '{id}'")))?;
                    if !book.contains(&record.id) {
                        return Err(ApplyError::new(format!(
                            "'{}' is not in your spellbook",
                            record.name
                        )));
                    }
                }
                Ok(())
            }),
            validate: Box::new(move |state, decision| {
                let Some(sc) = caster(state, &d_val) else {
                    return vec![];
                };
                let count = slot_count(sc) as usize;
                let picked = decision
                    .map(|d| match &d.selection {
                        Selection::Options(ids) => ids.len(),
                        Selection::Option(_) => 1,
                        Selection::Text(_) => 0,
                    })
                    .unwrap_or(0);
                let mut out = vec![];
                if picked < count {
                    out.push(incomplete(
                        slot,
                        STEP,
                        "Preparation",
                        &format!("{} spell(s) left to prepare", count - picked),
                        "daily preparation",
                    ));
                }
                if picked > count {
                    out.push(illegal(
                        slot,
                        STEP,
                        "Preparation",
                        &format!("only {count} can be prepared here — remove some"),
                        "daily preparation",
                    ));
                }
                out
            }),
            meters: Box::new(move |state, decision| {
                let Some(sc) = caster(state, &d_meter) else {
                    return vec![];
                };
                let count = slot_count(sc) as usize;
                let picked = decision
                    .map(|d| match &d.selection {
                        Selection::Options(ids) => ids.len(),
                        Selection::Option(_) => 1,
                        Selection::Text(_) => 0,
                    })
                    .unwrap_or(0);
                vec![MeterView {
                    label: "Prepared".into(),
                    current: picked.to_string(),
                    limit: Some(count.to_string()),
                    state: match picked.cmp(&count) {
                        std::cmp::Ordering::Less => MeterState::Short,
                        std::cmp::Ordering::Equal => MeterState::Ok,
                        std::cmp::Ordering::Greater => MeterState::Exceeded,
                    },
                }]
            }),
            describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
        });
    }

    // The school's extra preparations: one curriculum cantrip and one
    // curriculum rank-1 spell, prepared directly from the curriculum (the
    // printed "as well as … from your arcane school" — no spellbook
    // membership required).
    for (slot, label, rank) in [
        (SLOT_PREP_SCHOOL_CANTRIP, "School cantrip", 0u32),
        (SLOT_PREP_SCHOOL, "School slot (rank 1)", 1u32),
    ] {
        let d_unlock = data.clone();
        let d_opts = data.clone();
        let d_apply = data.clone();
        let d_val = data.clone();
        let d_desc = data.clone();
        let curriculum = move |school: &crate::data::SchoolRecord| -> Vec<String> {
            if rank == 0 {
                school.curriculum_cantrips.clone()
            } else {
                school.curriculum_rank1.clone()
            }
        };
        regs.push(SlotRegistration::<Pf2eState> {
            id: SlotId::new(slot),
            step: StepId::new(STEP),
            label: label.into(),
            required: true,
            presentation_hint: Some("spell-prep".into()),
            kind: Box::new(|_| SlotViewKind::Single),
            unlock: Box::new(move |state| {
                let Some(sc) = caster(state, &d_unlock) else {
                    return Availability::Hidden;
                };
                if !sc.school_extra_slot {
                    return Availability::Hidden;
                }
                match &state.school {
                    None => Availability::Locked {
                        reason: "choose your arcane school first".into(),
                    },
                    Some(_) => Availability::Open,
                }
            }),
            dependents: vec![],
            options: Box::new(move |state| {
                let Some(school) = state.school.as_ref().and_then(|id| d_opts.school(id)) else {
                    return vec![];
                };
                curriculum(school)
                    .iter()
                    .filter_map(|id| d_opts.spell(id))
                    .map(spell_option)
                    .collect()
            }),
            apply: Box::new(move |state, decision| {
                let id = sel_single(&decision.selection)?;
                let record = d_apply
                    .spell(id.as_str())
                    .ok_or_else(|| ApplyError::new(format!("unknown spell '{id}'")))?;
                let Some(school) = state.school.as_ref().and_then(|s| d_apply.school(s)) else {
                    return Err(ApplyError::new("no arcane school chosen"));
                };
                if !curriculum(school).contains(&record.id) {
                    return Err(ApplyError::new(format!(
                        "'{}' is not in the {} curriculum — school preparations \
                         take curriculum spells only",
                        record.name, school.name
                    )));
                }
                Ok(())
            }),
            validate: Box::new(move |state, decision| {
                let has_school = caster(state, &d_val).is_some() && state.school.is_some();
                if has_school && decision.is_none() {
                    vec![incomplete(
                        slot,
                        STEP,
                        "Preparation",
                        &format!(
                            "Prepare a curriculum {} in your school slot",
                            if rank == 0 { "cantrip" } else { "spell" }
                        ),
                        "daily preparation",
                    )]
                } else {
                    vec![]
                }
            }),
            meters: Box::new(|_, _| vec![]),
            describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
        });
    }

    regs
}
