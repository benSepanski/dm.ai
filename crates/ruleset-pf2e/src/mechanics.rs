//! Shared PF2e mechanics: attribute/boost arithmetic, proficiency math,
//! money and Bulk, the folded character state, and sheet derivation.
//! Kind modules depend on this; this module never references a kind.

use std::collections::BTreeMap;

use serde::Deserialize;
use types::{OptionId, SheetEntry, SheetSection, SheetView};

use crate::data::{Effect, RulesData};

/// The six attributes. Remaster arithmetic is modifier-only: a boost is +1
/// to the modifier, a flaw is -1.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Attribute {
    Str,
    Dex,
    Con,
    Int,
    Wis,
    Cha,
}

pub const ALL_ATTRIBUTES: [Attribute; 6] = [
    Attribute::Str,
    Attribute::Dex,
    Attribute::Con,
    Attribute::Int,
    Attribute::Wis,
    Attribute::Cha,
];

impl Attribute {
    pub fn name(self) -> &'static str {
        match self {
            Attribute::Str => "Strength",
            Attribute::Dex => "Dexterity",
            Attribute::Con => "Constitution",
            Attribute::Int => "Intelligence",
            Attribute::Wis => "Wisdom",
            Attribute::Cha => "Charisma",
        }
    }
    pub fn abbrev(self) -> &'static str {
        match self {
            Attribute::Str => "Str",
            Attribute::Dex => "Dex",
            Attribute::Con => "Con",
            Attribute::Int => "Int",
            Attribute::Wis => "Wis",
            Attribute::Cha => "Cha",
        }
    }
    pub fn option_id(self) -> OptionId {
        OptionId::new(format!("attr.{}", self.abbrev().to_lowercase()))
    }
    pub fn from_option_id(id: &OptionId) -> Option<Attribute> {
        ALL_ATTRIBUTES.into_iter().find(|a| a.option_id() == *id)
    }
}

/// Proficiency ranks; bonus is rank value + level when trained or better.
/// Ordered Untrained < Trained < Expert < Master < Legendary so overrides
/// can take a max.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Proficiency {
    Untrained,
    Trained,
    Expert,
    Master,
    Legendary,
}

impl Proficiency {
    pub fn parse(s: &str) -> Proficiency {
        match s {
            "trained" => Proficiency::Trained,
            "expert" => Proficiency::Expert,
            "master" => Proficiency::Master,
            "legendary" => Proficiency::Legendary,
            _ => Proficiency::Untrained,
        }
    }
    pub fn bonus(self, level: i32) -> i32 {
        match self {
            Proficiency::Untrained => 0,
            Proficiency::Trained => level + 2,
            Proficiency::Expert => level + 4,
            Proficiency::Master => level + 6,
            Proficiency::Legendary => level + 8,
        }
    }
    pub fn label(self) -> &'static str {
        match self {
            Proficiency::Untrained => "untrained",
            Proficiency::Trained => "trained",
            Proficiency::Expert => "expert",
            Proficiency::Master => "master",
            Proficiency::Legendary => "legendary",
        }
    }
}

pub fn format_signed(n: i32) -> String {
    if n >= 0 {
        format!("+{n}")
    } else {
        format!("{n}")
    }
}

/// Coin arithmetic in copper pieces.
pub const STARTING_WEALTH_CP: i64 = 1500;

pub fn format_cp(cp: i64) -> String {
    let negative = cp < 0;
    let cp = cp.abs();
    let gp = cp / 100;
    let sp = (cp % 100) / 10;
    let rem = cp % 10;
    let mut parts = Vec::new();
    if gp > 0 {
        parts.push(format!("{gp} gp"));
    }
    if sp > 0 {
        parts.push(format!("{sp} sp"));
    }
    if rem > 0 || parts.is_empty() {
        parts.push(format!("{rem} cp"));
    }
    let joined = parts.join(", ");
    if negative {
        format!("-{joined}")
    } else {
        joined
    }
}

/// Bulk in tenths: "L" = 1, "2" = 20, "-"/"" = 0.
pub fn bulk_tenths(bulk: &str) -> i64 {
    match bulk.trim() {
        "L" | "l" => 1,
        "-" | "—" | "" => 0,
        n => n.parse::<i64>().map(|v| v * 10).unwrap_or(0),
    }
}

pub fn format_bulk_tenths(tenths: i64) -> String {
    let whole = tenths / 10;
    let light = tenths % 10;
    match (whole, light) {
        (0, 0) => "—".to_string(),
        (0, l) => format!("{l} L"),
        (w, 0) => format!("{w} Bulk"),
        (w, l) => format!("{w} Bulk, {l} L"),
    }
}

/// A fixed skill-training grant (background skill, Lore-feat skills).
#[derive(Debug, Clone)]
pub struct SkillGrant {
    pub skill: String,
    pub source: String,
}

/// A player-chosen set of skills (class picks, chooser slots).
#[derive(Debug, Clone)]
pub struct SkillChoice {
    pub slot: &'static str,
    pub source: String,
    pub skills: Vec<String>,
}

/// The folded PF2e character state. Kind modules write their slices during
/// the fold; mechanics reads the whole to derive the sheet.
#[derive(Debug, Clone, Default)]
pub struct Pf2eState {
    pub ancestry: Option<String>,
    pub heritage: Option<String>,
    pub ancestry_feat: Option<String>,
    pub background: Option<String>,
    /// The skill picked in the background's sub-choice slot, when its
    /// background offers one (Scholar pattern). Also steers the
    /// choice-dependent skill feat on the sheet.
    pub background_skill_choice: Option<String>,
    pub class: Option<String>,
    /// The chosen class's display name, resolved from its record at apply
    /// time — every source label derives from this, never from a literal.
    pub class_name: Option<String>,
    pub key_attribute: Option<Attribute>,
    pub class_feat: Option<String>,

    /// Spellcasting build choices (the Wizard).
    pub thesis: Option<String>,
    pub school: Option<String>,
    pub spellbook_cantrips: Vec<String>,
    pub spellbook_rank1: Vec<String>,

    /// Boosts by batch; duplicates within a batch are recorded as picked
    /// (validators flag them) but count once toward the modifier.
    pub boost_batches: BTreeMap<String, Vec<Attribute>>,
    pub flaws: Vec<Attribute>,

    /// Fixed grants in canonical precedence order (background before feats).
    pub skill_grants: Vec<SkillGrant>,
    pub skill_choices: Vec<SkillChoice>,
    pub class_skill_choice: Option<String>,
    pub lores: Vec<(String, String)>,

