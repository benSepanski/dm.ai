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
    /// Prior shipped data versions this one supersedes, oldest first. Every
    /// entry must have its ID set recorded in rules-data/shipped-versions.json
    /// (lint-enforced); the server treats these as "older known" versions.
    #[serde(default)]
    pub supersedes: Vec<String>,
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
    /// Languages a character of this ancestry may pick as bonus languages
    /// (the "additional languages" list under each Player Core ancestry).
    /// The chooser slot grants max(0, Int modifier) + bonus-language effects
    /// picks from this list; an empty list means no chooser exists for the
    /// ancestry. Entries must not repeat `languages` (integrity-checked).
    #[serde(default)]
    pub additional_languages: Vec<String>,
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

/// Feat catalog keys — the namespace shared by `AncestryFeatRecord.ancestry`
/// and `HeritageRecord.feat_ancestries`. Convention (integrity-enforced):
/// a key is either a full ancestry record ID (`"ancestry.elf"`, exactly as
/// base ancestry feats already use) or a versatile heritage's *short key* —
/// the last dot-segment of the heritage's record ID
/// (`"heritage.versatile.aiuvarin"` → `"aiuvarin"`). Versatile-heritage
/// feats set `ancestry` to that short key; a versatile heritage lists in
/// `feat_ancestries` its own short key plus any full ancestry IDs whose
/// feat catalogs it opens (e.g. Aiuvarin → `["aiuvarin", "ancestry.elf"]`).
#[derive(Debug, Clone, Deserialize)]
pub struct HeritageRecord {
    pub id: String,
    /// The ancestry this heritage belongs to, or `null` for a versatile
    /// heritage — selectable at the heritage step under *any* ancestry.
    /// Data files write `"ancestry": null` explicitly for readability.
    #[serde(default)]
    pub ancestry: Option<String>,
    pub name: String,
    pub text: String,
    /// Extra ancestry-feat catalog keys unioned into the ancestry-feat
    /// options while this heritage is chosen (see the catalog-key
    /// convention above). The base ancestry's own feats are always in the
    /// union and need not be listed.
    #[serde(default)]
    pub feat_ancestries: Vec<String>,
    #[serde(default)]
    pub effects: Vec<Effect>,
    pub source: SourceRef,
}

impl HeritageRecord {
    /// Versatile heritages are the ones unbound from an ancestry.
    pub fn is_versatile(&self) -> bool {
        self.ancestry.is_none()
    }
    /// The short key versatile-heritage feats use as their catalog key:
    /// the last dot-segment of the heritage's record ID.
    pub fn short_key(&self) -> &str {
        self.id.rsplit('.').next().unwrap_or(&self.id)
    }
}

