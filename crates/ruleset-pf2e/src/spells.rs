//! Spells kind: the spellcasting build slots — arcane thesis, arcane
//! school, and the spellbook as one picker per rank. All of it is data +
//! slot definitions over the class record's printed spellcasting entry;
//! the engine stays game-word-free.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{MeterView, OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::{RulesData, SpellRecord, SpellcastingDef};
use crate::mechanics::{
    describe_selection, illegal, incomplete, sel_multi, sel_single, Pf2eState, SLOT_SCHOOL,
    SLOT_SPELLBOOK_CANTRIPS, SLOT_SPELLBOOK_RANK1, SLOT_THESIS, STEP_CLASS,
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

fn spell_option(s: &SpellRecord, curriculum_of: Option<&str>) -> OptionView {
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
    // Curriculum membership rides as structured group + badge: the group
    // header labels the curriculum block, and the badge chip stays on the
    // row through filtering, so the player never cross-references a
    // second card.
    OptionView {
        id: OptionId::new(&s.id),
        label: s.name.clone(),
        summary: s.text.clone(),
        details,
        available: true,
        unavailable_reason: None,
        group: None,
        badge: curriculum_of.map(|_| "Curriculum".to_string()),
    }
}

/// The rank-1 spellbook catalog: every arcane rank-1 spell, curriculum
/// spells first (marked in place) when a school is chosen.
fn rank1_options(data: &RulesData, state: &Pf2eState) -> Vec<OptionView> {
    let school = state.school.as_ref().and_then(|id| data.school(id));
    let in_curriculum = |s: &SpellRecord| {
        school
            .map(|sc| sc.curriculum_rank1.contains(&s.id))
            .unwrap_or(false)
    };
    let mut spells: Vec<&SpellRecord> = data
        .spells
        .spells
        .iter()
        .filter(|s| s.rank == 1 && !s.focus && s.traditions.iter().any(|t| t == "arcane"))
        .collect();
    spells.sort_by_key(|s| (!in_curriculum(s), s.name.clone()));
    spells
        .into_iter()
        .map(|s| {
            let mut option = spell_option(
                s,
                if in_curriculum(s) {
                    school.map(|sc| sc.name.as_str())
                } else {
                    None
                },
            );
            // With a school chosen the list splits under two headers; with
            // none there is a single unlabeled group (no header renders).
            if let Some(sc) = school {
                option.group = Some(if in_curriculum(s) {
                    format!("{} curriculum", sc.name)
                } else {
                    "Other arcane spells".to_string()
                });
            }
            option
        })
        .collect()
}

/// The rank-1 spellbook size: the free picks, plus the school's curriculum
/// additions once a school is chosen.
fn rank1_count(state: &Pf2eState, data: &RulesData) -> u32 {
    caster(state, data)
        .map(|sc| {
            sc.spellbook_rank1
                + if state.school.is_some() {
                    sc.spellbook_curriculum_rank1
                } else {
                    0
                }
        })
        .unwrap_or(0)
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();
    regs.extend(growth_registrations(data));

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
                    group: None,
                    badge: None,
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
    // Deliberately no dependents: changing the school destroys nothing.
    // The spellbook's curriculum constraint re-judges the existing picks
    // against the new school, and the focus spell is derived.
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
        dependents: vec![],
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
                        group: None,
                        badge: None,
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

    // --- Spellbook: cantrips (one picker) ---
    let d_kind = data.clone();
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_SPELLBOOK_CANTRIPS),
        step: StepId::new(STEP),
        label: "Spellbook: cantrips".into(),
        required: true,
        presentation_hint: Some("spell-list".into()),
        kind: Box::new(move |state| SlotViewKind::Multi {
            count: caster(state, &d_kind)
                .map(|sc| sc.spellbook_cantrips)
                .unwrap_or(0),
        }),
        unlock: Box::new(move |state| caster_unlock(state, &d_unlock)),
        dependents: vec![],
        options: Box::new(move |_| {
            d_opts
                .spells
                .spells
                .iter()
                .filter(|s| s.rank == 0 && !s.focus && s.traditions.iter().any(|t| t == "arcane"))
                .map(|s| spell_option(s, None))
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            let mut picked = Vec::new();
            for id in ids {
                let record = d_apply
                    .spell(id.as_str())
                    .ok_or_else(|| ApplyError::new(format!("unknown spell '{id}'")))?;
                if record.rank != 0
                    || record.focus
                    || !record.traditions.iter().any(|t| t == "arcane")
                {
                    return Err(ApplyError::new(format!(
                        "'{}' is not an arcane cantrip",
                        record.name
                    )));
                }
                picked.push(record.id.clone());
            }
            state.spellbook_cantrips = picked;
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(sc) = caster(state, &d_val) else {
                return vec![];
            };
            book_count_entries(
                SLOT_SPELLBOOK_CANTRIPS,
                "cantrip",
                sc.spellbook_cantrips as usize,
                &state.spellbook_cantrips,
                decision.is_some(),
            )
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Spellbook: rank-1 spells (one picker; curriculum inside it) ---
    let d_kind = data.clone();
    let d_unlock = data.clone();
    let d_opts = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    let d_meter = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_SPELLBOOK_RANK1),
        step: StepId::new(STEP),
        label: "Spellbook: rank-1 spells".into(),
        required: true,
        presentation_hint: Some("spell-list".into()),
        kind: Box::new(move |state| SlotViewKind::Multi {
            count: rank1_count(state, &d_kind),
        }),
        unlock: Box::new(move |state| caster_unlock(state, &d_unlock)),
        dependents: vec![],
        options: Box::new(move |state| rank1_options(&d_opts, state)),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            let mut picked = Vec::new();
            for id in ids {
                let record = d_apply
                    .spell(id.as_str())
                    .ok_or_else(|| ApplyError::new(format!("unknown spell '{id}'")))?;
                if record.rank != 1
                    || record.focus
                    || !record.traditions.iter().any(|t| t == "arcane")
                {
                    return Err(ApplyError::new(format!(
                        "'{}' is not an arcane rank-1 spell",
                        record.name
                    )));
                }
                picked.push(record.id.clone());
            }
            state.spellbook_rank1 = picked;
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(sc) = caster(state, &d_val) else {
                return vec![];
            };
            let count = rank1_count(state, &d_val) as usize;
            let mut out = book_count_entries(
                SLOT_SPELLBOOK_RANK1,
                "rank-1 spell",
                count,
                &state.spellbook_rank1,
                decision.is_some(),
            );
            // The curriculum minimum, judged in place: the printed rule adds
            // curriculum spells to the book, so a full book must include at
            // least that many.
            if let Some(school) = state.school.as_ref().and_then(|id| d_val.school(id)) {
                let have = state
                    .spellbook_rank1
                    .iter()
                    .filter(|id| school.curriculum_rank1.contains(id))
                    .count();
                let need = sc.spellbook_curriculum_rank1 as usize;
                if have < need && state.spellbook_rank1.len() >= count {
                    out.push(illegal(
                        SLOT_SPELLBOOK_RANK1,
                        STEP,
                        "Curriculum",
                        &format!(
                            "at least {need} of these must come from the {} curriculum \
                             — swap {} in",
                            school.name,
                            need - have
                        ),
                        "from Arcane school",
                    ));
                }
            }
            out
        }),
        meters: Box::new(move |state, _| {
            let Some(sc) = caster(state, &d_meter) else {
                return vec![];
            };
            let Some(school) = state.school.as_ref().and_then(|id| d_meter.school(id)) else {
                return vec![];
            };
            let have = state
                .spellbook_rank1
                .iter()
                .filter(|id| school.curriculum_rank1.contains(id))
                .count();
            let need = sc.spellbook_curriculum_rank1 as usize;
            vec![MeterView::requirement("Curriculum", have, need)]
        }),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}