    /// Feats chosen through catalog choosers (general feats, bonus class
    /// feats), in pick order.
    pub chosen_general_feats: Vec<String>,
    pub bonus_class_feats: Vec<String>,

    /// Bonus languages picked in the ancestry-language chooser, in pick
    /// order (display names from the ancestry's additional_languages).
    pub chosen_languages: Vec<String>,

    /// Mechanical effects collected from heritage/feat records.
    pub effects: Vec<Effect>,

    /// Equipment: chosen kit option (kit id, option id) and itemized extras.
    pub kit: Option<(String, Option<String>)>,
    pub extra_items: Vec<String>,

    pub name: Option<String>,
    pub concept: Option<String>,
    pub description: Option<String>,
}

impl Pf2eState {
    pub fn modifier(&self, attr: Attribute) -> i32 {
        let mut m = 0;
        for batch in self.boost_batches.values() {
            let mut distinct: Vec<Attribute> = batch.clone();
            distinct.sort();
            distinct.dedup();
            if distinct.contains(&attr) {
                m += 1;
            }
        }
        m - self.flaws.iter().filter(|f| **f == attr).count() as i32
    }

    /// Trained skills under the ownership policy: **fixed grants own a
    /// skill and its attribution; player picks flex around them.** Grants
    /// resolve first, so a sheet always names the granting source. A grant
    /// (or the class skill) landing on an already-trained skill converts
    /// into one extra free trained pick — the printed "select another
    /// skill instead" rule — while a free/chooser pick landing on an
    /// owned skill is the player's to re-judge in place.
    pub fn skill_resolution(&self) -> SkillResolution {
        let mut trained: Vec<(String, String)> = Vec::new();
        let mut extra_free_picks: Vec<String> = Vec::new();
        let mut illegal_choice_dupes: Vec<(&'static str, String, String)> = Vec::new();

        for grant in &self.skill_grants {
            if trained.iter().any(|(t, _)| t == &grant.skill) {
                extra_free_picks.push(grant.source.clone());
            } else {
                trained.push((grant.skill.clone(), grant.source.clone()));
            }
        }
        if let Some(s) = &self.class_skill_choice {
            let source = self.class_name.clone().unwrap_or_else(|| "Class".into());
            if trained.iter().any(|(t, _)| t == s) {
                extra_free_picks.push(source);
            } else {
                trained.push((s.clone(), source));
            }
        }
        for choice in &self.skill_choices {
            for s in &choice.skills {
                if let Some((_, owner)) = trained.iter().find(|(t, _)| t == s) {
                    illegal_choice_dupes.push((choice.slot, s.clone(), owner.clone()));
                } else {
                    trained.push((s.clone(), choice.source.clone()));
                }
            }
        }
        SkillResolution {
            trained,
            extra_free_picks,
            illegal_choice_dupes,
        }
    }

    pub fn has_effect(&self, pred: impl Fn(&Effect) -> bool) -> bool {
        self.effects.iter().any(pred)
    }

    /// Trained (or better) in the given skill ID under the folded state.
    /// At level 1 every skill rank above untrained is exactly trained, so
    /// membership in the resolution is the whole check.
    pub fn is_trained(&self, skill: &str) -> bool {
        self.skill_resolution()
            .trained
            .iter()
            .any(|(id, _)| id == skill)
    }

    /// The ancestry-language chooser's current pick count:
    /// max(0, Int modifier) plus every bonus-language effect.
    pub fn language_count(&self) -> u32 {
        let int = self.modifier(Attribute::Int).max(0) as u32;
        let bonus: u32 = self
            .effects
            .iter()
            .map(|e| match e {
                Effect::BonusLanguages { count } => *count,
                _ => 0,
            })
            .sum();
        int + bonus
    }
}

pub struct SkillResolution {
    /// (skill id, source label), grants first (they own attribution).
    pub trained: Vec<(String, String)>,
    /// One extra free trained pick per entry — a grant or the class skill
    /// that landed on an already-trained skill (the printed "select
    /// another skill instead" rule). Entries name the redundant source.
    pub extra_free_picks: Vec<String>,
    /// A free or chooser pick landing on an owned skill, the player's to
    /// re-judge in place: (slot id, skill id, owning source label).
    pub illegal_choice_dupes: Vec<(&'static str, String, String)>,
}

/// Everything owned, derived from kit + extras: (item id, source label).
pub fn inventory(state: &Pf2eState, data: &RulesData) -> Vec<(String, String)> {
    let mut items = Vec::new();
    if let Some((kit_id, option)) = &state.kit {
        if let Some(kit) = data.kit(kit_id) {
            for item in &kit.contents {
                items.push((item.clone(), kit.name.clone()));
            }
            if let Some(option_id) = option {
                if let Some(opt) = kit.options.iter().find(|o| o.id == *option_id) {
                    for item in &opt.items {
                        items.push((item.clone(), kit.name.clone()));
                    }
                }
            }
        }
    }
    for item in &state.extra_items {
        items.push((item.clone(), "purchased".to_string()));
    }
    items
}

/// Total spend in cp (kit price + option price + extras).
pub fn total_spend_cp(state: &Pf2eState, data: &RulesData) -> i64 {
    let mut spend: i64 = 0;
    if let Some((kit_id, option)) = &state.kit {
        if let Some(kit) = data.kit(kit_id) {
            spend += kit.price_cp as i64;
            if let Some(option_id) = option {
                if let Some(opt) = kit.options.iter().find(|o| o.id == *option_id) {
                    spend += opt.price_cp as i64;
                }
            }
        }
    }
    for item in &state.extra_items {
        spend += item_price_cp(item, data);
    }
    spend
}

pub fn item_price_cp(id: &str, data: &RulesData) -> i64 {
    let e = &data.equipment;
    e.weapons
        .iter()
        .find(|r| r.id == id)
        .map(|r| r.price_cp as i64)
        .or_else(|| {
            e.armor
                .iter()
                .find(|r| r.id == id)
                .map(|r| r.price_cp as i64)
        })
        .or_else(|| {
            e.shields
                .iter()
                .find(|r| r.id == id)
                .map(|r| r.price_cp as i64)
        })
        .or_else(|| {
            e.gear
                .iter()
                .find(|r| r.id == id)
                .map(|r| r.price_cp as i64)
        })
        .unwrap_or(0)
}

pub fn item_name(id: &str, data: &RulesData) -> String {
    let e = &data.equipment;
    e.weapons
        .iter()
        .find(|r| r.id == id)
        .map(|r| r.name.clone())
        .or_else(|| e.armor.iter().find(|r| r.id == id).map(|r| r.name.clone()))
        .or_else(|| {
            e.shields
                .iter()
                .find(|r| r.id == id)
                .map(|r| r.name.clone())
        })
        .or_else(|| e.gear.iter().find(|r| r.id == id).map(|r| r.name.clone()))
        .unwrap_or_else(|| id.to_string())
}

const LEVEL: i32 = 1;

/// Derive the presentation-contract sheet from the folded state. Pure.
pub fn derive_sheet(state: &Pf2eState, data: &RulesData) -> SheetView {
    let name = state.name.clone().unwrap_or_default();
    let ancestry = state.ancestry.as_ref().and_then(|id| data.ancestry(id));
    let heritage = state.heritage.as_ref().and_then(|id| data.heritage(id));
    let class = state.class.as_ref().and_then(|id| data.class(id));

    let mut summary = Vec::new();
    {
        let mut identity = String::new();
        if let Some(a) = ancestry {
            identity.push_str(&a.name);
            if let Some(h) = heritage {
                identity = format!("{} ({})", identity, h.name);
            }
        }
        if let Some(c) = class {
            if !identity.is_empty() {
                identity.push(' ');
            }
            identity.push_str(&format!("{} {LEVEL}", c.name));
        }
        if !identity.is_empty() {
            summary.push(identity);
        }
        if let Some(a) = ancestry {
            let senses = a.senses_with_effects(state);
            summary.push(format!(
                "{} · Speed {} feet{}",
                capitalize(&a.size),
                effective_speed(state, data),
                if senses.is_empty() {
                    String::new()
                } else {
                    format!(" · {senses}")
                }
            ));
        }
    }

    let mut sections = Vec::new();

    // Attributes.
    let mut attr_entries = Vec::new();
    for attr in ALL_ATTRIBUTES {
        let m = state.modifier(attr);
        let mut parts: Vec<String> = Vec::new();
        for (batch, boosts) in &state.boost_batches {
            let mut distinct = boosts.clone();
            distinct.sort();
            distinct.dedup();
            if distinct.contains(&attr) {
                parts.push(format!("+1 {}", batch_label(batch)));
            }
        }
        if state.flaws.contains(&attr) {
            parts.push("-1 ancestry flaw".to_string());
        }
        attr_entries.push(SheetEntry {
            label: attr.name().to_string(),
            value: format_signed(m),
            detail: if parts.is_empty() {
                None
            } else {
                Some(parts.join(", "))
            },
        });
    }
    sections.push(SheetSection {
        title: "Attributes".to_string(),
        entries: attr_entries,
    });

    // Defense & vitals.
    if let Some(c) = class {
        let con = state.modifier(Attribute::Con);
        let dex = state.modifier(Attribute::Dex);
        let wis = state.modifier(Attribute::Wis);
        let str_ = state.modifier(Attribute::Str);

        let ancestry_hp = ancestry.map(|a| a.hp).unwrap_or(0);
        let ancestry_hp = state
            .effects
            .iter()
            .find_map(|e| match e {
                Effect::AncestryHpOverride { value } => Some(*value),
                _ => None,
            })
            .unwrap_or(ancestry_hp);
        let bonus_hp: i32 = state
            .effects
            .iter()
            .map(|e| match e {
                Effect::HpPerLevel { value } => *value as i32 * LEVEL,
                _ => 0,
            })
            .sum();
        let hp = ancestry_hp as i32 + c.hp_per_level as i32 + con * LEVEL + bonus_hp;
        let mut hp_detail = format!(
            "{ancestry_hp} ancestry + {} class + {con} Con",
            c.hp_per_level
        );
        if bonus_hp != 0 {
            hp_detail.push_str(&format!(" + {bonus_hp} Toughness"));
        }

        let worn = worn_armor(state, data);
        let (ac, ac_detail) = match worn {
            Some(armor) => {
                let prof = Proficiency::parse(&c.proficiencies.armor).bonus(LEVEL);
                let dex_used = dex.min(armor.dex_cap);
                (
                    10 + dex_used + armor.ac_bonus + prof,
                    format!(
                        "10 + {} Dex (cap {}) + {} {} + {} {} armor prof",
                        dex_used,
                        format_signed(armor.dex_cap),
                        armor.ac_bonus,
                        armor.name,
                        prof,
                        Proficiency::parse(&c.proficiencies.armor).label()
                    ),
                )
            }
            None => {
                let prof = Proficiency::parse(&c.proficiencies.unarmored_defense).bonus(LEVEL);
                (
                    10 + dex + prof,
                    format!(
                        "10 + {dex} Dex + {prof} {} unarmored",
                        Proficiency::parse(&c.proficiencies.unarmored_defense).label()
                    ),
                )
            }
        };

        // A proficiency-override effect (Canny Acumen) sets a save or
        // Perception to a named rank; derivation takes max(class rank,
        // override) so an override never lowers anything.
        let effective_rank = |class_rank: &str, target: &str| -> Proficiency {
            state
                .effects
                .iter()
                .filter_map(|e| match e {
                    Effect::ProficiencyOverride { target: t, rank } if t == target => {
                        Some(Proficiency::parse(rank))
                    }
                    _ => None,
                })
                .fold(Proficiency::parse(class_rank), Proficiency::max)
        };
        let save = |p: Proficiency, attr_mod: i32, attr: &str| -> (String, String) {
            let total = p.bonus(LEVEL) + attr_mod;
            (
                format_signed(total),
                format!("{} {} + {} {}", p.bonus(LEVEL), p.label(), attr_mod, attr),
            )
        };
        let (fort, fort_d) = save(
            effective_rank(&c.proficiencies.fortitude, "fortitude"),
            con,
            "Con",
        );
        let (refl, refl_d) = save(
            effective_rank(&c.proficiencies.reflex, "reflex"),
            dex,
            "Dex",
        );
        let (will, will_d) = save(effective_rank(&c.proficiencies.will, "will"), wis, "Wis");
        let (perc, perc_d) = save(
            effective_rank(&c.proficiencies.perception, "perception"),
            wis,
            "Wis",
        );
        let class_dc = 10
            + Proficiency::parse(&c.proficiencies.class_dc).bonus(LEVEL)
            + state.key_attribute.map(|a| state.modifier(a)).unwrap_or(0);

        let mut entries = vec![
            SheetEntry {
                label: "Hit Points".into(),
                value: hp.to_string(),
                detail: Some(hp_detail),
            },
            SheetEntry {
                label: "Armor Class".into(),
                value: ac.to_string(),
                detail: Some(ac_detail),
            },
            SheetEntry {
                label: "Fortitude".into(),
                value: fort,
                detail: Some(fort_d),
            },
            SheetEntry {
                label: "Reflex".into(),
                value: refl,
                detail: Some(refl_d),
            },
            SheetEntry {
                label: "Will".into(),
                value: will,
                detail: Some(will_d),
            },
            SheetEntry {
                label: "Perception".into(),
                value: perc,
                detail: Some(format!("{perc_d} (initiative)")),
            },
        ];
        if state.key_attribute.is_some() {
            entries.push(SheetEntry {
                label: "Class DC".into(),
                value: class_dc.to_string(),
                detail: Some(format!(
                    "10 + {} trained + {} {}",
                    Proficiency::parse(&c.proficiencies.class_dc).bonus(LEVEL),
                    state.key_attribute.map(|a| state.modifier(a)).unwrap_or(0),
                    state
                        .key_attribute
                        .map(|a| a.abbrev())
                        .unwrap_or("key attribute")
                )),
            });
        }
        let _ = str_;
        sections.push(SheetSection {
            title: "Defense".to_string(),
            entries,
        });

        // Attacks.
        sections.push(SheetSection {
            title: "Attacks".to_string(),
            entries: attack_entries(state, data, c),
        });

        // Skills.
        sections.push(SheetSection {
            title: "Skills".to_string(),
            entries: skill_entries(state, data, c),
        });
    }

    // Features.
    let mut features = Vec::new();
    if let Some(a) = ancestry {
        for s in &a.specials {
            features.push(SheetEntry {
                label: s.name.clone(),
                value: format!("{} ancestry", a.name),
                detail: Some(s.text.clone()),
            });
        }
    }
    if let Some(h) = heritage {
        features.push(SheetEntry {
            label: h.name.clone(),
            value: "heritage".into(),
            detail: Some(h.text.clone()),
        });
    }
    if let Some(f) = state
        .ancestry_feat
        .as_ref()
        .and_then(|id| data.ancestry_feat(id))
    {
        features.push(SheetEntry {
            label: f.name.clone(),
            value: "ancestry feat".into(),
            detail: Some(f.text.clone()),
        });
    }
    if let Some(c) = class {
        for feature in &c.features {
            features.push(SheetEntry {
                label: feature.name.clone(),
                value: format!("{} feature", c.name),
                detail: Some(feature.text.clone()),
            });
        }
    }
    if let Some(f) = state.class_feat.as_ref().and_then(|id| data.class_feat(id)) {
        features.push(SheetEntry {
            label: f.name.clone(),
            value: "class feat".into(),
            detail: Some(f.text.clone()),
        });
    }
    for id in &state.bonus_class_feats {
        if let Some(f) = data.class_feat(id) {
            features.push(SheetEntry {
                label: f.name.clone(),
                value: "class feat (Natural Ambition)".into(),
                detail: Some(f.text.clone()),
            });
        }
    }
    for id in &state.chosen_general_feats {
        if let Some(f) = data.general_feat(id) {
            features.push(SheetEntry {
                label: f.name.clone(),
                value: "general feat".into(),
                detail: Some(f.text.clone()),
            });
        }
    }
    if let Some(b) = state.background.as_ref().and_then(|id| data.background(id)) {
        // A choice-dependent skill feat follows the chosen sub-choice
        // skill; a fixed one renders directly; no entry while the choice
        // (or the feat itself) is missing.
        let feat_label = if !b.skill_feat_by_choice.is_empty() {
            state
                .background_skill_choice
                .as_ref()
                .and_then(|s| b.skill_feat_label_for_choice(data, s))
        } else {
            b.skill_feat_label(data)
        };
        if let Some(label) = feat_label {
            features.push(SheetEntry {
                label,
                value: format!("skill feat — {}", b.name),
                detail: Some(b.text.clone()),
            });
        }
    }
    for e in &state.effects {
        if let Effect::GrantLore { name: lore } = e {
            features.push(SheetEntry {
                label: format!("Additional Lore ({lore})"),
                value: "skill feat".into(),
                detail: None,
            });
        }
    }
    if !features.is_empty() {
        sections.push(SheetSection {
            title: "Features".to_string(),
            entries: features,
        });
    }

    // Equipment.
    let items = inventory(state, data);
    if !items.is_empty() || state.kit.is_some() {
        let mut entries: Vec<SheetEntry> = Vec::new();
        let mut bulk_total: i64 = 0;
        let mut armor_seen = false;
        for (id, source) in &items {
            let armor_record = data.equipment.armor.iter().find(|r| r.id == *id);
            let mut bulk = data
                .equipment
                .weapons
                .iter()
                .find(|r| r.id == *id)
                .map(|r| bulk_tenths(&r.bulk))
                .or_else(|| armor_record.map(|r| bulk_tenths(&r.bulk)))
                .or_else(|| {
                    data.equipment
                        .shields
                        .iter()
                        .find(|r| r.id == *id)
                        .map(|r| bulk_tenths(&r.bulk))
                })
                .or_else(|| {
                    data.equipment
                        .gear
                        .iter()
                        .find(|r| r.id == *id)
                        .map(|r| bulk_tenths(&r.bulk))
                })
                .unwrap_or(0);
            let mut note = source.clone();
            if let Some(a) = armor_record {
                if armor_seen {
                    // A second suit of armor is carried, not worn: +1 Bulk.
                    bulk += 10;
                    note = format!("{note}; carried");
                } else {
                    armor_seen = true;
                    note = format!("{note}; worn");
                }
                let _ = a;
            }
            bulk_total += bulk;
            entries.push(SheetEntry {
                label: item_name(id, data),
                value: format_bulk_tenths(bulk),
                detail: Some(note),
            });
        }
        let spend = total_spend_cp(state, data);
        entries.push(SheetEntry {
            label: "Coins".into(),
            value: format_cp(STARTING_WEALTH_CP - spend),
            detail: Some(format!(
                "15 gp starting wealth - {} spent",
                format_cp(spend)
            )),
        });
        let str_mod = state.modifier(Attribute::Str);
        entries.push(SheetEntry {
            label: "Bulk".into(),
            value: format_bulk_tenths(bulk_total),
            detail: Some(format!(
                "encumbered above {} Bulk, maximum {} Bulk",
                5 + str_mod,
                10 + str_mod
            )),
        });
        sections.push(SheetSection {
            title: "Equipment".to_string(),
            entries,
        });
    }

    // Spellcasting (prepared casters): every value derived from the
    // class's printed spellcasting entry and the folded build choices.
    // Slot and per-day counts are stated facts; which spells are prepared
    // is session state and no business of this sheet.
    if let Some((c, sc)) = class.and_then(|c| c.spellcasting.as_ref().map(|sc| (c, sc))) {
        let attr = state
            .key_attribute
            .or_else(|| c.key_attribute_choice.first().copied());
        let m = attr.map(|a| state.modifier(a)).unwrap_or(0);
        let attr_label = attr.map(|a| a.abbrev()).unwrap_or("—");
        let attack = Proficiency::parse(&sc.attack_proficiency);
        let dc = Proficiency::parse(&sc.dc_proficiency);
        let mut entries = vec![
            SheetEntry {
                label: "Tradition".into(),
                value: capitalize(&sc.tradition),
                detail: None,
            },
            SheetEntry {
                label: "Spell attack".into(),
                value: format_signed(attack.bonus(LEVEL) + m),
                detail: Some(format!(
                    "{} {} + {m} {attr_label}",
                    attack.bonus(LEVEL),
                    attack.label()
                )),
            },
            SheetEntry {
                label: "Spell DC".into(),
                value: (10 + dc.bonus(LEVEL) + m).to_string(),
                detail: Some(format!(
                    "10 + {} {} + {m} {attr_label}",
                    dc.bonus(LEVEL),
                    dc.label()
                )),
            },
        ];
        let school = state.school.as_ref().and_then(|id| data.school(id));
        let extra = if sc.school_extra_slot && school.is_some() {
            1
        } else {
            0
        };
        entries.push(SheetEntry {
            label: "Cantrips".into(),
            value: format!("{}/day", sc.cantrips_prepared + extra),
            detail: Some(format!(
                "heightened to rank {} (half level, rounded up){}",
                (LEVEL + 1) / 2,
                school
                    .filter(|_| extra > 0)
                    .map(|s| format!(" · includes 1 school cantrip ({} curriculum)", s.name))
                    .unwrap_or_default()
            )),
        });
        entries.push(SheetEntry {
            label: "Rank 1 slots".into(),
            value: (sc.rank1_slots + extra).to_string(),
            detail: school
                .filter(|_| extra > 0)
                .map(|s| format!("includes 1 school slot ({} curriculum only)", s.name)),
        });
        if let Some(t) = state.thesis.as_ref().and_then(|id| data.thesis(id)) {
            entries.push(SheetEntry {
                label: "Arcane thesis".into(),
                value: t.name.clone(),
                detail: None,
            });
        }
        if let Some(s) = school {
            entries.push(SheetEntry {
                label: "Arcane school".into(),
                value: s.name.clone(),
                detail: None,
            });
            if let Some(f) = data.spell(&s.focus_spell) {
                entries.push(SheetEntry {
                    label: "Focus pool".into(),
                    value: "1 Focus Point".into(),
                    detail: Some(format!("focus spell: {} (from {})", f.name, s.name)),
                });
            }
        }
        let book_names = |ids: &[String]| -> String {
            if ids.is_empty() {
                "none chosen yet".to_string()
            } else {
                ids.iter()
                    .map(|id| {
                        data.spell(id)
                            .map(|s| s.name.clone())
                            .unwrap_or_else(|| id.clone())
                    })
                    .collect::<Vec<_>>()
                    .join(", ")
            }
        };
        entries.push(SheetEntry {
            label: "Spellbook (cantrips)".into(),
            value: book_names(&state.spellbook_cantrips),
            detail: None,
        });
        entries.push(SheetEntry {
            label: "Spellbook (rank 1)".into(),
            value: book_names(&state.spellbook_rank1),
            detail: school.map(|s| format!("includes the {} curriculum additions", s.name)),
        });
        entries.push(SheetEntry {
            label: "Preparation".into(),
            value: "at the table".into(),
            detail: Some(
                "Daily preparation is session play, not character creation —                  it arrives with the play features."
                    .into(),
            ),
        });
        sections.push(SheetSection {
            title: "Spellcasting".to_string(),
            entries,
        });
    }

    // Languages and lore. The value keeps the ancestry defaults first, in
    // record order, then chosen additional languages in pick order — with
    // nothing chosen it renders exactly as before.
    if let Some(a) = ancestry {
        let mut languages = a.languages.clone();
        for lang in &state.chosen_languages {
            if !languages.contains(lang) {
                languages.push(lang.clone());
            }
        }
        let mut entries = vec![SheetEntry {
            label: "Languages".into(),
            value: languages.join(", "),
            detail: None,
        }];
        if !state.lores.is_empty() {
            for (lore, source) in &state.lores {
                entries.push(SheetEntry {
                    label: lore.clone(),
                    value: "trained".into(),
                    detail: Some(source.clone()),
                });
            }
        }
        sections.push(SheetSection {
            title: "Languages & Lore".to_string(),
            entries,
        });
    }

    SheetView {
        name,
        summary,
        sections,
    }
}

impl crate::data::AncestryRecord {
    fn senses_with_effects(&self, state: &Pf2eState) -> String {
        let mut senses: Vec<String> = self.senses.clone();
        for e in &state.effects {
            match e {
                Effect::Sense { value } => {
                    if !senses.contains(value) {
                        senses.push(value.clone());
                    }
                }
                // Grants `otherwise` normally; when the ancestry's own
                // base senses already include `otherwise`, upgrades to
                // `sense` instead (the Aiuvarin/Dromaar rule).
                Effect::SenseUpgrade { sense, otherwise } => {
                    let granted = if self.senses.contains(otherwise) {
                        sense
                    } else {
                        otherwise
                    };
                    if !senses.contains(granted) {
                        senses.push(granted.clone());
                    }
                }
                _ => {}
            }
        }
        senses.join(", ")
    }
}

fn batch_label(batch: &str) -> String {
    match batch {
        "ancestry" => "ancestry".to_string(),
        "ancestry-free" => "ancestry (free)".to_string(),
        "background" => "background".to_string(),
        "class" => "class key attribute".to_string(),
        "free" => "free boost".to_string(),
        other => other.to_string(),
    }
}

pub fn worn_armor<'a>(
    state: &Pf2eState,
    data: &'a RulesData,
) -> Option<&'a crate::data::ArmorRecord> {
    inventory(state, data)
        .iter()
        .find_map(|(id, _)| data.equipment.armor.iter().find(|r| r.id == *id))
}

