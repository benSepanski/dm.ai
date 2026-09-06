//! Shared 5.5e mechanics: abilities and modifiers, the proficiency bonus,
//! the folded character state, option-id conventions, checklist helpers,
//! and sheet derivation. Kind modules depend on this; this module never
//! references a kind.

use std::collections::BTreeMap;

use engine_core::ApplyError;
use serde::Deserialize;
use types::{
    ChecklistEntry, ChecklistSeverity, OptionId, Selection, SheetEntry, SheetSection, SheetView,
    SlotId, StepId,
};

use crate::data::{ArmorRecord, Effect, RulesData, WeaponRecord};

/// The six abilities, in the published order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Ability {
    Str,
    Dex,
    Con,
    Int,
    Wis,
    Cha,
}

impl Ability {
    pub const ALL: [Ability; 6] = [
        Ability::Str,
        Ability::Dex,
        Ability::Con,
        Ability::Int,
        Ability::Wis,
        Ability::Cha,
    ];

    pub fn name(self) -> &'static str {
        match self {
            Ability::Str => "Strength",
            Ability::Dex => "Dexterity",
            Ability::Con => "Constitution",
            Ability::Int => "Intelligence",
            Ability::Wis => "Wisdom",
            Ability::Cha => "Charisma",
        }
    }
    pub fn abbrev(self) -> &'static str {
        match self {
            Ability::Str => "Str",
            Ability::Dex => "Dex",
            Ability::Con => "Con",
            Ability::Int => "Int",
            Ability::Wis => "Wis",
            Ability::Cha => "Cha",
        }
    }
    /// The lowercase key used inside option IDs (`str`, `dex`, ...).
    pub fn key(self) -> &'static str {
        match self {
            Ability::Str => "str",
            Ability::Dex => "dex",
            Ability::Con => "con",
            Ability::Int => "int",
            Ability::Wis => "wis",
            Ability::Cha => "cha",
        }
    }
    pub fn from_key(key: &str) -> Option<Ability> {
        Ability::ALL.into_iter().find(|a| a.key() == key)
    }
}

/// The published modifier table: (score − 10) ÷ 2, rounded down.
pub fn modifier_of(score: u32) -> i32 {
    (score as i32 - 10).div_euclid(2)
}

/// The published Proficiency Bonus by character level (+2 through 4,
/// +3 through 8, ...).
pub fn proficiency_bonus(level: u32) -> i32 {
    2 + ((level.max(1) - 1) / 4) as i32
}

/// No ability-score increase can raise a score above this (Character
/// Origins, "Ability Scores").
pub const ABILITY_SCORE_CAP: u32 = 20;

pub fn format_signed(n: i32) -> String {
    if n >= 0 {
        format!("+{n}")
    } else {
        n.to_string()
    }
}

/// Render pounds the way the equipment tables do ("55 lb.", "0.25 lb.").
pub fn format_weight(lb: f64) -> String {
    if (lb - lb.round()).abs() < 1e-9 {
        format!("{} lb.", lb.round() as i64)
    } else {
        let s = format!("{lb:.2}");
        format!("{} lb.", s.trim_end_matches('0').trim_end_matches('.'))
    }
}

pub fn format_gp(gp: u32) -> String {
    format!("{gp} GP")
}

// ---- Option-id conventions -------------------------------------------

/// `score.<ability>.<value>` — one assignment option.
pub fn score_option_id(ability: Ability, value: u32) -> OptionId {
    OptionId::new(format!("score.{}.{value}", ability.key()))
}

pub fn parse_score_option(id: &OptionId) -> Option<(Ability, u32)> {
    let rest = id.as_str().strip_prefix("score.")?;
    let (key, value) = rest.split_once('.')?;
    Some((Ability::from_key(key)?, value.parse().ok()?))
}

/// How a background's increases are distributed among its abilities.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Increase {
    /// +2 to the first, +1 to the second.
    TwoOne(Ability, Ability),
    /// +1 to each of the background's three abilities.
    AllOne,
}

impl Increase {
    pub fn option_id(self) -> OptionId {
        match self {
            Increase::TwoOne(a, b) => OptionId::new(format!("increase.{}2-{}1", a.key(), b.key())),
            Increase::AllOne => OptionId::new("increase.all1"),
        }
    }
    pub fn parse(id: &OptionId) -> Option<Increase> {
        let rest = id.as_str().strip_prefix("increase.")?;
        if rest == "all1" {
            return Some(Increase::AllOne);
        }
        let (two, one) = rest.split_once('-')?;
        let a = Ability::from_key(two.strip_suffix('2')?)?;
        let b = Ability::from_key(one.strip_suffix('1')?)?;
        Some(Increase::TwoOne(a, b))
    }
    /// Render-ready label given the background's abilities (for AllOne).
    pub fn label(self, abilities: &[Ability]) -> String {
        match self {
            Increase::TwoOne(a, b) => format!("{} +2, {} +1", a.name(), b.name()),
            Increase::AllOne => abilities
                .iter()
                .map(|a| format!("{} +1", a.name()))
                .collect::<Vec<_>>()
                .join(", "),
        }
    }
    /// The seven legal distributions over three abilities, in a stable
    /// order: the six ordered pairs, then +1 to each.
    pub fn all(abilities: &[Ability]) -> Vec<Increase> {
        let mut out = Vec::new();
        for a in abilities {
            for b in abilities {
                if a != b {
                    out.push(Increase::TwoOne(*a, *b));
                }
            }
        }
        out.push(Increase::AllOne);
        out
    }
    pub fn amounts(self, abilities: &[Ability]) -> BTreeMap<Ability, i32> {
        let mut map = BTreeMap::new();
        match self {
            Increase::TwoOne(a, b) => {
                map.insert(a, 2);
                map.insert(b, 1);
            }
            Increase::AllOne => {
                for a in abilities {
                    map.insert(*a, 1);
                }
            }
        }
        map
    }
}

