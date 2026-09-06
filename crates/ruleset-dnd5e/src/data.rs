//! Rules-data records: parsed from the versioned JSON files, passed in as
//! strings (this crate never touches a filesystem). Every record carries a
//! stable ID and per-record license metadata naming the SRD 5.2.1 and its
//! CC BY 4.0 attribution.

use std::collections::{BTreeMap, BTreeSet};

use serde::Deserialize;

use crate::mechanics::Ability;

#[derive(Debug, Clone, Deserialize)]
pub struct SourceRef {
    pub book: String,
    pub page: u32,
    pub url: String,
    pub license: String,
    pub attribution: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Manifest {
    pub version: String,
    pub system: String,
    pub description: String,
    /// Prior shipped data versions this one supersedes, oldest first.
    #[serde(default)]
    pub supersedes: Vec<String>,
    pub license_notice: LicenseNotice,
}

/// The CC BY 4.0 notice the app must display: the SRD's own required
/// attribution sentence, verbatim, plus the license statement.
#[derive(Debug, Clone, Deserialize)]
pub struct LicenseNotice {
    pub attribution: String,
    pub license: String,
    pub license_url: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SkillRecord {
    pub id: String,
    pub name: String,
    pub ability: Ability,
    pub source: SourceRef,
}

/// One ability-score generation method. `kind` selects the machinery:
/// `array` offers each of `array`'s values under every ability and
/// requires each value once; `point-buy` offers every score in `costs`
/// under every ability against `budget`. A rolling method arrives as a
/// third kind in `dnd-dice` without touching the method slot.
#[derive(Debug, Clone, Deserialize)]
pub struct ScoreMethodRecord {
    pub id: String,
    pub name: String,
    pub kind: String,
    pub text: String,
    #[serde(default)]
    pub array: Vec<u32>,
    #[serde(default)]
    pub budget: u32,
    #[serde(default)]
    pub costs: BTreeMap<String, u32>,
    pub source: SourceRef,
}

impl ScoreMethodRecord {
    pub fn is_array(&self) -> bool {
        self.kind == "array"
    }
    pub fn is_point_buy(&self) -> bool {
        self.kind == "point-buy"
    }
    /// The point cost of a score under this method, when the method is a
    /// point buy and the score is purchasable.
    pub fn cost_of(&self, score: u32) -> Option<u32> {
        self.costs.get(&score.to_string()).copied()
    }
    /// The scores this method offers under every ability, ascending for a
    /// point buy and in printed order for an array.
    pub fn offered_scores(&self) -> Vec<u32> {
        if self.is_array() {
            self.array.clone()
        } else {
            let mut scores: Vec<u32> = self.costs.keys().filter_map(|k| k.parse().ok()).collect();
            scores.sort_unstable();
            scores
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct ScoresFile {
    pub methods: Vec<ScoreMethodRecord>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Trait {
    pub name: String,
    pub text: String,
}

/// A species trait that asks the player to pick one of several benefits
/// (the Goliath's Giant Ancestry).
#[derive(Debug, Clone, Deserialize)]
pub struct ChoiceTrait {
    pub name: String,
    pub text: String,
    pub options: Vec<ChoiceOption>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ChoiceOption {
    pub id: String,
    pub name: String,
    pub text: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SpeciesRecord {
    pub id: String,
    pub name: String,
    pub creature_type: String,
    pub size: String,
    pub speed: i32,
    #[serde(default)]
    pub darkvision: Option<u32>,
    pub traits: Vec<Trait>,
    /// Skills the species lets the player choose (the Human's Skillful).
    #[serde(default)]
    pub skill_choices: u32,
    /// Whether the species grants an Origin feat of the player's choice
    /// (the Human's Versatile).
    #[serde(default)]
    pub origin_feat_choice: bool,
    /// Hit Point maximum bonus per character level (Dwarven Toughness).
    #[serde(default)]
    pub hp_bonus_per_level: u32,
    /// Counts as one size larger for carrying capacity (Powerful Build).
    #[serde(default)]
    pub powerful_build: bool,
    #[serde(default)]
    pub choice_trait: Option<ChoiceTrait>,
    pub source: SourceRef,
}

/// One item line of an equipment package.
#[derive(Debug, Clone, Deserialize)]
pub struct PackItem {
    pub item: String,
    pub count: u32,
}

#[derive(Debug, Clone, Deserialize)]
pub struct EquipmentPackage {
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub label: String,
    pub items: Vec<PackItem>,
    pub gold: u32,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BackgroundRecord {
    pub id: String,
    pub name: String,
    /// The three abilities the background's increases may go to.
    pub abilities: Vec<Ability>,
    /// The granted Origin feat record ID.
    pub feat: String,
    /// Display override for a parameterized grant ("Magic Initiate
    /// (Cleric)"); the feat record's name otherwise.
    #[serde(default)]
    pub feat_display: Option<String>,
    pub skills: Vec<String>,
    /// The granted tool proficiency, as a tool record ID.
    pub tool: String,
    pub equipment: EquipmentPackage,
    /// The coin alternative to the equipment package.
    pub gold_alternative: u32,
    pub source: SourceRef,
}

impl BackgroundRecord {
    pub fn feat_label(&self, data: &RulesData) -> String {
        self.feat_display
            .clone()
            .or_else(|| data.feat(&self.feat).map(|f| f.name.clone()))
            .unwrap_or_default()
    }
}

/// A mechanical effect a feat carries, evaluated by derivation or by the
/// chooser slots. Unknown types fail to parse (a typo is a build defect).
#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Effect {
    /// Add the Proficiency Bonus to Initiative (Alert).
    InitiativeProficiency,
    /// The feat's spell choices are not modeled this slice (Magic
    /// Initiate); the sheet says so beside the rules text.
    SpellChoicesUnsupported,
    /// Opens a chooser for `count` skills or tools (Skilled).
    ChooseSkillsOrTools { count: u32 },
    /// Bonus to attack rolls with Ranged weapons (Archery).
    RangedAttackBonus { bonus: i32 },
    /// Bonus to AC while wearing Light, Medium, or Heavy armor (Defense).
    ArmorClassBonusArmored { bonus: i32 },
}

#[derive(Debug, Clone, Deserialize)]
pub struct FeatRecord {
    pub id: String,
    pub name: String,
    /// `origin` or `fighting-style`.
    pub category: String,
    pub text: String,
    #[serde(default)]
    pub effects: Vec<Effect>,
    pub source: SourceRef,
}

impl FeatRecord {
    pub fn is_origin(&self) -> bool {
        self.category == "origin"
    }
    pub fn is_fighting_style(&self) -> bool {
        self.category == "fighting-style"
    }
    /// The count of a `choose_skills_or_tools` effect, when present.
    pub fn skill_or_tool_choices(&self) -> u32 {
        self.effects
            .iter()
            .filter_map(|e| match e {
                Effect::ChooseSkillsOrTools { count } => Some(*count),
                _ => None,
            })
            .sum()
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct SkillChoice {
    pub count: u32,
    pub from: Vec<String>,
}

/// A fixed class feature: a record with an ID (its name never lives in
/// source) and its printed text.
#[derive(Debug, Clone, Deserialize)]
pub struct ClassFeature {
    pub id: String,
    pub name: String,
    pub text: String,
}

/// One level of a class's advancement table (level 2 and up): the fixed
/// features gained and whether the level opens the subclass choice.
#[derive(Debug, Clone, Deserialize)]
pub struct AdvancementLevel {
    pub level: u32,
    #[serde(default)]
    pub features: Vec<ClassFeature>,
    #[serde(default)]
    pub subclass_choice: bool,
    #[serde(default)]
    pub subclass_text: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct GoldAlternative {
    pub id: String,
    #[serde(default)]
    pub label: String,
    pub gold: u32,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ClassRecord {
    pub id: String,
    pub name: String,
    pub text: String,
    pub primary_abilities: Vec<Ability>,
    pub hit_die: u32,
    pub hp_at_level_1: u32,
    pub hp_per_level: u32,
    pub saving_throws: Vec<Ability>,
    pub skill_choice: SkillChoice,
    /// Weapon categories the class is proficient with ("simple",
    /// "martial").
    pub weapon_proficiencies: Vec<String>,
    /// Armor categories the class is trained with ("light", "medium",
    /// "heavy", "shield").
    pub armor_training: Vec<String>,
    /// Level-1 features, fixed (Second Wind, Weapon Mastery) or the
    /// anchor of a choice (Fighting Style).
    pub features: Vec<ClassFeature>,
    /// The level-1 feature whose choice is the Fighting Style slot, when
    /// the class has one.
    #[serde(default)]
    pub fighting_style_feature: Option<String>,
    /// The level-1 feature whose choice is the weapon-mastery slot, when
    /// the class has one, and how many weapons it covers.
    #[serde(default)]
    pub weapon_mastery_feature: Option<String>,
    #[serde(default)]
    pub weapon_mastery_count: u32,
    #[serde(default)]
    pub advancement: Vec<AdvancementLevel>,
    pub equipment_packages: Vec<EquipmentPackage>,
    pub gold_alternative: GoldAlternative,
    pub source: SourceRef,
}

impl ClassRecord {
    /// The highest level this class's advancement table defines — the
    /// shipped cap (1 when the table is empty).
    pub fn level_cap(&self) -> u32 {
        self.advancement.iter().map(|a| a.level).max().unwrap_or(1)
    }
    pub fn advancement_at(&self, level: u32) -> Option<&AdvancementLevel> {
        self.advancement.iter().find(|a| a.level == level)
    }
    pub fn feature(&self, id: &str) -> Option<&ClassFeature> {
        self.features
            .iter()
            .chain(self.advancement.iter().flat_map(|a| a.features.iter()))
            .find(|f| f.id == id)
    }
    pub fn is_proficient_with_weapon(&self, weapon: &WeaponRecord) -> bool {
        self.weapon_proficiencies.contains(&weapon.category)
    }
    pub fn is_trained_with_armor(&self, armor: &ArmorRecord) -> bool {
        self.armor_training.contains(&armor.category)
    }
    /// The levels at which this class opens its subclass choice.
    pub fn subclass_levels(&self) -> Vec<u32> {
        self.advancement
            .iter()
            .filter(|a| a.subclass_choice)
            .map(|a| a.level)
            .collect()
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct SubclassFeature {
    pub level: u32,
    pub id: String,
    pub name: String,
    pub text: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SubclassRecord {
    pub id: String,
    pub name: String,
    pub class: String,
    pub text: String,
    pub features: Vec<SubclassFeature>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct WeaponRecord {
    pub id: String,
    pub name: String,
    /// "simple" or "martial".
    pub category: String,
    /// "melee" or "ranged".
    pub kind: String,
    pub damage: String,
    pub damage_type: String,
    /// The printed properties ("Finesse", "Thrown", ...); ranges and
    /// versatile damage ride in their own fields.
    pub properties: Vec<String>,
    #[serde(default)]
    pub versatile_damage: Option<String>,
    #[serde(default)]
    pub range: Option<String>,
    #[serde(default)]
    pub ammunition: Option<String>,
    pub mastery: String,
    pub weight_lb: f64,
    pub cost_cp: u32,
    pub source: SourceRef,
}

impl WeaponRecord {
    pub fn has_property(&self, name: &str) -> bool {
        self.properties.iter().any(|p| p.starts_with(name))
    }
    pub fn is_ranged(&self) -> bool {
        self.kind == "ranged"
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct ArmorRecord {
    pub id: String,
    pub name: String,
    /// "light", "medium", "heavy", or "shield".
    pub category: String,
    /// Base AC for armor; the AC bonus for a shield.
    pub base_ac: i32,
    pub add_dex: bool,
    #[serde(default)]
    pub dex_max: Option<i32>,
    #[serde(default)]
    pub strength_requirement: Option<u32>,
    pub stealth_disadvantage: bool,
    pub weight_lb: f64,
    pub cost_cp: u32,
    pub source: SourceRef,
}

impl ArmorRecord {
    pub fn is_shield(&self) -> bool {
        self.category == "shield"
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct GearRecord {
    pub id: String,
    pub name: String,
    pub weight_lb: f64,
    pub cost_cp: u32,
    #[serde(default)]
    pub text: String,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct EquipmentFile {
    pub weapons: Vec<WeaponRecord>,
    pub armor: Vec<ArmorRecord>,
    pub gear: Vec<GearRecord>,
    pub tools: Vec<GearRecord>,
}

/// The files as the parser takes them.
pub struct RulesDataFiles<'a> {
    pub manifest: &'a str,
    pub skills: &'a str,
    pub scores: &'a str,
    pub species: &'a str,
    pub backgrounds: &'a str,
    pub feats: &'a str,
    pub classes: &'a str,
    pub subclasses: &'a str,
    pub equipment: &'a str,
}

#[derive(Debug, Clone)]
pub struct RulesData {
    pub manifest: Manifest,
    pub skills: Vec<SkillRecord>,
    pub scores: ScoresFile,
    pub species: Vec<SpeciesRecord>,
    pub backgrounds: Vec<BackgroundRecord>,
    pub feats: Vec<FeatRecord>,
    pub classes: Vec<ClassRecord>,
    pub subclasses: Vec<SubclassRecord>,
    pub equipment: EquipmentFile,
}

#[derive(Debug, thiserror::Error)]
pub enum DataError {
    #[error("rules data file '{file}' failed to parse: {message}")]
    Parse { file: &'static str, message: String },
    #[error("rules data integrity: {0}")]
    Integrity(String),
}

fn parse<T: serde::de::DeserializeOwned>(file: &'static str, s: &str) -> Result<T, DataError> {
    serde_json::from_str(s).map_err(|e| DataError::Parse {
        file,
        message: e.to_string(),
    })
}

fn integrity(message: String) -> DataError {
    DataError::Integrity(message)
}

impl RulesData {
    pub fn parse(files: &RulesDataFiles<'_>) -> Result<Self, DataError> {
        let data = RulesData {
            manifest: parse("manifest.json", files.manifest)?,
            skills: parse("skills.json", files.skills)?,
            scores: parse("scores.json", files.scores)?,
            species: parse("species.json", files.species)?,
            backgrounds: parse("backgrounds.json", files.backgrounds)?,
            feats: parse("feats.json", files.feats)?,
            classes: parse("classes.json", files.classes)?,
            subclasses: parse("subclasses.json", files.subclasses)?,
            equipment: parse("equipment.json", files.equipment)?,
        };
        data.check_integrity()?;
        Ok(data)
    }

    /// The integrity rules the rules-data lint asserts: IDs unique and
    /// well-formed, every cross-reference resolvable, every class reaching
    /// the shipped cap, every subclass naming a shipped class.
    pub fn check_integrity(&self) -> Result<(), DataError> {
        let mut ids: BTreeSet<&str> = BTreeSet::new();
        let all_ids: Vec<&str> = self
            .skills
            .iter()
            .map(|r| r.id.as_str())
            .chain(self.scores.methods.iter().map(|r| r.id.as_str()))
            .chain(self.species.iter().map(|r| r.id.as_str()))
            .chain(self.backgrounds.iter().map(|r| r.id.as_str()))
            .chain(self.feats.iter().map(|r| r.id.as_str()))
            .chain(self.classes.iter().map(|r| r.id.as_str()))
            .chain(self.subclasses.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.weapons.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.armor.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.gear.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.tools.iter().map(|r| r.id.as_str()))
            // Embedded sub-records share the namespace: features,
            // packages, and choice-trait options must not collide.
            .chain(self.classes.iter().flat_map(|c| {
                c.features
                    .iter()
                    .map(|f| f.id.as_str())
                    .chain(
                        c.advancement
                            .iter()
                            .flat_map(|a| a.features.iter().map(|f| f.id.as_str())),
                    )
                    .chain(c.equipment_packages.iter().map(|p| p.id.as_str()))
                    .chain(std::iter::once(c.gold_alternative.id.as_str()))
            }))
            .chain(
                self.subclasses
                    .iter()
                    .flat_map(|s| s.features.iter().map(|f| f.id.as_str())),
            )
            .chain(self.species.iter().flat_map(|s| {
                s.choice_trait
                    .iter()
                    .flat_map(|t| t.options.iter().map(|o| o.id.as_str()))
            }))
            .collect();
        for id in &all_ids {
            if !ids.insert(id) {
                return Err(integrity(format!("duplicate record id '{id}'")));
            }
            if id.trim().is_empty() || id.contains(char::is_whitespace) || !id.contains('.') {
                return Err(integrity(format!("malformed record id '{id}'")));
            }
        }

        if self.manifest.system.is_empty() {
            return Err(integrity("manifest names no system".into()));
        }
        if !self
            .manifest
            .version
            .starts_with(&format!("{}-", self.manifest.system))
        {
            return Err(integrity(format!(
                "manifest version '{}' must begin with '{}-'",
                self.manifest.version, self.manifest.system
            )));
        }
        if self.manifest.license_notice.attribution.is_empty()
            || self.manifest.license_notice.license.is_empty()
        {
            return Err(integrity(
                "manifest license_notice must carry the attribution and license text".into(),
            ));
        }

        // Score methods: at least one; arrays carry six values; point buys
        // carry a budget and a contiguous cost table.
        if self.scores.methods.is_empty() {
            return Err(integrity("no ability-score methods shipped".into()));
        }
        for m in &self.scores.methods {
            match m.kind.as_str() {
                "array" => {
                    if m.array.len() != Ability::ALL.len() {
                        return Err(integrity(format!(
                            "score method '{}' must list exactly {} array values",
                            m.id,
                            Ability::ALL.len()
                        )));
                    }
                }
                "point-buy" => {
                    if m.budget == 0 || m.costs.is_empty() {
                        return Err(integrity(format!(
                            "score method '{}' needs a budget and a cost table",
                            m.id
                        )));
                    }
                    for key in m.costs.keys() {
                        if key.parse::<u32>().is_err() {
                            return Err(integrity(format!(
                                "score method '{}' cost key '{key}' is not a score",
                                m.id
                            )));
                        }
                    }
                }
                other => {
                    return Err(integrity(format!(
                        "score method '{}' has unknown kind '{other}'",
                        m.id
                    )))
                }
            }
        }

        for s in &self.species {
            if let Some(t) = &s.choice_trait {
                if t.options.is_empty() {
                    return Err(integrity(format!(
                        "species '{}' choice trait '{}' offers no options",
                        s.id, t.name
                    )));
                }
            }
        }

        for b in &self.backgrounds {
            if b.abilities.len() != 3 {
                return Err(integrity(format!(
                    "background '{}' must name exactly three abilities",
                    b.id
                )));
            }
            let feat = self.feat(&b.feat).ok_or_else(|| {
                integrity(format!(
                    "background '{}' feat '{}' does not resolve",
                    b.id, b.feat
                ))
            })?;
            if !feat.is_origin() {
                return Err(integrity(format!(
                    "background '{}' feat '{}' is not an Origin feat",
                    b.id, b.feat
                )));
            }
            for skill in &b.skills {
                if self.skill(skill).is_none() {
                    return Err(integrity(format!(
                        "background '{}' skill '{skill}' does not resolve",
                        b.id
                    )));
                }
            }
            if self.tool(&b.tool).is_none() {
                return Err(integrity(format!(
                    "background '{}' tool '{}' does not resolve",
                    b.id, b.tool
                )));
            }
            self.check_package(&b.id, &b.equipment)?;
        }

        for f in &self.feats {
            if !f.is_origin() && !f.is_fighting_style() {
                return Err(integrity(format!(
                    "feat '{}' has unknown category '{}'",
                    f.id, f.category
                )));
            }
        }

        // Classes: skills resolve, packages resolve, advancement tables run
        // contiguously from level 2 and every class reaches the shipped cap.
        let cap = self.max_advancement_level();
        for c in &self.classes {
            for skill in &c.skill_choice.from {
                if self.skill(skill).is_none() {
                    return Err(integrity(format!(
                        "class '{}' skill choice '{skill}' does not resolve",
                        c.id
                    )));
                }
            }
            if (c.skill_choice.count as usize) > c.skill_choice.from.len() {
                return Err(integrity(format!(
                    "class '{}' asks for more skills than it offers",
                    c.id
                )));
            }
            if let Some(id) = &c.fighting_style_feature {
                if !c.features.iter().any(|f| &f.id == id) {
                    return Err(integrity(format!(
                        "class '{}' fighting_style_feature '{id}' is not a level-1 feature",
                        c.id
                    )));
                }
                if !self.feats.iter().any(|f| f.is_fighting_style()) {
                    return Err(integrity(format!(
                        "class '{}' offers a Fighting Style but no fighting-style feats ship",
                        c.id
                    )));
                }
            }
            if let Some(id) = &c.weapon_mastery_feature {
                if !c.features.iter().any(|f| &f.id == id) {
                    return Err(integrity(format!(
                        "class '{}' weapon_mastery_feature '{id}' is not a level-1 feature",
                        c.id
                    )));
                }
                if c.weapon_mastery_count == 0 {
                    return Err(integrity(format!(
                        "class '{}' has a weapon-mastery feature but a zero count",
                        c.id
                    )));
                }
            }
            for (expected, adv) in (2..).zip(c.advancement.iter()) {
                if adv.level != expected {
                    return Err(integrity(format!(
                        "class '{}' advancement table must run contiguously from level 2 (found level {} where {expected} was expected)",
                        c.id, adv.level
                    )));
                }
                if adv.subclass_choice && !self.subclasses.iter().any(|s| s.class == c.id) {
                    return Err(integrity(format!(
                        "class '{}' opens its subclass choice at level {} but ships no subclass",
                        c.id, adv.level
                    )));
                }
            }
            for f in c
                .features
                .iter()
                .chain(c.advancement.iter().flat_map(|a| a.features.iter()))
            {
                if !f.id.starts_with("feature.") {
                    return Err(integrity(format!(
                        "class '{}' feature '{}' must carry a 'feature.' ID",
                        c.id, f.id
                    )));
                }
            }
            if cap > 1 && c.level_cap() != cap {
                return Err(integrity(format!(
                    "class '{}' defines levels through {} but the shipped cap is {cap} — every class must reach the cap",
                    c.id,
                    c.level_cap()
                )));
            }
            if c.equipment_packages.is_empty() {
                return Err(integrity(format!(
                    "class '{}' ships no equipment package",
                    c.id
                )));
            }
            for p in &c.equipment_packages {
                if p.id.is_empty() {
                    return Err(integrity(format!(
                        "class '{}' has an equipment package without an id",
                        c.id
                    )));
                }
                self.check_package(&c.id, p)?;
            }
            if !c.gold_alternative.id.starts_with("package.") {
                return Err(integrity(format!(
                    "class '{}' gold alternative must carry a 'package.' ID",
                    c.id
                )));
            }
        }

        for s in &self.subclasses {
            let class = self.class(&s.class).ok_or_else(|| {
                integrity(format!(
                    "subclass '{}' names unknown class '{}'",
                    s.id, s.class
                ))
            })?;
            let levels = class.subclass_levels();
            if levels.is_empty() {
                return Err(integrity(format!(
                    "subclass '{}' belongs to '{}', which never opens a subclass choice",
                    s.id, s.class
                )));
            }
            for f in &s.features {
                if !f.id.starts_with("feature.") {
                    return Err(integrity(format!(
                        "subclass '{}' feature '{}' must carry a 'feature.' ID",
                        s.id, f.id
                    )));
                }
            }
        }

        for w in &self.equipment.weapons {
            if !matches!(w.category.as_str(), "simple" | "martial") {
                return Err(integrity(format!(
                    "weapon '{}' has unknown category '{}'",
                    w.id, w.category
                )));
            }
            if !matches!(w.kind.as_str(), "melee" | "ranged") {
                return Err(integrity(format!(
                    "weapon '{}' has unknown kind '{}'",
                    w.id, w.kind
                )));
            }
            if w.mastery.is_empty() {
                return Err(integrity(format!(
                    "weapon '{}' has no mastery property",
                    w.id
                )));
            }
        }
        for a in &self.equipment.armor {
            if !matches!(a.category.as_str(), "light" | "medium" | "heavy" | "shield") {
                return Err(integrity(format!(
                    "armor '{}' has unknown category '{}'",
                    a.id, a.category
                )));
            }
        }
        Ok(())
    }

    fn check_package(&self, owner: &str, package: &EquipmentPackage) -> Result<(), DataError> {
        for line in &package.items {
            if self.item_weight(&line.item).is_none() {
                return Err(integrity(format!(
                    "'{owner}' equipment package item '{}' does not resolve",
                    line.item
                )));
            }
            if line.count == 0 {
                return Err(integrity(format!(
                    "'{owner}' equipment package item '{}' has a zero count",
                    line.item
                )));
            }
        }
        Ok(())
    }

    /// The highest level any shipped class's advancement table defines —
    /// the level slots the ruleset registers.
    pub fn max_advancement_level(&self) -> u32 {
        self.classes
            .iter()
            .map(|c| c.level_cap())
            .max()
            .unwrap_or(1)
    }

    /// Every level at which some shipped class opens its subclass choice.
    pub fn subclass_levels(&self) -> Vec<u32> {
        let mut levels: Vec<u32> = self
            .classes
            .iter()
            .flat_map(|c| c.subclass_levels())
            .collect();
        levels.sort_unstable();
        levels.dedup();
        levels
    }

    pub fn skill(&self, id: &str) -> Option<&SkillRecord> {
        self.skills.iter().find(|r| r.id == id)
    }
    pub fn score_method(&self, id: &str) -> Option<&ScoreMethodRecord> {
        self.scores.methods.iter().find(|r| r.id == id)
    }
    pub fn species(&self, id: &str) -> Option<&SpeciesRecord> {
        self.species.iter().find(|r| r.id == id)
    }
    pub fn background(&self, id: &str) -> Option<&BackgroundRecord> {
        self.backgrounds.iter().find(|r| r.id == id)
    }
    pub fn feat(&self, id: &str) -> Option<&FeatRecord> {
        self.feats.iter().find(|r| r.id == id)
    }
    pub fn class(&self, id: &str) -> Option<&ClassRecord> {
        self.classes.iter().find(|r| r.id == id)
    }
    pub fn subclass(&self, id: &str) -> Option<&SubclassRecord> {
        self.subclasses.iter().find(|r| r.id == id)
    }
    pub fn weapon(&self, id: &str) -> Option<&WeaponRecord> {
        self.equipment.weapons.iter().find(|r| r.id == id)
    }
    pub fn armor(&self, id: &str) -> Option<&ArmorRecord> {
        self.equipment.armor.iter().find(|r| r.id == id)
    }
    pub fn gear(&self, id: &str) -> Option<&GearRecord> {
        self.equipment.gear.iter().find(|r| r.id == id)
    }
    pub fn tool(&self, id: &str) -> Option<&GearRecord> {
        self.equipment.tools.iter().find(|r| r.id == id)
    }
    /// Any carried item's display name.
    pub fn item_name(&self, id: &str) -> Option<String> {
        self.weapon(id)
            .map(|r| r.name.clone())
            .or_else(|| self.armor(id).map(|r| r.name.clone()))
            .or_else(|| self.gear(id).map(|r| r.name.clone()))
            .or_else(|| self.tool(id).map(|r| r.name.clone()))
    }
    /// Any carried item's weight in pounds.
    pub fn item_weight(&self, id: &str) -> Option<f64> {
        self.weapon(id)
            .map(|r| r.weight_lb)
            .or_else(|| self.armor(id).map(|r| r.weight_lb))
            .or_else(|| self.gear(id).map(|r| r.weight_lb))
            .or_else(|| self.tool(id).map(|r| r.weight_lb))
    }
}