fn effective_speed(state: &Pf2eState, data: &RulesData) -> i32 {
    let base = state
        .ancestry
        .as_ref()
        .and_then(|id| data.ancestry(id))
        .map(|a| a.speed)
        .unwrap_or(25);
    let bonus: i32 = state
        .effects
        .iter()
        .map(|e| match e {
            Effect::SpeedBonus { value } => *value,
            _ => 0,
        })
        .sum();
    let ignore_armor = state.has_effect(|e| matches!(e, Effect::IgnoreArmorSpeedPenalty));
    let armor_penalty = match worn_armor(state, data) {
        Some(a) if !ignore_armor => {
            // Meeting the armor's Strength requirement reduces the Speed
            // penalty by 5 feet.
            if state.modifier(Attribute::Str) >= a.str_req {
                (a.speed_penalty + 5).min(0)
            } else {
                a.speed_penalty
            }
        }
        _ => 0,
    };
    base + bonus + armor_penalty
}

fn attack_entries(
    state: &Pf2eState,
    data: &RulesData,
    class: &crate::data::ClassRecord,
) -> Vec<SheetEntry> {
    let str_ = state.modifier(Attribute::Str);
    let dex = state.modifier(Attribute::Dex);
    let mut entries = Vec::new();

    let prof_for = |category: &str| -> Proficiency {
        match category {
            "simple" => Proficiency::parse(&class.proficiencies.simple_weapons),
            "martial" => Proficiency::parse(&class.proficiencies.martial_weapons),
            "advanced" => Proficiency::parse(&class.proficiencies.advanced_weapons),
            _ => Proficiency::Untrained,
        }
    };

    // Fist first — everyone has it, unless a replaces_fist unarmed-attack
    // effect (Iron Fists pattern) swaps it out below.
    let unarmed_prof = Proficiency::parse(&class.proficiencies.unarmed_attacks);
    let fist_replaced = state.has_effect(|e| {
        matches!(
            e,
            Effect::UnarmedAttack {
                replaces_fist: true,
                ..
            }
        )
    });
    if !fist_replaced {
        let fist_attr = if dex > str_ { dex } else { str_ };
        let fist_attr_name = if dex > str_ { "Dex" } else { "Str" };
        entries.push(SheetEntry {
            label: "Fist".into(),
            value: format!(
                "{} · 1d4{} B",
                format_signed(unarmed_prof.bonus(LEVEL) + fist_attr),
                if str_ != 0 {
                    format_signed(str_)
                } else {
                    String::new()
                }
            ),
            detail: Some(format!(
                "{} {} + {} {} · agile, finesse, nonlethal, unarmed",
                unarmed_prof.bonus(LEVEL),
                unarmed_prof.label(),
                fist_attr,
                fist_attr_name
            )),
        });
    }
    for e in &state.effects {
        if let Effect::UnarmedAttack {
            name,
            damage,
            traits,
            range,
            replaces_fist: _,
        } = e
        {
            // Kept simple by design: a `range` marks a true ranged
            // unarmed attack (Seedpod) — Dex to the attack roll, no
            // attribute to damage. Melee unarmed attacks use Str (Dex
            // with finesse when higher) and add Str to damage.
            let (attr, attr_name, dmg_mod) = if range.is_some() {
                (dex, "Dex", 0)
            } else {
                let finesse = traits.iter().any(|t| t == "finesse");
                if finesse && dex > str_ {
                    (dex, "Dex", str_)
                } else {
                    (str_, "Str", str_)
                }
            };
            entries.push(SheetEntry {
                label: name.clone(),
                value: format!(
                    "{} · {}{}",
                    format_signed(unarmed_prof.bonus(LEVEL) + attr),
                    damage,
                    if dmg_mod != 0 {
                        format!(" ({})", format_signed(dmg_mod))
                    } else {
                        String::new()
                    }
                ),
                detail: Some(format!(
                    "{} {} + {} {}{} · {}",
                    unarmed_prof.bonus(LEVEL),
                    unarmed_prof.label(),
                    attr,
                    attr_name,
                    range
                        .as_ref()
                        .map(|r| format!(" · {r}"))
                        .unwrap_or_default(),
                    traits.join(", ")
                )),
            });
        }
    }

    for (id, _) in inventory(state, data) {
        let Some(w) = data.equipment.weapons.iter().find(|r| r.id == id) else {
            continue;
        };
        let Some(damage) = &w.damage else { continue }; // ammunition
        let prof = prof_for(&w.category);
        // A thrown weapon is a melee weapon you can also throw; only true
        // ranged weapons (bows, slings) attack and damage with Dex rules.
        let thrown = w.traits.iter().any(|t| t.starts_with("thrown"));
        let is_ranged = w.range.is_some() && !thrown;
        let finesse = w.traits.iter().any(|t| t == "finesse");
        let propulsive = w.traits.iter().any(|t| t == "propulsive");
        let (attr, attr_name) = if is_ranged || (finesse && dex > str_) {
            (dex, "Dex")
        } else {
            (str_, "Str")
        };
        let bonus = prof.bonus(LEVEL) + attr;
        let dmg_mod = if is_ranged {
            if propulsive && str_ > 0 {
                str_ / 2
            } else if propulsive {
                str_
            } else {
                0
            }
        } else {
            str_
        };
        entries.push(SheetEntry {
            label: w.name.clone(),
            value: format!(
                "{} · {}{}",
                format_signed(bonus),
                damage,
                if dmg_mod != 0 {
                    format_signed(dmg_mod)
                } else {
                    String::new()
                }
            ),
            detail: Some(format!(
                "{} {} ({}) + {} {}{}{}",
                prof.bonus(LEVEL),
                prof.label(),
                w.category,
                attr,
                attr_name,
                w.range
                    .as_ref()
                    .map(|r| format!(" · {r}"))
                    .unwrap_or_default(),
                if w.traits.is_empty() {
                    String::new()
                } else {
                    format!(" · {}", w.traits.join(", "))
                }
            )),
        });
    }
    entries
}

