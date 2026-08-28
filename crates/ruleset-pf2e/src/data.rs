//! Rules-data records: parsed from the versioned JSON files, passed in as
//! strings (this crate never touches a filesystem). Every record carries a
//! stable ID and per-record license metadata.

use std::collections::BTreeSet;

use serde::Deserialize;

use crate::mechanics::Attribute;

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
    pub license_notice: LicenseNotice,
}

#[derive(Debug, Clone, Deserialize)]
pub struct LicenseNotice {
    pub orc_notice: String,
    pub attribution: String,
    pub reserved: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AncestryRecord {
    pub id: String,
    pub name: String,
    pub hp: u32,
    pub size: String,
    pub speed: i32,
    pub boosts: Vec<Attribute>,
    pub free_boosts: u32,
    pub flaws: Vec<Attribute>,
    pub languages: Vec<String>,
    pub traits: Vec<String>,
    pub senses: Vec<String>,
    pub specials: Vec<SpecialAbility>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SpecialAbility {
    pub name: String,
    pub text: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct HeritageRecord {
    pub id: String,
    pub ancestry: String,
    pub name: String,
    pub text: String,
    #[serde(default)]
    pub effects: Vec<Effect>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Prerequisite {
    pub kind: String,
    pub text: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AncestryFeatRecord {
    pub id: String,
    pub ancestry: String,
    pub level: u32,
    pub name: String,
    #[serde(default)]
    pub prerequisites: Vec<Prerequisite>,
    pub text: String,
    #[serde(default)]
    pub effects: Vec<Effect>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct BackgroundRecord {
    pub id: String,
    pub name: String,
    pub text: String,
    pub boost_choice: Vec<Attribute>,
    pub skill: String,
    pub lore: String,
    pub skill_feat: String,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ClassRecord {
    pub id: String,
    pub name: String,
    pub text: String,
    pub key_attribute_choice: Vec<Attribute>,
    pub hp_per_level: u32,
    pub proficiencies: ClassProficiencies,
    pub class_skill_choice: Vec<String>,
    pub additional_skills_base: u32,
    pub features: Vec<SpecialAbility>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ClassProficiencies {
    pub perception: String,
    pub fortitude: String,
    pub reflex: String,
    pub will: String,
    pub simple_weapons: String,
    pub martial_weapons: String,
    pub advanced_weapons: String,
    pub unarmed_attacks: String,
    pub armor: String,
    pub unarmored_defense: String,
    pub class_dc: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ClassFeatRecord {
    pub id: String,
    pub class: String,
    pub level: u32,
    pub name: String,
    pub actions: String,
    #[serde(default)]
    pub prerequisites: Vec<Prerequisite>,
    pub requirements: Option<String>,
    pub text: String,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct GeneralFeatRecord {
    pub id: String,
    pub level: u32,
    pub name: String,
    #[serde(default)]
    pub prerequisites: Vec<Prerequisite>,
    pub text: String,
    #[serde(default)]
    pub effects: Vec<Effect>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SkillRecord {
    pub id: String,
    pub name: String,
    pub attribute: Attribute,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct EquipmentFile {
    pub weapons: Vec<WeaponRecord>,
    pub armor: Vec<ArmorRecord>,
    pub shields: Vec<ShieldRecord>,
    pub gear: Vec<GearRecord>,
    pub kits: Vec<KitRecord>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct WeaponRecord {
    pub id: String,
    pub name: String,
    pub price_cp: u32,
    pub damage: Option<String>,
    pub bulk: String,
    pub hands: Option<String>,
    pub group: String,
    pub category: String,
    pub range: Option<String>,
    pub traits: Vec<String>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ArmorRecord {
    pub id: String,
    pub name: String,
    pub price_cp: u32,
    pub ac_bonus: i32,
    pub dex_cap: i32,
    pub check_penalty: i32,
    pub speed_penalty: i32,
    pub str_req: i32,
    pub bulk: String,
    pub group: String,
    pub category: String,
    pub traits: Vec<String>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ShieldRecord {
    pub id: String,
    pub name: String,
    pub price_cp: u32,
    pub ac_bonus: i32,
    pub speed_penalty: i32,
    pub bulk: String,
    pub hardness: u32,
    pub hp: u32,
    pub bt: u32,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct GearRecord {
    pub id: String,
    pub name: String,
    pub price_cp: u32,
    pub bulk: String,
    pub text: String,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct KitRecord {
    pub id: String,
    pub name: String,
    pub class: String,
    pub price_cp: u32,
    pub contents: Vec<String>,
    pub options: Vec<KitOption>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct KitOption {
    pub id: String,
    pub name: String,
    pub price_cp: u32,
    pub items: Vec<String>,
}

/// Mechanical effects a record can carry. Content stays data; the ruleset
/// interprets these few effect kinds.
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Effect {
    /// Heritage overrides the ancestry HP contribution (Unbreakable Goblin).
    AncestryHpOverride { value: u32 },
    /// Extra max HP per level (Toughness).
    HpPerLevel { value: u32 },
    /// Flat Speed increase (Nimble Elf, Fleet).
    SpeedBonus { value: i32 },
    /// Ignore armor's Speed reduction (Unburdened Iron).
    IgnoreArmorSpeedPenalty,
    /// Gain a sense (Cavern Elf darkvision).
    Sense { value: String },
    /// An extra unarmed attack (Razortooth Goblin jaws).
    UnarmedAttack {
        name: String,
        damage: String,
        traits: Vec<String>,
    },
    /// Become trained in these specific skills; collisions with existing
    /// training open replacement-skill slots (the PF2e replacement rule).
    GrantSkills {
        skills: Vec<String>,
        source_label: String,
    },
    /// Gain a Lore skill.
    GrantLore { name: String },
    /// Become trained in N skills of your choice (opens a chooser slot).
    ChooseSkills { count: u32, source_label: String },
    /// Choose N entries from a named catalog (opens a chooser slot). An
    /// empty catalog in this data version makes the carrying option
    /// unavailable, with an explanation.
    ChooseFromCatalog { catalog: String, count: u32 },
}

/// The raw JSON file contents, as shipped.
pub struct RulesDataFiles<'a> {
    pub manifest: &'a str,
    pub ancestries: &'a str,
    pub heritages: &'a str,
    pub ancestry_feats: &'a str,
    pub backgrounds: &'a str,
    pub classes: &'a str,
    pub class_feats: &'a str,
    pub general_feats: &'a str,
    pub skills: &'a str,
    pub equipment: &'a str,
}

#[derive(Debug, Clone)]
pub struct RulesData {
    pub manifest: Manifest,
    pub ancestries: Vec<AncestryRecord>,
    pub heritages: Vec<HeritageRecord>,
    pub ancestry_feats: Vec<AncestryFeatRecord>,
    pub backgrounds: Vec<BackgroundRecord>,
    pub classes: Vec<ClassRecord>,
    pub class_feats: Vec<ClassFeatRecord>,
    pub general_feats: Vec<GeneralFeatRecord>,
    pub skills: Vec<SkillRecord>,
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

impl RulesData {
    pub fn parse(files: &RulesDataFiles<'_>) -> Result<Self, DataError> {
        let data = RulesData {
            manifest: parse("manifest.json", files.manifest)?,
            ancestries: parse("ancestries.json", files.ancestries)?,
            heritages: parse("heritages.json", files.heritages)?,
            ancestry_feats: parse("ancestry-feats.json", files.ancestry_feats)?,
            backgrounds: parse("backgrounds.json", files.backgrounds)?,
            classes: parse("classes.json", files.classes)?,
            class_feats: parse("class-feats.json", files.class_feats)?,
            general_feats: parse("general-feats.json", files.general_feats)?,
            skills: parse("skills.json", files.skills)?,
            equipment: parse("equipment.json", files.equipment)?,
        };
        data.check_integrity()?;
        Ok(data)
    }

    /// The integrity rules the rules-data lint asserts: IDs unique and
    /// well-formed, every cross-reference resolvable.
    pub fn check_integrity(&self) -> Result<(), DataError> {
        let mut ids: BTreeSet<&str> = BTreeSet::new();
        let all_ids: Vec<&str> = self
            .ancestries
            .iter()
            .map(|r| r.id.as_str())
            .chain(self.heritages.iter().map(|r| r.id.as_str()))
            .chain(self.ancestry_feats.iter().map(|r| r.id.as_str()))
            .chain(self.backgrounds.iter().map(|r| r.id.as_str()))
            .chain(self.classes.iter().map(|r| r.id.as_str()))
            .chain(self.class_feats.iter().map(|r| r.id.as_str()))
            .chain(self.general_feats.iter().map(|r| r.id.as_str()))
            .chain(self.skills.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.weapons.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.armor.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.shields.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.gear.iter().map(|r| r.id.as_str()))
            .chain(self.equipment.kits.iter().map(|r| r.id.as_str()))
            .collect();
        for id in &all_ids {
            if !ids.insert(id) {
                return Err(DataError::Integrity(format!("duplicate record id '{id}'")));
            }
            if id.trim().is_empty() || id.contains(char::is_whitespace) {
                return Err(DataError::Integrity(format!("malformed record id '{id}'")));
            }
        }

        for h in &self.heritages {
            if !self.ancestries.iter().any(|a| a.id == h.ancestry) {
                return Err(DataError::Integrity(format!(
                    "heritage '{}' references unknown ancestry '{}'",
                    h.id, h.ancestry
                )));
            }
        }
        for f in &self.ancestry_feats {
            if !self.ancestries.iter().any(|a| a.id == f.ancestry) {
                return Err(DataError::Integrity(format!(
                    "ancestry feat '{}' references unknown ancestry '{}'",
                    f.id, f.ancestry
                )));
            }
        }
        for b in &self.backgrounds {
            if !self.skills.iter().any(|s| s.id == b.skill) {
                return Err(DataError::Integrity(format!(
                    "background '{}' references unknown skill '{}'",
                    b.id, b.skill
                )));
            }
        }
        for c in &self.classes {
            for s in &c.class_skill_choice {
                if !self.skills.iter().any(|sk| sk.id == *s) {
                    return Err(DataError::Integrity(format!(
                        "class '{}' references unknown skill '{s}'",
                        c.id
                    )));
                }
            }
        }
        for f in &self.class_feats {
            if !self.classes.iter().any(|c| c.id == f.class) {
                return Err(DataError::Integrity(format!(
                    "class feat '{}' references unknown class '{}'",
                    f.id, f.class
                )));
            }
        }
        for feat in &self.ancestry_feats {
            for e in &feat.effects {
                if let Effect::GrantSkills { skills, .. } = e {
                    for s in skills {
                        if !self.skills.iter().any(|sk| sk.id == *s) {
                            return Err(DataError::Integrity(format!(
                                "feat '{}' grants unknown skill '{s}'",
                                feat.id
                            )));
                        }
                    }
                }
            }
        }
        let item_exists = |id: &str| {
            self.equipment.weapons.iter().any(|r| r.id == id)
                || self.equipment.armor.iter().any(|r| r.id == id)
                || self.equipment.shields.iter().any(|r| r.id == id)
                || self.equipment.gear.iter().any(|r| r.id == id)
        };
        for kit in &self.equipment.kits {
            if !self.classes.iter().any(|c| c.id == kit.class) {
                return Err(DataError::Integrity(format!(
                    "kit '{}' references unknown class '{}'",
                    kit.id, kit.class
                )));
            }
            for item in kit
                .contents
                .iter()
                .chain(kit.options.iter().flat_map(|o| o.items.iter()))
            {
                if !item_exists(item) {
                    return Err(DataError::Integrity(format!(
                        "kit '{}' references unknown item '{item}'",
                        kit.id
                    )));
                }
            }
        }
        Ok(())
    }

    pub fn ancestry(&self, id: &str) -> Option<&AncestryRecord> {
        self.ancestries.iter().find(|r| r.id == id)
    }
    pub fn heritage(&self, id: &str) -> Option<&HeritageRecord> {
        self.heritages.iter().find(|r| r.id == id)
    }
    pub fn ancestry_feat(&self, id: &str) -> Option<&AncestryFeatRecord> {
        self.ancestry_feats.iter().find(|r| r.id == id)
    }
    pub fn background(&self, id: &str) -> Option<&BackgroundRecord> {
        self.backgrounds.iter().find(|r| r.id == id)
    }
    pub fn class(&self, id: &str) -> Option<&ClassRecord> {
        self.classes.iter().find(|r| r.id == id)
    }
    pub fn class_feat(&self, id: &str) -> Option<&ClassFeatRecord> {
        self.class_feats.iter().find(|r| r.id == id)
    }
    pub fn general_feat(&self, id: &str) -> Option<&GeneralFeatRecord> {
        self.general_feats.iter().find(|r| r.id == id)
    }
    pub fn skill(&self, id: &str) -> Option<&SkillRecord> {
        self.skills.iter().find(|r| r.id == id)
    }
    pub fn kit(&self, id: &str) -> Option<&KitRecord> {
        self.equipment.kits.iter().find(|r| r.id == id)
    }
}