/// Shared count/distinctness entries for a spellbook picker.
fn book_count_entries(
    slot: &str,
    noun: &str,
    count: usize,
    picked: &[String],
    has_decision: bool,
) -> Vec<types::ChecklistEntry> {
    let mut out = vec![];
    if !has_decision || picked.len() < count {
        out.push(incomplete(
            slot,
            STEP,
            "Spellbook",
            &format!(
                "{} {noun}(s) left to inscribe",
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
}

// ---- Spellbook growth at level-up ----
//
// The printed rule: each level, a wizard adds two spells of any rank they
// can cast to the spellbook. One slot per level, mixed-rank options
// grouped by rank — never a grown count on the level-1 picker (that would
// amend a finalized decision), never two cards to reconcile.

/// Every arcane spell the book does not yet hold, at ranks 1..=max
/// castable at the level, grouped by rank.
fn growth_options(data: &RulesData, state: &Pf2eState, level: u32) -> Vec<OptionView> {
    let Some(sc) = caster(state, data) else {
        return vec![];
    };
    let max_rank = sc.max_rank_at(level).max(1);
    let in_book = |id: &str| {
        state.spellbook_rank1.iter().any(|s| s == id)
            || state.spellbook_added.iter().any(|(_, s)| s == id)
    };
    let mut spells: Vec<&SpellRecord> = data
        .spells
        .spells
        .iter()
        .filter(|s| {
            s.rank >= 1
                && s.rank <= max_rank
                && !s.focus
                && s.traditions.iter().any(|t| t == "arcane")
        })
        .collect();
    spells.sort_by_key(|s| (s.rank, s.name.clone()));
    spells
        .into_iter()
        .map(|s| {
            let mut option = spell_option(s, None);
            option.group = Some(format!("Rank {} spells", s.rank));
            if in_book(&s.id) {
                option.available = false;
                option.unavailable_reason = Some("already in the spellbook".to_string());
            }
            option
        })
        .collect()
}

fn growth_registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    use crate::mechanics::{slot_level_spellbook, step_level};
    let mut regs = Vec::new();
    for level in 2..=data.max_advancement_level() {
        let slot = slot_level_spellbook(level);
        let step = step_level(level);
        let (d_kind, d_unlock, d_opts, d_apply, d_val, d_desc) = (
            data.clone(),
            data.clone(),
            data.clone(),
            data.clone(),
            data.clone(),
            data.clone(),
        );
        let (slot_v, step_v) = (slot.clone(), step.clone());
        regs.push(SlotRegistration::<Pf2eState> {
            id: SlotId::new(&slot),
            step: StepId::new(&step),
            label: format!("Spellbook: new spells (level {level})"),
            required: true,
            presentation_hint: Some("spell-list".into()),
            kind: Box::new(move |state| SlotViewKind::Multi {
                count: caster(state, &d_kind)
                    .map(|sc| sc.spells_per_level)
                    .unwrap_or(0),
            }),
            unlock: Box::new(move |state| {
                if state.level() as u32 >= level {
                    caster_unlock(state, &d_unlock)
                } else {
                    Availability::Hidden
                }
            }),
            dependents: vec![],
            options: Box::new(move |state| growth_options(&d_opts, state, level)),
            apply: Box::new(move |state, decision| {
                let ids = sel_multi(&decision.selection)?;
                let Some(sc) = caster(state, &d_apply) else {
                    return Err(ApplyError::new("this class has no spellbook"));
                };
                let max_rank = sc.max_rank_at(level).max(1);
                let mut picked = Vec::new();
                for id in ids {
                    let record = d_apply
                        .spell(id.as_str())
                        .ok_or_else(|| ApplyError::new(format!("unknown spell '{id}'")))?;
                    if record.rank < 1
                        || record.rank > max_rank
                        || record.focus
                        || !record.traditions.iter().any(|t| t == "arcane")
                    {
                        return Err(ApplyError::new(format!(
                            "'{}' is not an arcane spell of a rank castable at level {level}",
                            record.name
                        )));
                    }
                    if state.spellbook_rank1.contains(&record.id)
                        || state.spellbook_added.iter().any(|(_, s)| *s == record.id)
                    {
                        return Err(ApplyError::new(format!(
                            "'{}' is already in the spellbook",
                            record.name
                        )));
                    }
                    picked.push(record.id.clone());
                }
                // Re-applying this slot's own decision replaces its picks.
                state.spellbook_added.retain(|(l, _)| *l != level);
                for id in picked {
                    state.spellbook_added.push((level, id));
                }
                Ok(())
            }),
            validate: Box::new(move |state, decision| {
                let Some(sc) = caster(state, &d_val) else {
                    return vec![];
                };
                if (state.level() as u32) < level {
                    return vec![];
                }
                let picked: Vec<String> = state
                    .spellbook_added
                    .iter()
                    .filter(|(l, _)| *l == level)
                    .map(|(_, id)| id.clone())
                    .collect();
                book_count_entries_in(
                    &slot_v,
                    &step_v,
                    "new spell",
                    sc.spells_per_level as usize,
                    &picked,
                    decision.is_some(),
                )
            }),
            meters: Box::new(|_, _| vec![]),
            describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
        });
    }
    regs
}

/// `book_count_entries` for a slot in an arbitrary step.
fn book_count_entries_in(
    slot: &str,
    step: &str,
    noun: &str,
    count: usize,
    picked: &[String],
    has_decision: bool,
) -> Vec<types::ChecklistEntry> {
    let mut out = vec![];
    if !has_decision || picked.len() < count {
        out.push(incomplete(
            slot,
            step,
            "Spellbook",
            &format!(
                "{} {noun}(s) left to inscribe",
                count.saturating_sub(picked.len()).max(1)
            ),
            "from Class: spellbook",
        ));
    }
    if picked.len() > count {
        out.push(illegal(
            slot,
            step,
            "Spellbook",
            &format!("this level adds {count} — remove some"),
            "from Class: spellbook",
        ));
    }
    out
}