fn skill_entries(
    state: &Pf2eState,
    data: &RulesData,
    class: &crate::data::ClassRecord,
) -> Vec<SheetEntry> {
    let resolution = state.skill_resolution();
    let armor = worn_armor(state, data);
    let str_mod = state.modifier(Attribute::Str);
    let check_penalty = match armor {
        Some(a) if str_mod < a.str_req => a.check_penalty,
        _ => 0,
    };
    let _ = class;
    data.skills
        .iter()
        .map(|skill| {
            let trained_source = resolution
                .trained
                .iter()
                .find(|(id, _)| *id == skill.id)
                .map(|(_, source)| source.clone());
            let prof = if trained_source.is_some() {
                Proficiency::Trained
            } else {
                Proficiency::Untrained
            };
            let attr_mod = state.modifier(skill.attribute);
            let physical = matches!(skill.attribute, Attribute::Str | Attribute::Dex);
            let penalty = if physical { check_penalty } else { 0 };
            let total = prof.bonus(LEVEL) + attr_mod + penalty;
            let mut detail = format!(
                "{} {} + {} {}",
                prof.bonus(LEVEL),
                prof.label(),
                attr_mod,
                skill.attribute.abbrev()
            );
            if penalty != 0 {
                detail.push_str(&format!(" {penalty} armor check penalty"));
            }
            if let Some(source) = trained_source {
                detail.push_str(&format!(" · from {source}"));
            }
            SheetEntry {
                label: skill.name.clone(),
                value: format_signed(total),
                detail: Some(detail),
            }
        })
        .collect()
}