/// How a background's equipment offer was taken.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BackgroundEquipment {
    Package,
    Gold,
}

pub const BACKGROUND_EQUIPMENT_PACKAGE: &str = "background-equipment.package";
pub const BACKGROUND_EQUIPMENT_GOLD: &str = "background-equipment.gold";

// ---- The folded state ---------------------------------------------------

#[derive(Debug, Clone, Default)]
pub struct Dnd5eState {
    pub class: Option<String>,
    /// The chosen class's display name, resolved from its record at apply
    /// time — source labels derive from this, never from a literal.
    pub class_name: Option<String>,
    pub background: Option<String>,
    pub increase: Option<Increase>,
    pub background_equipment: Option<BackgroundEquipment>,
    pub species: Option<String>,
    pub species_skill: Option<String>,
    pub species_feat: Option<String>,
    pub species_ancestry: Option<String>,
    pub score_method: Option<String>,
    /// Assignment picks in pick order; validators judge one per ability
    /// and (array) each value once. The first pick per ability counts.
    pub assignments: Vec<(Ability, u32)>,
    pub class_skills: Vec<String>,
    pub fighting_style: Option<String>,
    pub masteries: Vec<String>,
    /// Skill or tool IDs chosen through a `choose_skills_or_tools` feat.
    pub skilled_picks: Vec<String>,
    /// The chosen class package ID, or the class's gold-alternative ID.
    pub equipment_package: Option<String>,
    pub name: Option<String>,
    pub description: Option<String>,
    /// Level advances applied, in order: the character's level is one plus
    /// this count. Set only by the advance slots' `apply`.
    pub level_advances: u32,
    /// Fixed class features granted by advances, (level, feature ID).
    pub granted_features: Vec<(u32, String)>,
    pub subclass: Option<String>,
}

/// One skill or tool proficiency and where it came from.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Proficiency {
    pub id: String,
    pub source: String,
}

/// One carried item line.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Carried {
    pub item: String,
    pub count: u32,
    pub source: String,
}

impl Dnd5eState {
    pub fn level(&self) -> u32 {
        1 + self.level_advances
    }

    pub fn proficiency_bonus(&self) -> i32 {
        proficiency_bonus(self.level())
    }

    /// The generated score assigned to an ability (first pick wins), before
    /// the background's increase.
    pub fn base_score(&self, ability: Ability) -> Option<u32> {
        self.assignments
            .iter()
            .find(|(a, _)| *a == ability)
            .map(|(_, v)| *v)
    }

    /// The background's distributed increases, resolved against its
    /// abilities.
    pub fn increases(&self, data: &RulesData) -> BTreeMap<Ability, i32> {
        let Some(increase) = self.increase else {
            return BTreeMap::new();
        };
        let abilities = self
            .background
            .as_ref()
            .and_then(|id| data.background(id))
            .map(|b| b.abilities.clone())
            .unwrap_or_default();
        increase.amounts(&abilities)
    }

    /// The final score: generated value plus increases. `None` until the
    /// ability is assigned (increases alone do not make a score).
    pub fn score(&self, ability: Ability, data: &RulesData) -> Option<u32> {
        let base = self.base_score(ability)? as i32;
        let inc = self.increases(data).get(&ability).copied().unwrap_or(0);
        Some((base + inc).max(1) as u32)
    }

    /// The modifier of the final score; an unassigned ability counts as 10
    /// (+0) so derived numbers stay meaningful mid-wizard.
    pub fn modifier(&self, ability: Ability, data: &RulesData) -> i32 {
        modifier_of(self.score(ability, data).unwrap_or(10))
    }

    /// Every feat the character holds, (feat ID, source label, display
    /// name): the background's origin feat, the species' chosen origin
    /// feat, and the Fighting Style feat.
    pub fn feats(&self, data: &RulesData) -> Vec<(String, String, String)> {
        let mut out = Vec::new();
        if let Some(b) = self.background.as_ref().and_then(|id| data.background(id)) {
            out.push((b.feat.clone(), b.name.clone(), b.feat_label(data)));
        }
        if let (Some(feat), Some(sp)) = (
            self.species_feat.as_ref().and_then(|id| data.feat(id)),
            self.species.as_ref().and_then(|id| data.species(id)),
        ) {
            out.push((feat.id.clone(), sp.name.clone(), feat.name.clone()));
        }
        if let (Some(feat), Some(class)) = (
            self.fighting_style.as_ref().and_then(|id| data.feat(id)),
            self.class_name.as_ref(),
        ) {
            out.push((feat.id.clone(), class.clone(), feat.name.clone()));
        }
        out
    }

    pub fn effects(&self, data: &RulesData) -> Vec<Effect> {
        self.feats(data)
            .iter()
            .filter_map(|(id, _, _)| data.feat(id))
            .flat_map(|f| f.effects.iter().cloned())
            .collect()
    }

