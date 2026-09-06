//! Class kind: the class slot, its skill picks and weapon masteries, and
//! the subclass slot each subclass-granting level opens (its catalog is
//! the subclass records for the chosen class).

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    describe_selection, illegal, incomplete, sel_multi, sel_single, slot_level_subclass,
    step_level, Dnd5eState, SLOT_CLASS, SLOT_CLASS_MASTERIES, SLOT_CLASS_SKILLS, SLOT_CLASS_STYLE,
    SLOT_EQUIPMENT_PACKAGE, STEP_CLASS, STEP_CLASS_CHOICES,
};

fn option(id: &str, label: &str, summary: String, details: Vec<String>) -> OptionView {
    OptionView {
        id: OptionId::new(id),
        label: label.to_string(),
        summary,
        details,
        available: true,
        unavailable_reason: None,
        group: None,
        badge: None,
    }
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Dnd5eState>> {
    let mut regs = Vec::new();

    // --- Class ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_CLASS),
        step: StepId::new(STEP_CLASS),
        label: "Class".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![
            SlotId::new(SLOT_CLASS_SKILLS),
            SlotId::new(SLOT_CLASS_STYLE),
            SlotId::new(SLOT_CLASS_MASTERIES),
            SlotId::new(SLOT_EQUIPMENT_PACKAGE),
        ],
        options: Box::new(move |_| {
            d.classes
                .iter()
                .map(|c| {
                    option(
                        &c.id,
                        &c.name,
                        c.text.clone(),
                        vec![
                            format!(
                                "Primary ability: {}",
                                c.primary_abilities
                                    .iter()
                                    .map(|a| a.name())
                                    .collect::<Vec<_>>()
                                    .join(" or ")
                            ),
                            format!("Hit Point Die: D{}", c.hit_die),
                            format!(
                                "Saving throws: {}",
                                c.saving_throws
                                    .iter()
                                    .map(|a| a.name())
                                    .collect::<Vec<_>>()
                                    .join(", ")
                            ),
                            format!(
                                "Level 1: {}",
                                c.features
                                    .iter()
                                    .map(|f| f.name.as_str())
                                    .collect::<Vec<_>>()
                                    .join(", ")
                            ),
                        ],
                    )
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .class(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown class '{id}'")))?;
            state.class = Some(record.id.clone());
            state.class_name = Some(record.name.clone());
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.class.is_none() {
                vec![incomplete(
                    SLOT_CLASS,
                    STEP_CLASS,
                    "Class",
                    "Choose a class",
                    "character creation",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Class skills ---
    let d = data.clone();
    let d_kind = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_CLASS_SKILLS),
        step: StepId::new(STEP_CLASS_CHOICES),
        label: "Class skills".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(move |state| SlotViewKind::Multi {
            count: state
                .class
                .as_ref()
                .and_then(|id| d_kind.class(id))
                .map(|c| c.skill_choice.count)
                .unwrap_or(0),
        }),
        unlock: Box::new(|state| match state.class {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose a class first".into(),
            },
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(c) = state.class.as_ref().and_then(|id| d.class(id)) else {
                return vec![];
            };
            // Skills the background or species already granted are not
            // legal picks: the class list offers only what would be new.
            let granted: Vec<_> = state
                .skill_proficiencies(&d)
                .into_iter()
                .filter(|p| !state.class_skills.contains(&p.id))
                .collect();
            c.skill_choice
                .from
                .iter()
                .filter_map(|id| d.skill(id))
                .map(|s| {
                    let owner = granted.iter().find(|p| p.id == s.id);
                    let mut o = option(
                        &s.id,
                        &s.name,
                        format!("{} skill", s.ability.name()),
                        vec![],
                    );
                    if let Some(p) = owner {
                        o.available = false;
                        o.unavailable_reason =
                            Some(format!("already proficient from {}", p.source));
                    }
                    o
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            let Some(c) = state.class.as_ref().and_then(|id| d_apply.class(id)) else {
                return Err(ApplyError::new("choose a class before its skills"));
            };
            for id in ids {
                if !c.skill_choice.from.iter().any(|s| s == id.as_str()) {
                    return Err(ApplyError::new(format!(
                        "'{id}' is not one of the class's skill options"
                    )));
                }
            }
            state.class_skills = ids.iter().map(|i| i.as_str().to_string()).collect();
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(c) = state.class.as_ref().and_then(|id| d_val.class(id)) else {
                return vec![];
            };
            let mut out = Vec::new();
            let count = c.skill_choice.count as usize;
            if decision.is_none() || state.class_skills.len() < count {
                out.push(incomplete(
                    SLOT_CLASS_SKILLS,
                    STEP_CLASS_CHOICES,
                    "Skill Proficiencies",
                    &format!(
                        "{} skill choice(s) left",
                        count - state.class_skills.len().min(count)
                    ),
                    &format!("from {}", c.name),
                ));
            }
            if state.class_skills.len() > count {
                out.push(illegal(
                    SLOT_CLASS_SKILLS,
                    STEP_CLASS_CHOICES,
                    "Skill Proficiencies",
                    &format!("Choose exactly {count} skills"),
                    &format!("from {}", c.name),
                ));
            }
            let mut sorted = state.class_skills.clone();
            sorted.sort();
            sorted.dedup();
            if sorted.len() != state.class_skills.len() {
                out.push(illegal(
                    SLOT_CLASS_SKILLS,
                    STEP_CLASS_CHOICES,
                    "Skill Proficiencies",
                    "Each skill can be chosen only once",
                    &format!("from {}", c.name),
                ));
            }
            for pick in &state.class_skills {
                if let Some(owner) = state
                    .skill_proficiencies(&d_val)
                    .into_iter()
                    .find(|p| p.id == *pick && p.source != c.name)
                {
                    out.push(illegal(
                        SLOT_CLASS_SKILLS,
                        STEP_CLASS_CHOICES,
                        "Skill Proficiencies",
                        &format!(
                            "{} is already granted by {} — choose a different skill",
                            d_val.skill(pick).map(|s| s.name.as_str()).unwrap_or(pick),
                            owner.source
                        ),
                        &format!("from {}", c.name),
                    ));
                }
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Weapon masteries ---
    let d = data.clone();
    let d_kind = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_val2 = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_CLASS_MASTERIES),
        step: StepId::new(STEP_CLASS_CHOICES),
        label: "Weapon masteries".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(move |state| SlotViewKind::Multi {
            count: state
                .class
                .as_ref()
                .and_then(|id| d_kind.class(id))
                .map(|c| c.weapon_mastery_count)
                .unwrap_or(0),
        }),
        unlock: Box::new(
            move |state| match state.class.as_ref().and_then(|id| d.class(id)) {
                Some(c) if c.weapon_mastery_feature.is_some() => Availability::Open,
                Some(_) => Availability::Hidden,
                None => Availability::Locked {
                    reason: "choose a class first".into(),
                },
            },
        ),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(c) = state.class.as_ref().and_then(|id| d_apply.class(id)) else {
                return vec![];
            };
            d_apply
                .equipment
                .weapons
                .iter()
                .filter(|w| c.is_proficient_with_weapon(w))
                .map(|w| {
                    let mut o = option(
                        &w.id,
                        &w.name,
                        format!("{} — {} {}", w.mastery, w.damage, w.damage_type),
                        if w.properties.is_empty() {
                            vec![]
                        } else {
                            vec![w.properties.join(", ")]
                        },
                    );
                    o.group = Some(format!("{} {} weapons", capitalize(&w.category), w.kind));
                    o.badge = Some(w.mastery.clone());
                    o
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let ids = sel_multi(&decision.selection)?;
            let Some(c) = state.class.as_ref().and_then(|id| d_val.class(id)) else {
                return Err(ApplyError::new(
                    "choose a class before its weapon masteries",
                ));
            };
            for id in ids {
                let w = d_val
                    .weapon(id.as_str())
                    .ok_or_else(|| ApplyError::new(format!("unknown weapon '{id}'")))?;
                if !c.is_proficient_with_weapon(w) {
                    return Err(ApplyError::new(format!(
                        "{} is not proficient with the {}",
                        c.name, w.name
                    )));
                }
            }
            state.masteries = ids.iter().map(|i| i.as_str().to_string()).collect();
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(c) = state.class.as_ref().and_then(|id| d_val2.class(id)) else {
                return vec![];
            };
            let Some(feature_id) = &c.weapon_mastery_feature else {
                return vec![];
            };
            let feature = c
                .feature(feature_id)
                .map(|f| f.name.clone())
                .unwrap_or_default();
            let count = c.weapon_mastery_count as usize;
            let mut out = Vec::new();
            if decision.is_none() || state.masteries.len() < count {
                out.push(incomplete(
                    SLOT_CLASS_MASTERIES,
                    STEP_CLASS_CHOICES,
                    &feature,
                    &format!(
                        "{} weapon mastery choice(s) left",
                        count - state.masteries.len().min(count)
                    ),
                    &format!("from {}", c.name),
                ));
            }
            if state.masteries.len() > count {
                out.push(illegal(
                    SLOT_CLASS_MASTERIES,
                    STEP_CLASS_CHOICES,
                    &feature,
                    &format!("Choose exactly {count} kinds of weapon"),
                    &format!("from {}", c.name),
                ));
            }
            let mut sorted = state.masteries.clone();
            sorted.sort();
            sorted.dedup();
            if sorted.len() != state.masteries.len() {
                out.push(illegal(
                    SLOT_CLASS_MASTERIES,
                    STEP_CLASS_CHOICES,
                    &feature,
                    "Each kind of weapon can be chosen only once",
                    &format!("from {}", c.name),
                ));
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Subclass, at every level some class opens the choice ---
    for level in data.subclass_levels() {
        let d_unlock = data.clone();
        let d_opts = data.clone();
        let d_apply = data.clone();
        let d_val = data.clone();
        let d_desc = data.clone();
        regs.push(SlotRegistration::<Dnd5eState> {
            id: SlotId::new(slot_level_subclass(level)),
            step: StepId::new(step_level(level)),
            label: "Subclass".into(),
            required: true,
            presentation_hint: None,
            kind: Box::new(|_| SlotViewKind::Single),
            unlock: Box::new(move |state| {
                let opens = state
                    .class
                    .as_ref()
                    .and_then(|id| d_unlock.class(id))
                    .and_then(|c| c.advancement_at(level))
                    .is_some_and(|a| a.subclass_choice);
                if opens && state.level() == level {
                    Availability::Open
                } else {
                    Availability::Hidden
                }
            }),
            dependents: vec![],
            options: Box::new(move |state| {
                let Some(class) = &state.class else {
                    return vec![];
                };
                d_opts
                    .subclasses
                    .iter()
                    .filter(|s| &s.class == class)
                    .map(|s| {
                        option(
                            &s.id,
                            &s.name,
                            s.text.clone(),
                            s.features
                                .iter()
                                .map(|f| format!("Level {}: {} — {}", f.level, f.name, f.text))
                                .collect(),
                        )
                    })
                    .collect()
            }),
            apply: Box::new(move |state, decision| {
                let id = sel_single(&decision.selection)?;
                let record = d_apply
                    .subclass(id.as_str())
                    .ok_or_else(|| ApplyError::new(format!("unknown subclass '{id}'")))?;
                if state.class.as_deref() != Some(record.class.as_str()) {
                    return Err(ApplyError::new(format!(
                        "{} is not a subclass of the chosen class",
                        record.name
                    )));
                }
                if state.level() != level {
                    return Err(ApplyError::new(format!(
                        "the subclass is chosen at level {level}, not {}",
                        state.level()
                    )));
                }
                state.subclass = Some(record.id.clone());
                Ok(())
            }),
            validate: Box::new(move |state, decision| {
                let Some(c) = state.class.as_ref().and_then(|id| d_val.class(id)) else {
                    return vec![];
                };
                if decision.is_none() && state.subclass.is_none() {
                    vec![incomplete(
                        &slot_level_subclass(level),
                        &step_level(level),
                        &format!("{} Subclass", c.name),
                        "Choose a subclass",
                        &format!("from {} level {level}", c.name),
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

fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
        None => String::new(),
    }
}