// ---- Selection parsing and checklist helpers shared by kind modules ----

use engine_core::ApplyError;
use types::{ChecklistEntry, ChecklistSeverity, Selection, SlotId, StepId};

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

pub fn sel_attribute(selection: &Selection) -> Result<Attribute, ApplyError> {
    let id = sel_single(selection)?;
    Attribute::from_option_id(id)
        .ok_or_else(|| ApplyError::new(format!("'{id}' is not an attribute")))
}

pub fn sel_attributes(selection: &Selection) -> Result<Vec<Attribute>, ApplyError> {
    sel_multi(selection)?
        .iter()
        .map(|id| {
            Attribute::from_option_id(id)
                .ok_or_else(|| ApplyError::new(format!("'{id}' is not an attribute")))
        })
        .collect()
}

// ---- Prerequisites (shared by every catalog that evaluates them) ----

/// Human-readable description of one prerequisite: the record's own text
/// when present, otherwise generated from the kind's fields.
pub fn prereq_description(data: &RulesData, p: &crate::data::Prerequisite) -> String {
    if !p.text.is_empty() {
        return p.text.clone();
    }
    match p.kind.as_str() {
        "attribute" => match (p.attribute, p.value) {
            (Some(attr), Some(value)) => format!("{} {}", attr.name(), format_signed(value)),
            _ => "an attribute threshold".to_string(),
        },
        "trained_skill" => match &p.skill {
            Some(skill) => format!(
                "trained in {}",
                data.skill(skill)
                    .map(|s| s.name.clone())
                    .unwrap_or_else(|| skill.clone())
            ),
            None => "trained in a skill".to_string(),
        },
        other => other.replace('_', " "),
    }
}