    pub fn has_effect(&self, data: &RulesData, pred: impl Fn(&Effect) -> bool) -> bool {
        self.effects(data).iter().any(pred)
    }

    /// The number of `choose_skills_or_tools` picks the held feats grant.
    pub fn skilled_pick_count(&self, data: &RulesData) -> u32 {
        self.effects(data)
            .iter()
            .filter_map(|e| match e {
                Effect::ChooseSkillsOrTools { count } => Some(*count),
                _ => None,
            })
            .sum()
    }

    /// Skill proficiencies in canonical precedence: background, species,
    /// class picks, then feat picks. Duplicates are kept (validators flag
    /// them); the first grant owns the skill.
    pub fn skill_proficiencies(&self, data: &RulesData) -> Vec<Proficiency> {
        let mut out = Vec::new();
        if let Some(b) = self.background.as_ref().and_then(|id| data.background(id)) {
            for s in &b.skills {
                out.push(Proficiency {
                    id: s.clone(),
                    source: b.name.clone(),
                });
            }
        }
        if let (Some(skill), Some(sp)) = (
            &self.species_skill,
            self.species.as_ref().and_then(|id| data.species(id)),
        ) {
            out.push(Proficiency {
                id: skill.clone(),
                source: sp.name.clone(),
            });
        }
        if let Some(class) = &self.class_name {
            for s in &self.class_skills {
                out.push(Proficiency {
                    id: s.clone(),
                    source: class.clone(),
                });
            }
        }
        let feat_name = self
            .feats(data)
            .iter()
            .filter_map(|(id, _, _)| data.feat(id))
            .find(|f| f.skill_or_tool_choices() > 0)
            .map(|f| f.name.clone())
            .unwrap_or_default();
        for pick in &self.skilled_picks {
            if data.skill(pick).is_some() {
                out.push(Proficiency {
                    id: pick.clone(),
                    source: feat_name.clone(),
                });
            }
        }
        out
    }

    pub fn is_proficient_in_skill(&self, skill: &str, data: &RulesData) -> bool {
        self.skill_proficiencies(data).iter().any(|p| p.id == skill)
    }

    /// Tool proficiencies: the background's tool, then feat picks.
    pub fn tool_proficiencies(&self, data: &RulesData) -> Vec<Proficiency> {
        let mut out = Vec::new();
        if let Some(b) = self.background.as_ref().and_then(|id| data.background(id)) {
            out.push(Proficiency {
                id: b.tool.clone(),
                source: b.name.clone(),
            });
        }
        let feat_name = self
            .feats(data)
            .iter()
            .filter_map(|(id, _, _)| data.feat(id))
            .find(|f| f.skill_or_tool_choices() > 0)
            .map(|f| f.name.clone())
            .unwrap_or_default();
        for pick in &self.skilled_picks {
            if data.tool(pick).is_some() {
                out.push(Proficiency {
                    id: pick.clone(),
                    source: feat_name.clone(),
                });
            }
        }
        out
    }

    /// Everything carried: the class package's items, then the
    /// background package's. The gold alternatives carry nothing.
    pub fn inventory(&self, data: &RulesData) -> Vec<Carried> {
        let mut out = Vec::new();
        if let Some(class) = self.class.as_ref().and_then(|id| data.class(id)) {
            if let Some(p) = self
                .equipment_package
                .as_ref()
                .and_then(|id| class.equipment_packages.iter().find(|p| &p.id == id))
            {
                for line in &p.items {
                    out.push(Carried {
                        item: line.item.clone(),
                        count: line.count,
                        source: format!("{} package {}", class.name, p.label),
                    });
                }
            }
        }
        if let (Some(BackgroundEquipment::Package), Some(b)) = (
            self.background_equipment,
            self.background.as_ref().and_then(|id| data.background(id)),
        ) {
            for line in &b.equipment.items {
                out.push(Carried {
                    item: line.item.clone(),
                    count: line.count,
                    source: b.name.clone(),
                });
            }
        }
        out
    }

    /// Coin in GP with its sources.
    pub fn coin(&self, data: &RulesData) -> Vec<(u32, String)> {
        let mut out = Vec::new();
        if let Some(class) = self.class.as_ref().and_then(|id| data.class(id)) {
            if let Some(id) = &self.equipment_package {
                if *id == class.gold_alternative.id {
                    out.push((
                        class.gold_alternative.gold,
                        format!("{} option {}", class.name, class.gold_alternative.label),
                    ));
                } else if let Some(p) = class.equipment_packages.iter().find(|p| &p.id == id) {
                    out.push((p.gold, format!("{} package {}", class.name, p.label)));
                }
            }
        }
        if let Some(b) = self.background.as_ref().and_then(|id| data.background(id)) {
            match self.background_equipment {
                Some(BackgroundEquipment::Package) => {
                    out.push((b.equipment.gold, b.name.clone()));
                }
                Some(BackgroundEquipment::Gold) => {
                    out.push((b.gold_alternative, b.name.clone()));
                }
                None => {}
            }
        }
        out
    }

    /// The worn armor (the first non-shield armor carried) and whether a
    /// shield is carried.
    pub fn worn_armor<'a>(&self, data: &'a RulesData) -> Option<&'a ArmorRecord> {
        self.inventory(data)
            .iter()
            .filter_map(|c| data.armor(&c.item))
            .find(|a| !a.is_shield())
    }

    pub fn shield<'a>(&self, data: &'a RulesData) -> Option<&'a ArmorRecord> {
        self.inventory(data)
            .iter()
            .filter_map(|c| data.armor(&c.item))
            .find(|a| a.is_shield())
    }
}

