//! Equipment kind: the class kit choice (kit-first, per the spec) and the
//! open-ended extra-item list, all under the 15 gp starting wealth.

use std::sync::Arc;

use engine_core::{ApplyError, Availability, SlotRegistration};
use types::{MeterState, MeterView, OptionId, OptionView, SlotId, SlotViewKind, StepId};

use crate::data::RulesData;
use crate::mechanics::{
    describe_selection, format_cp, illegal, incomplete, item_name, item_price_cp, sel_single,
    total_spend_cp, Pf2eState, SLOT_EXTRA_ITEMS, SLOT_KIT, STARTING_WEALTH_CP,
};

const STEP: &str = crate::mechanics::STEP_EQUIPMENT;

const NO_KIT: &str = "equipment.no-kit";

pub fn registrations(data: &Arc<RulesData>) -> Vec<SlotRegistration<Pf2eState>> {
    let mut regs = Vec::new();

    // --- Kit ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_KIT),
        step: StepId::new(STEP),
        label: "Class kit".into(),
        required: true,
        presentation_hint: None,
        kind: Box::new(|_| SlotViewKind::Single),
        unlock: Box::new(|state| match state.class {
            Some(_) => Availability::Open,
            None => Availability::Locked {
                reason: "choose a class first — kits are class-specific".into(),
            },
        }),
        dependents: vec![],
        options: Box::new(move |state| {
            let Some(class) = &state.class else {
                return vec![];
            };
            let mut out = Vec::new();
            for kit in d.equipment.kits.iter().filter(|k| &k.class == class) {
                let contents: Vec<String> =
                    kit.contents.iter().map(|id| item_name(id, &d)).collect();
                out.push(OptionView {
                    id: OptionId::new(&kit.id),
                    label: kit.name.clone(),
                    summary: format!(
                        "{} · {}",
                        format_cp(kit.price_cp as i64),
                        contents.join(", ")
                    ),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                });
                for opt in &kit.options {
                    out.push(OptionView {
                        id: OptionId::new(&opt.id),
                        label: format!("{} + {}", kit.name, opt.name),
                        summary: format!(
                            "{} · kit plus {}",
                            format_cp((kit.price_cp + opt.price_cp) as i64),
                            opt.items
                                .iter()
                                .map(|id| item_name(id, &d))
                                .collect::<Vec<_>>()
                                .join(", ")
                        ),
                        details: vec![],
                        available: true,
                        unavailable_reason: None,
                    });
                }
            }
            out.push(OptionView {
                id: OptionId::new(NO_KIT),
                label: "No kit — buy items individually".into(),
                summary: "Spend your 15 gp on the item list instead".into(),
                details: vec![],
                available: true,
                unavailable_reason: None,
            });
            out
        }),
        apply: Box::new(move |state, decision| {
            let id = sel_single(&decision.selection)?;
            if id.as_str() == NO_KIT {
                state.kit = None;
                return Ok(());
            }
            if let Some(kit) = d_apply.kit(id.as_str()) {
                state.kit = Some((kit.id.clone(), None));
                return Ok(());
            }
            for kit in &d_apply.equipment.kits {
                if let Some(opt) = kit.options.iter().find(|o| o.id == id.as_str()) {
                    state.kit = Some((kit.id.clone(), Some(opt.id.clone())));
                    return Ok(());
                }
            }
            Err(ApplyError::new(format!("unknown kit option '{id}'")))
        }),
        validate: Box::new(|state, decision| {
            if state.class.is_some() && decision.is_none() {
                vec![incomplete(
                    SLOT_KIT,
                    STEP,
                    "Equipment",
                    "Take the class kit (or choose to buy items individually)",
                    "from Class",
                )]
            } else {
                vec![]
            }
        }),
        meters: Box::new(|_, _| vec![]),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    // --- Extra items ---
    let d = data.clone();
    let d_apply = data.clone();
    let d_val = data.clone();
    let d_meter = data.clone();
    let d_desc = data.clone();
    regs.push(SlotRegistration::<Pf2eState> {
        id: SlotId::new(SLOT_EXTRA_ITEMS),
        step: StepId::new(STEP),
        label: "Additional items".into(),
        required: false,
        presentation_hint: Some("shopping-list".into()),
        kind: Box::new(|_| SlotViewKind::List),
        unlock: Box::new(|_| Availability::Open),
        dependents: vec![],
        options: Box::new(move |_| {
            let e = &d.equipment;
            let mut out = Vec::new();
            for (id, name, price, bulk) in e
                .weapons
                .iter()
                .map(|w| (&w.id, &w.name, w.price_cp, &w.bulk))
                .chain(
                    e.armor
                        .iter()
                        .map(|a| (&a.id, &a.name, a.price_cp, &a.bulk)),
                )
                .chain(
                    e.shields
                        .iter()
                        .map(|s| (&s.id, &s.name, s.price_cp, &s.bulk)),
                )
                .chain(e.gear.iter().map(|g| (&g.id, &g.name, g.price_cp, &g.bulk)))
            {
                out.push(OptionView {
                    id: OptionId::new(id),
                    label: name.clone(),
                    summary: format!("{} · Bulk {}", format_cp(price as i64), bulk),
                    details: vec![],
                    available: true,
                    unavailable_reason: None,
                });
            }
            out
        }),
        apply: Box::new(move |state, decision| {
            let ids = match &decision.selection {
                types::Selection::Options(ids) => ids,
                _ => return Err(ApplyError::new("expected an item list")),
            };
            for id in ids {
                if item_price_cp(id.as_str(), &d_apply) == 0
                    && item_name(id.as_str(), &d_apply) == id.as_str()
                {
                    return Err(ApplyError::new(format!("unknown item '{id}'")));
                }
            }
            state.extra_items = ids.iter().map(|i| i.as_str().to_string()).collect();
            Ok(())
        }),
        validate: Box::new(move |state, _| {
            let spend = total_spend_cp(state, &d_val);
            if spend > STARTING_WEALTH_CP {
                vec![illegal(
                    SLOT_EXTRA_ITEMS,
                    STEP,
                    "Starting wealth",
                    &format!(
                        "You've spent {} but starting wealth is 15 gp",
                        format_cp(spend)
                    ),
                    "Player Core pg. 10",
                )]
            } else {
                vec![]
            }
        }),
        // The always-on gauge the budget rule derives from: a violation
        // without a visible meter is unrepresentable. Shoppers think in
        // what's left, so remaining is the headline.
        meters: Box::new(move |state, _| {
            let spend = total_spend_cp(state, &d_meter);
            vec![MeterView {
                label: "Remaining".into(),
                current: format_cp(STARTING_WEALTH_CP - spend),
                limit: Some("15 gp".into()),
                state: if spend > STARTING_WEALTH_CP {
                    MeterState::Exceeded
                } else {
                    MeterState::Ok
                },
            }]
        }),
        describe: Box::new(move |sel| describe_selection(&d_desc, sel)),
    });

    regs
}