/// Evaluable prerequisite kinds gate availability against the folded
/// state; the rest annotate only. Returns the greying reason for the
/// first unmet prerequisite. Used for option greying AND re-checked on
/// apply (the server folds through the same registrations, so a raw
/// request cannot skip it).
pub fn prereq_unavailable(
    data: &RulesData,
    prereqs: &[crate::data::Prerequisite],
    state: &Pf2eState,
) -> Option<String> {
    for p in prereqs {
        let unmet = match p.kind.as_str() {
            // No class in this data version has a spellcasting feature.
            "spellcasting" => true,
            "attribute" => match (p.attribute, p.value) {
                (Some(attr), Some(value)) => state.modifier(attr) < value,
                _ => false,
            },
            "trained_skill" => match &p.skill {
                Some(skill) => !state.is_trained(skill),
                None => false,
            },
            _ => false,
        };
        if unmet {
            // Spellcasting records carry their full reason as text; the
            // evaluated kinds get a generated "requires …" naming the rule.
            return Some(if p.kind == "spellcasting" && !p.text.is_empty() {
                p.text.clone()
            } else {
                format!("requires {}", prereq_description(data, p))
            });
        }
    }
    None
}

// ---- Player-named Lore skills ----

/// Normalize the player-typed Lore subject into the sheet's "<Typed> Lore"
/// form: trims, strips one trailing "Lore" word (any ASCII case) so typing
/// "Steppe Lore" doesn't render "Steppe Lore Lore", and rejects an empty
/// subject.
pub fn lore_name_from_text(text: &str) -> Result<String, ApplyError> {
    let t = text.trim();
    let bytes = t.as_bytes();
    let t = if bytes.len() > 5 && bytes[bytes.len() - 5..].eq_ignore_ascii_case(b" lore") {
        t[..t.len() - 5].trim_end()
    } else {
        t
    };
    if t.is_empty() || t.eq_ignore_ascii_case("lore") {
        return Err(ApplyError::new("name the Lore's subject (e.g. \"Steppe\")"));
    }
    Ok(format!("{t} Lore"))
}