// ---- Selection helpers ---------------------------------------------------

pub fn sel_single(selection: &Selection) -> Result<&OptionId, ApplyError> {
    match selection {
        Selection::Option(id) => Ok(id),
        _ => Err(ApplyError::new("expected a single option")),
    }
}

pub fn sel_multi(selection: &Selection) -> Result<&[OptionId], ApplyError> {
    match selection {
        Selection::Options(ids) => Ok(ids),
        _ => Err(ApplyError::new("expected a list of options")),
    }
}

pub fn sel_text(selection: &Selection) -> Result<&str, ApplyError> {
    match selection {
        Selection::Text(t) => Ok(t),
        _ => Err(ApplyError::new("expected text")),
    }
}

pub fn incomplete(
    slot: &str,
    step: &str,
    rule: &str,
    message: &str,
    source: &str,
) -> ChecklistEntry {
    ChecklistEntry {
        severity: ChecklistSeverity::Incomplete,
        slot: SlotId::new(slot),
        step: StepId::new(step),
        rule: rule.to_string(),
        message: message.to_string(),
        source: source.to_string(),
    }
}

pub fn illegal(slot: &str, step: &str, rule: &str, message: &str, source: &str) -> ChecklistEntry {
    ChecklistEntry {
        severity: ChecklistSeverity::Illegal,
        slot: SlotId::new(slot),
        step: StepId::new(step),
        rule: rule.to_string(),
        message: message.to_string(),
        source: source.to_string(),
    }
}

/// Render-ready display name for any record or synthetic option ID.
pub fn display_name(data: &RulesData, id: &OptionId) -> String {
    let s = id.as_str();
    if let Some((ability, value)) = parse_score_option(id) {
        return format!("{} {value}", ability.name());
    }
    if let Some(increase) = Increase::parse(id) {
        // The background is unknown here; render the pairs and a generic
        // all-one label.
        return match increase {
            Increase::TwoOne(a, b) => format!("{} +2, {} +1", a.name(), b.name()),
            Increase::AllOne => "+1 to each".to_string(),
        };
    }
    if s == BACKGROUND_EQUIPMENT_PACKAGE {
        return "equipment package".to_string();
    }
    if s == BACKGROUND_EQUIPMENT_GOLD {
        return "coin instead of the package".to_string();
    }
    if let Some(level) = s.strip_prefix("advance.") {
        return format!("Level {level}");
    }
    for c in &data.classes {
        if let Some(p) = c.equipment_packages.iter().find(|p| p.id == s) {
            return format!("{} package {}", c.name, p.label);
        }
        if c.gold_alternative.id == s {
            return format!("{} option {}", c.name, c.gold_alternative.label);
        }
    }
    for sp in &data.species {
        if let Some(t) = &sp.choice_trait {
            if let Some(o) = t.options.iter().find(|o| o.id == s) {
                return o.name.clone();
            }
        }
    }
    data.skill(s)
        .map(|r| r.name.clone())
        .or_else(|| data.score_method(s).map(|r| r.name.clone()))
        .or_else(|| data.species(s).map(|r| r.name.clone()))
        .or_else(|| data.background(s).map(|r| r.name.clone()))
        .or_else(|| data.feat(s).map(|r| r.name.clone()))
        .or_else(|| data.class(s).map(|r| r.name.clone()))
        .or_else(|| data.subclass(s).map(|r| r.name.clone()))
        .or_else(|| data.item_name(s))
        .unwrap_or_else(|| s.to_string())
}

pub fn describe_selection(data: &std::sync::Arc<RulesData>, selection: &Selection) -> String {
    match selection {
        Selection::Option(id) => display_name(data, id),
        Selection::Options(ids) => ids
            .iter()
            .map(|id| display_name(data, id))
            .collect::<Vec<_>>()
            .join(", "),
        Selection::Text(t) => {
            let t = t.trim();
            if t.chars().count() > 40 {
                format!("\"{}…\"", t.chars().take(40).collect::<String>())
            } else {
                format!("\"{t}\"")
            }
        }
    }
}

// ---- Step and slot IDs ----------------------------------------------------

/// The skill whose passive score the sheet carries (a record ID, resolved
/// to its name at render time).
pub const SKILL_PERCEPTION: &str = "skill.perception";

pub const STEP_CLASS: &str = "class";
pub const STEP_ORIGIN: &str = "origin";
pub const STEP_SCORES: &str = "scores";
pub const STEP_CLASS_CHOICES: &str = "class-choices";
pub const STEP_EQUIPMENT: &str = "equipment";
pub const STEP_DETAILS: &str = "details";