/// One prerequisite on a feat. `kind` selects how (and whether) it is
/// evaluated; the extra fields carry that kind's data:
/// - `{"kind": "spellcasting", "text": "requires a spellcasting class
///   feature"}` — never satisfiable in this data version; always greys.
/// - `{"kind": "attribute", "attribute": "con", "value": 2}` — the folded
///   attribute modifier must be >= `value`.
/// - `{"kind": "trained_skill", "skill": "skill.acrobatics"}` — the folded
///   state must be trained (or better) in that skill.
///
/// Unknown kinds are annotations only: shown, never evaluated. `text` is
/// optional; when absent, a human-readable description is generated from
/// the kind's fields.
#[derive(Debug, Clone, Deserialize)]
pub struct Prerequisite {
    pub kind: String,
    #[serde(default)]
    pub text: String,
    #[serde(default)]
    pub attribute: Option<Attribute>,
    #[serde(default)]
    pub value: Option<i32>,
    #[serde(default)]
    pub skill: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct AncestryFeatRecord {
    pub id: String,
    /// Feat catalog key: a full ancestry ID, or a versatile heritage's
    /// short key (see the convention on [`HeritageRecord`]).
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
    /// The fixed trained-skill grant. May be empty ("") when the
    /// background trains a chosen skill instead (`skill_choice`).
    pub skill: String,
    /// When non-empty, the background opens a sub-choice slot
    /// ("pf2e.background.skill") to pick exactly one of these skill IDs;
    /// the pick feeds the same collision/replacement machinery as the
    /// fixed grant. A background must have `skill` or `skill_choice`.
    #[serde(default)]
    pub skill_choice: Vec<String>,
    /// The fixed Lore grant. Empty when `lore_player_named` is true.
    pub lore: String,
    /// When true, the background opens a text slot
    /// ("pf2e.background.lore") where the player names the Lore; it lands
    /// trained on the sheet as "<Typed> Lore".
    #[serde(default)]
    pub lore_player_named: bool,
    /// The fixed skill-feat display string. May be empty when the feat
    /// follows the skill sub-choice (`skill_feat_by_choice`).
    pub skill_feat: String,
    /// Choice-dependent skill feat: skill ID (must appear in
    /// `skill_choice`) → skill-feat display string. When non-empty, the
    /// sheet's background skill-feat entry follows the chosen skill.
    /// (Display strings for now; feat IDs arrive with the skill-feat
    /// catalog.)
    #[serde(default)]
    pub skill_feat_by_choice: std::collections::BTreeMap<String, String>,
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
    /// Conditional sense upgrade (the Aiuvarin/Dromaar rule). Semantics:
    /// grants `otherwise` normally; when the base ancestry's own senses
    /// already include `otherwise`, grants `sense` instead; when they
    /// already include `sense`, grants nothing new. E.g. Dromaar's
    /// low-light vision is `{ "type": "sense_upgrade", "sense":
    /// "darkvision", "otherwise": "low-light vision" }`. Only the
    /// ancestry's *base* senses are consulted, never other effects.
    SenseUpgrade { sense: String, otherwise: String },
    /// An unarmed attack (Razortooth Goblin jaws). With `range` set it is
    /// a *ranged* unarmed attack (Seedpod): the attack roll uses Dex and
    /// no attribute is added to damage (it is not a thrown weapon). With
    /// `replaces_fist` it replaces the built-in Fist entry on the sheet
    /// instead of adding a new one (Iron Fists).
    UnarmedAttack {
        name: String,
        damage: String,
        traits: Vec<String>,
        #[serde(default)]
        range: Option<String>,
        #[serde(default)]
        replaces_fist: bool,
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
    /// A non-empty `from` restricts the choice to those skill IDs (the
    /// Hold Mark pattern); empty means any skill.
    ChooseSkills {
        count: u32,
        source_label: String,
        #[serde(default)]
        from: Vec<String>,
    },
    /// Gain a Lore skill the player names (the Gnome Obsession pattern):
    /// opens the text slot "pf2e.skills.feat-lore"; the typed name lands
    /// trained on the sheet as "<Typed> Lore" with `source_label` as its
    /// source. At most one record in a build may carry this effect.
    ChooseLore { source_label: String },
    /// Choose N entries from a named catalog (opens a chooser slot). An
    /// empty catalog in this data version makes the carrying option
    /// unavailable, with an explanation.
    ChooseFromCatalog { catalog: String, count: u32 },
    /// Set a save or Perception to a named proficiency rank at level 1
    /// (Canny Acumen → expert). `target` is one of "fortitude", "reflex",
    /// "will", "perception"; sheet derivation takes max(class rank,
    /// override) — an override never lowers a rank.
    ProficiencyOverride { target: String, rank: String },
    /// Extra bonus-language picks (Nomadic Halfling's +2, Multilingual):
    /// raises the "pf2e.ancestry.languages" chooser's count.
    BonusLanguages { count: u32 },
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

        // Feat catalog keys (see the convention on HeritageRecord): a key
        // is valid iff it is a full ancestry ID or a versatile heritage's
        // short key.
        let valid_catalog_key = |key: &str| {
            self.ancestries.iter().any(|a| a.id == key)
                || self
                    .heritages
                    .iter()
                    .any(|h| h.is_versatile() && h.short_key() == key)
        };
        for h in &self.heritages {
            // `ancestry: null` marks a versatile heritage — legal; a named
            // ancestry must resolve.
            if let Some(ancestry) = &h.ancestry {
                if !self.ancestries.iter().any(|a| &a.id == ancestry) {
                    return Err(DataError::Integrity(format!(
                        "heritage '{}' references unknown ancestry '{ancestry}'",
                        h.id
                    )));
                }
            }
            for key in &h.feat_ancestries {
                if !valid_catalog_key(key) {
                    return Err(DataError::Integrity(format!(
                        "heritage '{}' feat_ancestries key '{key}' is neither an \
                         ancestry ID nor a versatile heritage's short key",
                        h.id
                    )));
                }
            }
        }
        for f in &self.ancestry_feats {
            if !valid_catalog_key(&f.ancestry) {
                return Err(DataError::Integrity(format!(
                    "ancestry feat '{}' catalog key '{}' is neither an ancestry \
                     ID nor a versatile heritage's short key",
                    f.id, f.ancestry
                )));
            }
        }
        for a in &self.ancestries {
            for lang in &a.additional_languages {
                if lang.trim().is_empty() {
                    return Err(DataError::Integrity(format!(
                        "ancestry '{}' has an empty additional language",
                        a.id
                    )));
                }
                if a.languages.contains(lang) {
                    return Err(DataError::Integrity(format!(
                        "ancestry '{}' lists '{lang}' both as a starting and an \
                         additional language",
                        a.id
                    )));
                }
            }
        }
        for b in &self.backgrounds {
            if b.skill.is_empty() && b.skill_choice.is_empty() {
                return Err(DataError::Integrity(format!(
                    "background '{}' has neither a fixed skill nor a skill choice",
                    b.id
                )));
            }
            if !b.skill.is_empty() && !self.skills.iter().any(|s| s.id == b.skill) {
                return Err(DataError::Integrity(format!(
                    "background '{}' references unknown skill '{}'",
                    b.id, b.skill
                )));
            }
            for s in &b.skill_choice {
                if !self.skills.iter().any(|sk| sk.id == *s) {
                    return Err(DataError::Integrity(format!(
                        "background '{}' skill_choice references unknown skill '{s}'",
                        b.id
                    )));
                }
            }
            for key in b.skill_feat_by_choice.keys() {
                if !b.skill_choice.contains(key) {
                    return Err(DataError::Integrity(format!(
                        "background '{}' skill_feat_by_choice key '{key}' is not \
                         in its skill_choice list",
                        b.id
                    )));
                }
            }
            if b.lore_player_named && !b.lore.is_empty() {
                return Err(DataError::Integrity(format!(
                    "background '{}' is lore_player_named but also carries a \
                     fixed lore '{}'",
                    b.id, b.lore
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
        let effect_carriers = self
            .heritages
            .iter()
            .map(|h| (h.id.as_str(), &h.effects))
            .chain(
                self.ancestry_feats
                    .iter()
                    .map(|f| (f.id.as_str(), &f.effects)),
            )
            .chain(
                self.general_feats
                    .iter()
                    .map(|f| (f.id.as_str(), &f.effects)),
            );
        for (id, effects) in effect_carriers {
            for e in effects {
                let skill_refs: &[String] = match e {
                    Effect::GrantSkills { skills, .. } => skills,
                    Effect::ChooseSkills { from, .. } => from,
                    _ => &[],
                };
                for s in skill_refs {
                    if !self.skills.iter().any(|sk| sk.id == *s) {
                        return Err(DataError::Integrity(format!(
                            "record '{id}' effect references unknown skill '{s}'"
                        )));
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