// ---- Language options ----

/// Option ID for a language name ("Sylvan" → "lang.sylvan"). Languages are
/// plain names on ancestry records, not records of their own, so the slot
/// derives stable option IDs from the names.
pub fn lang_option_id(name: &str) -> String {
    format!("lang.{}", name.trim().to_lowercase().replace(' ', "-"))
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

/// Render-ready display name for any record or attribute option ID.
pub fn display_name(data: &RulesData, id: &OptionId) -> String {
    let s = id.as_str();
    if let Some(attr) = Attribute::from_option_id(id) {
        return attr.name().to_string();
    }
    if let Some(target) = s.strip_prefix("prof.") {
        // Proficiency-override chooser options (Canny Acumen targets).
        let mut label: String = target.to_string();
        if let Some(first) = label.get_mut(0..1) {
            first.make_ascii_uppercase();
        }
        return label;
    }
    if s.starts_with("lang.") {
        // Language options carry name-derived IDs; recover the display
        // name from the ancestry language lists.
        for a in &data.ancestries {
            for lang in a.languages.iter().chain(a.additional_languages.iter()) {
                if lang_option_id(lang) == s {
                    return lang.clone();
                }
            }
        }
        return s.trim_start_matches("lang.").to_string();
    }
    data.ancestry(s)
        .map(|r| r.name.clone())
        .or_else(|| data.spell(s).map(|r| r.name.clone()))
        .or_else(|| data.thesis(s).map(|r| r.name.clone()))
        .or_else(|| data.school(s).map(|r| r.name.clone()))
        .or_else(|| data.heritage(s).map(|r| r.name.clone()))
        .or_else(|| data.ancestry_feat(s).map(|r| r.name.clone()))
        .or_else(|| data.background(s).map(|r| r.name.clone()))
        .or_else(|| data.class(s).map(|r| r.name.clone()))
        .or_else(|| data.class_feat(s).map(|r| r.name.clone()))
        .or_else(|| data.general_feat(s).map(|r| r.name.clone()))
        .or_else(|| data.skill(s).map(|r| r.name.clone()))
        .or_else(|| data.kit(s).map(|r| r.name.clone()))
        .or_else(|| {
            data.kit("kit.fighter").and_then(|k| {
                k.options
                    .iter()
                    .find(|o| o.id == s)
                    .map(|o| format!("{} — {}", k.name, o.name))
            })
        })
        .unwrap_or_else(|| item_name(s, data))
}

/// A describe closure for slots whose selections are option IDs or text.
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

/// Attribute options for boost slots.
pub fn attribute_options(
    exclude_note: impl Fn(Attribute) -> Option<String>,
) -> Vec<types::OptionView> {
    ALL_ATTRIBUTES
        .into_iter()
        .map(|attr| {
            let note = exclude_note(attr);
            types::OptionView {
                id: attr.option_id(),
                label: attr.name().to_string(),
                summary: String::new(),
                details: vec![],
                available: note.is_none(),
                unavailable_reason: note,
                group: None,
                badge: None,
            }
        })
        .collect()
}

// ---- Slot and step identifiers ----
// Single-sourced here so kind modules can wire dependents without
// referencing each other (kinds -> mechanics -> engine-core).

pub const STEP_CONCEPT: &str = "concept";
pub const STEP_ANCESTRY: &str = "ancestry";
pub const STEP_BACKGROUND: &str = "background";
pub const STEP_CLASS: &str = "class";
pub const STEP_BOOSTS: &str = "boosts";
pub const STEP_EQUIPMENT: &str = "equipment";
pub const STEP_DETAILS: &str = "details";

pub const SLOT_CONCEPT: &str = "pf2e.concept";
pub const SLOT_ANCESTRY: &str = "pf2e.ancestry";
pub const SLOT_HERITAGE: &str = "pf2e.ancestry.heritage";
pub const SLOT_ANCESTRY_FEAT: &str = "pf2e.ancestry.feat";
pub const SLOT_ANCESTRY_FREE_BOOSTS: &str = "pf2e.boosts.ancestry-free";
pub const SLOT_ANCESTRY_LANGUAGES: &str = "pf2e.ancestry.languages";
pub const SLOT_BACKGROUND: &str = "pf2e.background";
pub const SLOT_BACKGROUND_SKILL: &str = "pf2e.background.skill";
pub const SLOT_BACKGROUND_LORE: &str = "pf2e.background.lore";
pub const SLOT_BACKGROUND_BOOST_CHOICE: &str = "pf2e.boosts.background-choice";
pub const SLOT_BACKGROUND_BOOST_FREE: &str = "pf2e.boosts.background-free";
pub const SLOT_CLASS: &str = "pf2e.class";
pub const SLOT_KEY_ATTRIBUTE: &str = "pf2e.class.key-attribute";
pub const SLOT_CLASS_FEAT: &str = "pf2e.class.feat";
pub const SLOT_CLASS_SKILL: &str = "pf2e.skills.class-choice";
pub const SLOT_TRAINED_SKILLS: &str = "pf2e.skills.trained";
pub const SLOT_HERITAGE_SKILLS: &str = "pf2e.skills.heritage-choice";
pub const SLOT_FEAT_SKILLS: &str = "pf2e.skills.feat-choice";
pub const SLOT_FEAT_LORE: &str = "pf2e.skills.feat-lore";
pub const SLOT_PROFICIENCY_CHOICE: &str = "pf2e.feats.proficiency-choice";
pub const SLOT_HERITAGE_GENERAL_FEAT: &str = "pf2e.feats.general.heritage";
pub const SLOT_FEAT_GENERAL_FEAT: &str = "pf2e.feats.general.ancestry-feat";
pub const SLOT_NATURAL_AMBITION: &str = "pf2e.feats.class.natural-ambition";
pub const SLOT_FREE_BOOSTS: &str = "pf2e.boosts.free";
pub const SLOT_KIT: &str = "pf2e.equipment.kit";
pub const SLOT_EXTRA_ITEMS: &str = "pf2e.equipment.extra";
pub const SLOT_NAME: &str = "pf2e.details.name";
pub const SLOT_DESCRIPTION: &str = "pf2e.details.description";
pub const SLOT_THESIS: &str = "pf2e.class.thesis";
pub const SLOT_SCHOOL: &str = "pf2e.class.school";
pub const SLOT_SPELLBOOK_CANTRIPS: &str = "pf2e.class.spellbook.cantrips";
pub const SLOT_SPELLBOOK_RANK1: &str = "pf2e.class.spellbook.rank1";

/// Every registered slot ID — the namespace suggested-build entries are
/// integrity-checked against. Keep in lockstep with the SLOT_* constants
/// above (the ruleset construction test asserts the engine registers
/// exactly these).
pub fn known_slot_ids() -> &'static [&'static str] {
    &[
        SLOT_CONCEPT,
        SLOT_ANCESTRY,
        SLOT_HERITAGE,
        SLOT_ANCESTRY_FEAT,
        SLOT_ANCESTRY_FREE_BOOSTS,
        SLOT_ANCESTRY_LANGUAGES,
        SLOT_BACKGROUND,
        SLOT_BACKGROUND_SKILL,
        SLOT_BACKGROUND_LORE,
        SLOT_BACKGROUND_BOOST_CHOICE,
        SLOT_BACKGROUND_BOOST_FREE,
        SLOT_CLASS,
        SLOT_KEY_ATTRIBUTE,
        SLOT_CLASS_FEAT,
        SLOT_CLASS_SKILL,
        SLOT_TRAINED_SKILLS,
        SLOT_HERITAGE_SKILLS,
        SLOT_FEAT_SKILLS,
        SLOT_FEAT_LORE,
        SLOT_PROFICIENCY_CHOICE,
        SLOT_HERITAGE_GENERAL_FEAT,
        SLOT_FEAT_GENERAL_FEAT,
        SLOT_NATURAL_AMBITION,
        SLOT_FREE_BOOSTS,
        SLOT_KIT,
        SLOT_EXTRA_ITEMS,
        SLOT_NAME,
        SLOT_DESCRIPTION,
        SLOT_THESIS,
        SLOT_SCHOOL,
        SLOT_SPELLBOOK_CANTRIPS,
        SLOT_SPELLBOOK_RANK1,
    ]
}

pub fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) => c.to_uppercase().collect::<String>() + chars.as_str(),
        None => String::new(),
    }
}