pub const SLOT_CLASS: &str = "dnd5e.class";
pub const SLOT_CLASS_SKILLS: &str = "dnd5e.class.skills";
pub const SLOT_CLASS_STYLE: &str = "dnd5e.class.style";
pub const SLOT_CLASS_MASTERIES: &str = "dnd5e.class.masteries";
pub const SLOT_BACKGROUND: &str = "dnd5e.background";
pub const SLOT_BACKGROUND_INCREASE: &str = "dnd5e.background.increase";
pub const SLOT_BACKGROUND_EQUIPMENT: &str = "dnd5e.background.equipment";
pub const SLOT_SPECIES: &str = "dnd5e.species";
pub const SLOT_SPECIES_SKILL: &str = "dnd5e.species.skill";
pub const SLOT_SPECIES_FEAT: &str = "dnd5e.species.feat";
pub const SLOT_SPECIES_ANCESTRY: &str = "dnd5e.species.ancestry";
pub const SLOT_SCORES_METHOD: &str = "dnd5e.scores.method";
pub const SLOT_SCORES_ASSIGN: &str = "dnd5e.scores.assign";
pub const SLOT_FEAT_SKILLED: &str = "dnd5e.feats.skilled";
pub const SLOT_EQUIPMENT_PACKAGE: &str = "dnd5e.equipment.package";
pub const SLOT_NAME: &str = "dnd5e.details.name";
pub const SLOT_DESCRIPTION: &str = "dnd5e.details.description";

/// The never-live step holding a level's advance slot.
pub fn step_level_advance(level: u32) -> String {
    format!("level-{level}-advance")
}
/// The rendered step for a pending level's choices.
pub fn step_level(level: u32) -> String {
    format!("level-{level}")
}
pub fn slot_level_advance(level: u32) -> String {
    format!("dnd5e.level.{level}.advance")
}
pub fn slot_level_subclass(level: u32) -> String {
    format!("dnd5e.level.{level}.subclass")
}
/// The level an advance slot ID advances to, if it is one.
pub fn advance_level_of(slot: &str) -> Option<u32> {
    slot.strip_prefix("dnd5e.level.")?
        .strip_suffix(".advance")?
        .parse()
        .ok()
}

// ---- Sheet derivation ------------------------------------------------------

fn entry(label: impl Into<String>, value: impl Into<String>, detail: Option<String>) -> SheetEntry {
    SheetEntry {
        label: label.into(),
        value: value.into(),
        detail,
    }
}

/// The ability a weapon attack uses and why: Ranged weapons use
/// Dexterity, Melee weapons Strength, and Finesse lets the better of the
/// two stand in.
fn attack_ability(weapon: &WeaponRecord, state: &Dnd5eState, data: &RulesData) -> Ability {
    let base = if weapon.is_ranged() {
        Ability::Dex
    } else {
        Ability::Str
    };
    if weapon.has_property("Finesse") {
        let (s, d) = (
            state.modifier(Ability::Str, data),
            state.modifier(Ability::Dex, data),
        );
        if d > s {
            Ability::Dex
        } else if s > d {
            Ability::Str
        } else {
            base
        }
    } else {
        base
    }
}

