//! Background kind: the background slot, the distribution of its ability
//! increases (a Single over the seven legal distributions, enumerated as
//! data), and its equipment offer (package or coin).

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    describe_selection, illegal, incomplete, sel_single, Ability, BackgroundEquipment, Dnd5eState,
    Increase, ABILITY_SCORE_CAP, BACKGROUND_EQUIPMENT_GOLD, BACKGROUND_EQUIPMENT_PACKAGE,
    SLOT_BACKGROUND, SLOT_BACKGROUND_EQUIPMENT, SLOT_BACKGROUND_INCREASE, SLOT_FEAT_SKILLED,
    STEP_EQUIPMENT, STEP_ORIGIN,
};

fn option(id: OptionId, label: String, summary: String, details: Vec<String>) -> OptionView {
    OptionView {
        id,
        label,
        summary,
        details,
        available: true,
        unavailable_reason: None,
        group: None,
        badge: None,
    }
}

fn locked_until_background(state: &Dnd5eState) -> Availability {
    match state.background {
        Some(_) => Availability::Open,
        None => Availability::Locked {
            reason: "choose a background first".into(),
        },
    }
}

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Dnd5eState>> {
    let mut regs = Vec::new();

    // --- Background ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_BACKGROUND),
        step: StepId::new(STEP_ORIGIN),
        label: "Background".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![
            SlotId::new(SLOT_BACKGROUND_INCREASE),
            SlotId::new(SLOT_BACKGROUND_EQUIPMENT),
            SlotId::new(SLOT_FEAT_SKILLED),
        ],
        options: Box::new(move |_| {
            d.backgrounds
                .iter()
                .map(|b| {
                    let skills = b
                        .skills
                        .iter()
                        .filter_map(|id| d.skill(id))
                        .map(|s| s.name.clone())
                        .collect::<Vec<_>>()
                        .join(", ");
                    let items = b
                        .equipment
                        .items
                        .iter()
                        .map(|line| {
                            let name = d.item_name(&line.item).unwrap_or_default();
                            if line.count > 1 {
                                format!("{} {name}", line.count)
                            } else {
                                name
                            }
                        })
                        .collect::<Vec<_>>()
                        .join(", ");
                    option(
                        OptionId::new(&b.id),
                        b.name.clone(),
                        format!(
                            "Ability scores: {}",
                            b.abilities
                                .iter()
                                .map(|a| a.name())
                                .collect::<Vec<_>>()
                                .join(", ")
                        ),
                        vec![
                            format!("Feat: {}", b.feat_label(&d)),
                            format!("Skill proficiencies: {skills}"),
                            format!(
                                "Tool proficiency: {}",
                                d.tool(&b.tool).map(|t| t.name.clone()).unwrap_or_default()
                            ),
                            format!(
                                "Equipment: {items}, {} GP; or {} GP",
                                b.equipment.gold, b.gold_alternative
                            ),
                        ],
                    )
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let record = d_apply
                .background(id.as_str())
                .ok_or_else(|| ApplyError::new(format!("unknown background '{id}'")))?;
            state.background = Some(record.id.clone());
            Ok(())
        }),
        validate: Box::new(|state, _| {
            if state.background.is_none() {
                vec![incomplete(
                    SLOT_BACKGROUND,
                    STEP_ORIGIN,
                    "Background",
                    "Choose a background",
                    "character creation",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Ability-score increase distribution ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_BACKGROUND_INCREASE),
        step: StepId::new(STEP_ORIGIN),
        label: "Ability score increases".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(locked_until_background),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(b) = state.background.as_ref().and_then(|id| d.background(id)) else {
                return vec![];
            };
            Increase::all(&b.abilities)
                .into_iter()
                .map(|inc| {
                    option(
                        inc.option_id(),
                        inc.label(&b.abilities),
                        match inc {
                            Increase::TwoOne(..) => "+2 to one ability and +1 to another".into(),
                            Increase::AllOne => "+1 to each of the three".into(),
                        },
                        vec![],
                    )
                })
                .collect()
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            let increase = Increase::parse(id)
                .ok_or_else(|| ApplyError::new(format!("'{id}' is not an increase option")))?;
            let Some(b) = state.background.as_ref().and_then(|id| d_apply.background(id)) else {
                return Err(ApplyError::new("choose a background before its increases"));
            };
            if let Increase::TwoOne(a, c) = increase {
                if !b.abilities.contains(&a) || !b.abilities.contains(&c) {
                    return Err(ApplyError::new(format!(
                        "{} does not offer increases to {} and {}",
                        b.name,
                        a.name(),
                        c.name()
                    )));
                }
            }
            state.increase = Some(increase);
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(b) = state.background.as_ref().and_then(|id| d_val.background(id)) else {
                return vec![];
            };
            let mut out = Vec::new();
            if decision.is_none() || state.increase.is_none() {
                out.push(incomplete(
                    SLOT_BACKGROUND_INCREASE,
                    STEP_ORIGIN,
                    "Ability Scores",
                    "Distribute the background's ability score increases (+2 and +1, or +1 to each)",
                    &format!("from {}", b.name),
                ));
            }
            // The published cap: unreachable by array or point buy, but a
            // rule is a rule (rolling in dnd-dice exercises it).
            for ability in Ability::ALL {
                if let Some(score) = state.score(ability, &d_val) {
                    if score > ABILITY_SCORE_CAP {
                        out.push(illegal(
                            SLOT_BACKGROUND_INCREASE,
                            STEP_ORIGIN,
                            "Ability Scores",
                            &format!(
                                "{} would be {score}: none of these increases can raise a score above {ABILITY_SCORE_CAP}",
                                ability.name()
                            ),
                            &format!("from {}", b.name),
                        ));
                    }
                }
            }
            out
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Background equipment: the package or the coin ---
    let d = data.clone();
    let d_val = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Dnd5eState> {
        id: SlotId::new(SLOT_BACKGROUND_EQUIPMENT),
        step: StepId::new(STEP_EQUIPMENT),
        label: "Background equipment".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(locked_until_background),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(b) = state.background.as_ref().and_then(|id| d.background(id)) else {
                return vec![];
            };
            let items = b
                .equipment
                .items
                .iter()
                .map(|line| {
                    let name = d.item_name(&line.item).unwrap_or_default();
                    if line.count > 1 {
                        format!("{} {name}", line.count)
                    } else {
                        name
                    }
                })
                .collect::<Vec<_>>()
                .join(", ");
            vec![
                option(
                    OptionId::new(BACKGROUND_EQUIPMENT_PACKAGE),
                    format!("{} equipment package", b.name),
                    format!("{items}, and {} GP", b.equipment.gold),
                    vec![],
                ),
                option(
                    OptionId::new(BACKGROUND_EQUIPMENT_GOLD),
                    format!("{} GP instead", b.gold_alternative),
                    "Take the coin and buy equipment yourself".into(),
                    vec![],
                ),
            ]
        }),
        apply: Box::new(|state, decision| {
            let id = sel_single(&decision.selection)?;
            if state.background.is_none() {
                return Err(ApplyError::new("choose a background before its equipment"));
            }
            state.background_equipment = Some(match id.as_str() {
                BACKGROUND_EQUIPMENT_PACKAGE => BackgroundEquipment::Package,
                BACKGROUND_EQUIPMENT_GOLD => BackgroundEquipment::Gold,
                other => {
                    return Err(ApplyError::new(format!(
                        "'{other}' is not a background equipment option"
                    )))
                }
            });
            Ok(())
        }),
        validate: Box::new(move |state, decision| {
            let Some(b) = state
                .background
                .as_ref()
                .and_then(|id| d_val.background(id))
            else {
                return vec![];
            };
            if decision.is_none() || state.background_equipment.is_none() {
                vec![incomplete(
                    SLOT_BACKGROUND_EQUIPMENT,
                    STEP_EQUIPMENT,
                    "Starting Equipment",
                    &format!(
                        "Take the background's equipment package or {} GP",
                        b.gold_alternative
                    ),
                    &format!("from {}", b.name),
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}