pub fn derive_sheet(state: &Dnd5eState, data: &RulesData) -> SheetView {
    let level = state.level();
    let pb = state.proficiency_bonus();
    let name = state.name.clone().unwrap_or_default();
    let species = state.species.as_ref().and_then(|id| data.species(id));
    let class = state.class.as_ref().and_then(|id| data.class(id));
    let subclass = state.subclass.as_ref().and_then(|id| data.subclass(id));
    let background = state.background.as_ref().and_then(|id| data.background(id));

    let mut summary = Vec::new();
    {
        let mut identity = String::new();
        if let Some(sp) = species {
            identity.push_str(&sp.name);
        }
        if let Some(c) = class {
            if !identity.is_empty() {
                identity.push(' ');
            }
            identity.push_str(&format!("{} {level}", c.name));
            if let Some(sc) = subclass {
                identity.push_str(&format!(" ({})", sc.name));
            }
        }
        if !identity.is_empty() {
            summary.push(identity);
        }
        if let Some(sp) = species {
            let mut line = format!("{} · Speed {} ft.", sp.size, effective_speed(state, data));
            if let Some(dv) = sp.darkvision {
                line.push_str(&format!(" · Darkvision {dv} ft."));
            }
            summary.push(line);
        }
    }

    let mut sections = Vec::new();

    // Ability scores: score and modifier, with the composition.
    let method_name = state
        .score_method
        .as_ref()
        .and_then(|id| data.score_method(id))
        .map(|m| m.name.clone());
    let increases = state.increases(data);
    let mut ability_entries = Vec::new();
    for ability in Ability::ALL {
        let base = state.base_score(ability);
        let score = state.score(ability, data);
        let mut parts = Vec::new();
        if let Some(b) = base {
            parts.push(format!(
                "{b} ({})",
                method_name.clone().unwrap_or_else(|| "assigned".into())
            ));
        }
        if let (Some(inc), Some(bg)) = (increases.get(&ability), background) {
            parts.push(format!("+{inc} ({})", bg.name));
        }
        let value = match score {
            Some(s) => format!("{s} ({})", format_signed(modifier_of(s))),
            None => "—".to_string(),
        };
        ability_entries.push(entry(
            ability.name(),
            value,
            if parts.is_empty() {
                Some("not yet assigned".into())
            } else {
                Some(parts.join(" "))
            },
        ));
    }
    sections.push(SheetSection {
        title: "Ability Scores".into(),
        entries: ability_entries,
    });

    // Combat.
    let con = state.modifier(Ability::Con, data);
    let dex = state.modifier(Ability::Dex, data);
    let mut combat = Vec::new();
    match class {
        Some(c) => {
            let mut hp = c.hp_at_level_1 as i32 + con;
            let mut detail = format!("{} + {con} Con", c.hp_at_level_1);
            if level > 1 {
                let per = c.hp_per_level as i32 + con;
                hp += per * (level as i32 - 1);
                detail.push_str(&format!(
                    " + {} × ({} + {con} Con)",
                    level - 1,
                    c.hp_per_level
                ));
            }
            if let Some(sp) = species.filter(|s| s.hp_bonus_per_level > 0) {
                let bonus = sp.hp_bonus_per_level * level;
                hp += bonus as i32;
                detail.push_str(&format!(" + {bonus} ({})", sp.name));
            }
            combat.push(entry("Hit Points", hp.max(1).to_string(), Some(detail)));
        }
        None => combat.push(entry("Hit Points", "—", Some("choose a class".into()))),
    }
    combat.push(armor_class_entry(state, data));
    {
        let mut init = dex;
        let mut parts = vec![format!("{dex} Dex")];
        if state.has_effect(data, |e| *e == Effect::InitiativeProficiency) {
            init += pb;
            let feat = state
                .feats(data)
                .into_iter()
                .find(|(id, _, _)| {
                    data.feat(id)
                        .is_some_and(|f| f.effects.contains(&Effect::InitiativeProficiency))
                })
                .map(|(_, _, name)| name)
                .unwrap_or_default();
            parts.push(format!("+{pb} proficiency ({feat})"));
        }
        combat.push(entry(
            "Initiative",
            format_signed(init),
            Some(parts.join(", ")),
        ));
    }
    {
        let (speed, detail) = speed_with_detail(state, data);
        combat.push(entry("Speed", format!("{speed} ft."), detail));
    }
    combat.push(entry(
        "Proficiency Bonus",
        format_signed(pb),
        Some(format!("level {level}")),
    ));
    if let Some(c) = class {
        combat.push(entry(
            "Hit Dice",
            format!("{level}d{}", c.hit_die),
            Some(format!("d{} per {} level", c.hit_die, c.name)),
        ));
    }
    if let Some(perception) = data.skill(SKILL_PERCEPTION) {
        let (bonus, detail) = skill_bonus(state, data, &perception.id);
        combat.push(entry(
            format!("Passive {}", perception.name),
            (10 + bonus).to_string(),
            Some(format!("10 + {}", detail)),
        ));
    }
    sections.push(SheetSection {
        title: "Combat".into(),
        entries: combat,
    });

    // Saving throws.
    let mut saves = Vec::new();
    for ability in Ability::ALL {
        let m = state.modifier(ability, data);
        let proficient = class.is_some_and(|c| c.saving_throws.contains(&ability));
        let total = if proficient { m + pb } else { m };
        let detail = if proficient {
            format!(
                "{m} {} + {pb} proficiency (from {})",
                ability.abbrev(),
                class.map(|c| c.name.as_str()).unwrap_or_default()
            )
        } else {
            format!("{m} {}", ability.abbrev())
        };
        saves.push(entry(ability.name(), format_signed(total), Some(detail)));
    }
    sections.push(SheetSection {
        title: "Saving Throws".into(),
        entries: saves,
    });

    // Skills: all eighteen, proficient ones marked with their source.
    let mut skills = Vec::new();
    for skill in &data.skills {
        let (bonus, detail) = skill_bonus(state, data, &skill.id);
        skills.push(entry(&skill.name, format_signed(bonus), Some(detail)));
    }
    sections.push(SheetSection {
        title: "Skills".into(),
        entries: skills,
    });

    // Attacks: one per carried weapon; empty when nothing is carried.
    sections.push(SheetSection {
        title: "Attacks".into(),
        entries: attack_entries(state, data),
    });

    // Features.
    sections.push(SheetSection {
        title: "Features".into(),
        entries: feature_entries(state, data),
    });

    // Equipment.
    sections.push(SheetSection {
        title: "Equipment".into(),
        entries: equipment_entries(state, data),
    });

    SheetView {
        name,
        summary,
        sections,
    }
}

/// The species' Speed, reduced by 10 when worn heavy armor's Strength
/// requirement is unmet.
fn speed_with_detail(state: &Dnd5eState, data: &RulesData) -> (i32, Option<String>) {
    let species = state.species.as_ref().and_then(|id| data.species(id));
    let base = species.map(|s| s.speed).unwrap_or(30);
    let mut detail = species.map(|s| s.name.clone());
    let mut speed = base;
    if let Some(armor) = state.worn_armor(data) {
        if let Some(req) = armor.strength_requirement {
            let str_score = state.score(Ability::Str, data).unwrap_or(10);
            if str_score < req {
                speed -= 10;
                detail = Some(format!(
                    "{} − 10 ({} requires Strength {req})",
                    detail.unwrap_or_default(),
                    armor.name
                ));
            }
        }
    }
    (speed, detail)
}

fn effective_speed(state: &Dnd5eState, data: &RulesData) -> i32 {
    speed_with_detail(state, data).0
}

fn armor_class_entry(state: &Dnd5eState, data: &RulesData) -> SheetEntry {
    let dex = state.modifier(Ability::Dex, data);
    let class = state.class.as_ref().and_then(|id| data.class(id));
    let mut ac;
    let mut parts = Vec::new();
    match state.worn_armor(data) {
        Some(armor) => {
            ac = armor.base_ac;
            parts.push(format!("{} ({})", armor.base_ac, armor.name));
            if armor.add_dex {
                let applied = match armor.dex_max {
                    Some(max) => dex.min(max),
                    None => dex,
                };
                ac += applied;
                parts.push(match armor.dex_max {
                    Some(max) => format!("{applied} Dex (max {max})"),
                    None => format!("{applied} Dex"),
                });
            }
            if class.is_some_and(|c| !c.is_trained_with_armor(armor)) {
                parts.push("(not trained with this armor)".into());
            }
            for (id, _, name) in state.feats(data) {
                if let Some(feat) = data.feat(&id) {
                    for effect in &feat.effects {
                        if let Effect::ArmorClassBonusArmored { bonus } = effect {
                            ac += bonus;
                            parts.push(format!("{} ({name})", format_signed(*bonus)));
                        }
                    }
                }
            }
        }
        None => {
            ac = 10 + dex;
            parts.push(format!("10 + {dex} Dex (unarmored)"));
        }
    }
    if let Some(shield) = state.shield(data) {
        if class.is_none_or(|c| c.is_trained_with_armor(shield)) {
            ac += shield.base_ac;
            parts.push(format!("+{} ({})", shield.base_ac, shield.name));
        }
    }
    entry("Armor Class", ac.to_string(), Some(parts.join(" ")))
}

/// A skill's total bonus and its render-ready breakdown.
fn skill_bonus(state: &Dnd5eState, data: &RulesData, skill_id: &str) -> (i32, String) {
    let Some(skill) = data.skill(skill_id) else {
        return (0, String::new());
    };
    let m = state.modifier(skill.ability, data);
    let pb = state.proficiency_bonus();
    let owner = state
        .skill_proficiencies(data)
        .into_iter()
        .find(|p| p.id == skill_id);
    match owner {
        Some(p) => (
            m + pb,
            format!(
                "{m} {} + {pb} proficiency (from {})",
                skill.ability.abbrev(),
                p.source
            ),
        ),
        None => (m, format!("{m} {}", skill.ability.abbrev())),
    }
}

fn attack_entries(state: &Dnd5eState, data: &RulesData) -> Vec<SheetEntry> {
    let class = state.class.as_ref().and_then(|id| data.class(id));
    let pb = state.proficiency_bonus();
    let ranged_bonus: i32 = state
        .effects(data)
        .iter()
        .filter_map(|e| match e {
            Effect::RangedAttackBonus { bonus } => Some(*bonus),
            _ => None,
        })
        .sum();
    let mut seen: Vec<String> = Vec::new();
    let mut out = Vec::new();
    for carried in state.inventory(data) {
        let Some(weapon) = data.weapon(&carried.item) else {
            continue;
        };
        if seen.contains(&weapon.id) {
            continue;
        }
        seen.push(weapon.id.clone());
        let ability = attack_ability(weapon, state, data);
        let m = state.modifier(ability, data);
        let proficient = class.is_some_and(|c| c.is_proficient_with_weapon(weapon));
        let mut attack = m;
        let mut parts = vec![format!("{m} {}", ability.abbrev())];
        if proficient {
            attack += pb;
            parts.push(format!("+{pb} proficiency"));
        }
        if weapon.is_ranged() && ranged_bonus != 0 {
            attack += ranged_bonus;
            parts.push(format!("{} ranged", format_signed(ranged_bonus)));
        }
        let dmg_mod = if m != 0 {
            format_signed(m)
        } else {
            String::new()
        };
        let mut damage = format!("{}{dmg_mod} {}", weapon.damage, weapon.damage_type);
        if let Some(v) = &weapon.versatile_damage {
            damage.push_str(&format!(" ({v}{dmg_mod} two-handed)"));
        }
        let mut detail = parts.join(", ");
        if !weapon.properties.is_empty() {
            detail.push_str(&format!("; {}", weapon.properties.join(", ")));
        }
        if let Some(r) = &weapon.range {
            detail.push_str(&format!(" (range {r})"));
        }
        let chosen = state.masteries.contains(&weapon.id);
        detail.push_str(&format!(
            "; mastery: {}{}",
            weapon.mastery,
            if chosen { " (chosen)" } else { "" }
        ));
        if carried.count > 1 {
            detail.push_str(&format!("; ×{}", carried.count));
        }
        out.push(entry(
            &weapon.name,
            format!("{} · {damage}", format_signed(attack)),
            Some(detail),
        ));
    }
    out
}

fn feature_entries(state: &Dnd5eState, data: &RulesData) -> Vec<SheetEntry> {
    let level = state.level();
    let class = state.class.as_ref().and_then(|id| data.class(id));
    let mut out = Vec::new();
    if let Some(c) = class {
        for f in &c.features {
            let (value, detail) = if c.fighting_style_feature.as_deref() == Some(f.id.as_str()) {
                match state.fighting_style.as_ref().and_then(|id| data.feat(id)) {
                    Some(feat) => (feat.name.clone(), format!("{} — {}", feat.text, f.text)),
                    None => ("not yet chosen".to_string(), f.text.clone()),
                }
            } else if c.weapon_mastery_feature.as_deref() == Some(f.id.as_str()) {
                let chosen: Vec<String> = state
                    .masteries
                    .iter()
                    .filter_map(|id| data.weapon(id))
                    .map(|w| format!("{} ({})", w.name, w.mastery))
                    .collect();
                (
                    if chosen.is_empty() {
                        "not yet chosen".to_string()
                    } else {
                        chosen.join(", ")
                    },
                    f.text.clone(),
                )
            } else {
                (format!("{} 1", c.name), f.text.clone())
            };
            out.push(entry(&f.name, value, Some(detail)));
        }
        for (lvl, id) in &state.granted_features {
            if let Some(f) = c.feature(id) {
                out.push(entry(
                    &f.name,
                    format!("{} {lvl}", c.name),
                    Some(f.text.clone()),
                ));
            }
        }
    }
    if let Some(sc) = state.subclass.as_ref().and_then(|id| data.subclass(id)) {
        for f in sc.features.iter().filter(|f| f.level <= level) {
            out.push(entry(
                &f.name,
                format!("{} {}", sc.name, f.level),
                Some(f.text.clone()),
            ));
        }
    }
    if let Some(sp) = state.species.as_ref().and_then(|id| data.species(id)) {
        for t in &sp.traits {
            out.push(entry(&t.name, sp.name.clone(), Some(t.text.clone())));
        }
        if let Some(ct) = &sp.choice_trait {
            let chosen = state
                .species_ancestry
                .as_ref()
                .and_then(|id| ct.options.iter().find(|o| &o.id == id));
            match chosen {
                Some(o) => out.push(entry(
                    &ct.name,
                    o.name.clone(),
                    Some(format!("{} {}", ct.text, o.text)),
                )),
                None => out.push(entry(&ct.name, "not yet chosen", Some(ct.text.clone()))),
            }
        }
    }
    for (id, source, display) in state.feats(data) {
        let Some(feat) = data.feat(&id) else {
            continue;
        };
        if feat.is_fighting_style() {
            // Rendered under the class's Fighting Style feature above.
            continue;
        }
        let mut value = format!("origin feat from {source}");
        if feat.effects.contains(&Effect::SpellChoicesUnsupported) {
            value.push_str(" · spell choices not yet supported");
        }
        if feat.skill_or_tool_choices() > 0 {
            let picks: Vec<String> = state
                .skilled_picks
                .iter()
                .map(|p| {
                    data.skill(p)
                        .map(|s| s.name.clone())
                        .or_else(|| data.tool(p).map(|t| t.name.clone()))
                        .unwrap_or_else(|| p.clone())
                })
                .collect();
            if !picks.is_empty() {
                value.push_str(&format!(" · {}", picks.join(", ")));
            }
        }
        out.push(entry(display, value, Some(feat.text.clone())));
    }
    if let Some(b) = state.background.as_ref().and_then(|id| data.background(id)) {
        let tool = data
            .tool(&b.tool)
            .map(|t| t.name.clone())
            .unwrap_or_default();
        out.push(entry(
            "Tool Proficiency",
            tool,
            Some(format!("from {}", b.name)),
        ));
    }
    let feat_tools: Vec<String> = state
        .tool_proficiencies(data)
        .into_iter()
        .filter(|p| {
            state
                .background
                .as_ref()
                .and_then(|id| data.background(id))
                .is_none_or(|b| b.tool != p.id)
        })
        .filter_map(|p| {
            data.tool(&p.id)
                .map(|t| format!("{} (from {})", t.name, p.source))
        })
        .collect();
    if !feat_tools.is_empty() {
        out.push(entry(
            "Additional Tool Proficiencies",
            feat_tools.join(", "),
            None,
        ));
    }
    out
}

fn equipment_entries(state: &Dnd5eState, data: &RulesData) -> Vec<SheetEntry> {
    let mut out = Vec::new();
    let mut total = 0.0;
    let worn = state.worn_armor(data).map(|a| a.id.clone());
    for carried in state.inventory(data) {
        let Some(weight) = data.item_weight(&carried.item) else {
            continue;
        };
        let name = data.item_name(&carried.item).unwrap_or_default();
        let line_weight = weight * carried.count as f64;
        total += line_weight;
        let label = if carried.count > 1 {
            format!("{name} ×{}", carried.count)
        } else {
            name
        };
        let kind = if let Some(w) = data.weapon(&carried.item) {
            format!("{} {} weapon", w.category, w.kind)
        } else if let Some(a) = data.armor(&carried.item) {
            if a.is_shield() {
                "shield".to_string()
            } else if worn.as_deref() == Some(a.id.as_str()) {
                format!("{} armor (worn)", a.category)
            } else {
                format!("{} armor", a.category)
            }
        } else if data.tool(&carried.item).is_some() {
            "tool".to_string()
        } else {
            "gear".to_string()
        };
        out.push(entry(
            label,
            format_weight(line_weight),
            Some(format!("{kind}; from {}", carried.source)),
        ));
    }
    let str_score = state.score(Ability::Str, data).unwrap_or(10);
    let species = state.species.as_ref().and_then(|id| data.species(id));
    let multiplier = if species.is_some_and(|s| s.powerful_build) {
        30
    } else {
        15
    };
    let capacity = str_score * multiplier;
    out.push(entry(
        "Total Weight",
        format_weight(total),
        Some(format!(
            "carrying capacity {} (Strength {str_score} × {multiplier}{})",
            format_weight(capacity as f64),
            if multiplier == 30 {
                ", one size larger"
            } else {
                ""
            }
        )),
    ));
    let coin = state.coin(data);
    let gp: u32 = coin.iter().map(|(g, _)| *g).sum();
    out.push(entry(
        "Coin",
        format_gp(gp),
        if coin.is_empty() {
            None
        } else {
            Some(
                coin.iter()
                    .map(|(g, s)| format!("{} from {s}", format_gp(*g)))
                    .collect::<Vec<_>>()
                    .join(" + "),
            )
        },
    ));
    out
}
