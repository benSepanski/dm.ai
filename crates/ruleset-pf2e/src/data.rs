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
    /// The fixed skill-feat grant, as a general-feat ID (e.g.
    /// "feat.skill.battle-medicine"; integrity-checked to resolve in
    /// `general_feats`). May be empty when the feat follows the skill
    /// sub-choice (`skill_feat_by_choice`). The sheet renders the
    /// referenced feat record's name unless `skill_feat_display`
    /// overrides it.
    pub skill_feat: String,
    /// Display override for a parameterized fixed grant (Nomad's
    /// "Assurance (Survival)"): rendered instead of the referenced feat
    /// record's name. Empty means no override; only meaningful alongside
    /// a non-empty `skill_feat` (integrity-checked).
    #[serde(default)]
    pub skill_feat_display: String,
    /// Choice-dependent skill feat: skill ID (must appear in
    /// `skill_choice`) → general-feat ID (integrity-checked to resolve in
    /// `general_feats`). When non-empty, the sheet's background
    /// skill-feat entry follows the chosen skill.
    #[serde(default)]
    pub skill_feat_by_choice: std::collections::BTreeMap<String, String>,
    /// Display overrides for parameterized choice-dependent grants
    /// (Scholar's "Assurance (Arcana)"): skill ID → rendered label. Keys
    /// must be a subset of `skill_feat_by_choice` keys
    /// (integrity-checked); a missing key renders the referenced feat
    /// record's name.
    #[serde(default)]
    pub skill_feat_display_by_choice: std::collections::BTreeMap<String, String>,
    pub source: SourceRef,
}

impl BackgroundRecord {
    /// The rendered label of the fixed skill-feat grant: the display
    /// override when present, else the referenced feat record's name.
    /// None when there is no fixed grant (`skill_feat` empty) or the ID
    /// dangles (shipped data cannot dangle — integrity rejects it).
    pub fn skill_feat_label(&self, data: &RulesData) -> Option<String> {
        if self.skill_feat.is_empty() {
            return None;
        }
        if !self.skill_feat_display.is_empty() {
            return Some(self.skill_feat_display.clone());
        }
        data.general_feat(&self.skill_feat).map(|f| f.name.clone())
    }

    /// The rendered label of the choice-dependent skill-feat grant under
    /// the chosen `skill`, with the same override-then-name fallback.
    pub fn skill_feat_label_for_choice(&self, data: &RulesData, skill: &str) -> Option<String> {
        if let Some(display) = self.skill_feat_display_by_choice.get(skill) {
            return Some(display.clone());
        }
        let id = self.skill_feat_by_choice.get(skill)?;
        data.general_feat(id).map(|f| f.name.clone())
    }
}

fn default_true() -> bool {
    true
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
    /// Whether the class grants a level-1 class feat (Fighter yes, Wizard
    /// no — the advancement table states it discretely). Defaults true.
    #[serde(default = "default_true")]
    pub level1_class_feat: bool,
    /// Prepared spellcasting, when the class has it (the Wizard). Absent
    /// for non-casters; counts and proficiencies are transcription from
    /// the class's printed spellcasting entry.
    #[serde(default)]
    pub spellcasting: Option<SpellcastingDef>,
    /// True while the class deliberately ships without a suggested build
    /// (the Wizard until `wizard-content` adds its quick build); integrity
    /// then allows the absent block instead of failing.
    #[serde(default)]
    pub quick_build_deferred: bool,
    /// The app-authored suggested build the quick-build planner interprets
    /// directly (no per-slot suggest hook). Integrity requires every
    /// shipped class to carry one. See [`SuggestedBuild`].
    #[serde(default)]
    pub suggested_build: Option<SuggestedBuild>,
    pub source: SourceRef,
}

/// The suggested-build block: dm.ai-curated choices (spec req 7 **[call]**
/// — PF2e publishes only the class kit and key attribute as quick-build
/// anchors, so everything else here is app-authored content, never
/// presented as Paizo-published). One entry per slot the build fills.
///
/// Design rule for authoring: prefer options that open no chooser chains;
/// when a chosen option does open a sub-slot (Skilled Human's skill
/// chooser), the block MUST carry a candidates entry for that sub-slot so
/// the expansion stays deterministic and complete. A slot the block cannot
/// parameterize simply stays open on the checklist.
#[derive(Debug, Clone, Deserialize)]
pub struct SuggestedBuild {
    /// One-line intent note for hand-inspection; not rendered.
    #[serde(default)]
    pub description: String,
    pub entries: Vec<SuggestedBuildEntry>,
}

/// One slot's suggestion: ordered candidate option IDs (the planner takes
/// the first legal one, or the first legal N for a state-dependent
/// multi-pick — author the list longer than needed), or free text for a
/// text slot. Exactly one of the two forms (integrity-checked); an empty
/// candidates list is legal (a multi slot whose count may be zero, or a
/// deliberately-empty list slot).
#[derive(Debug, Clone, Deserialize)]
pub struct SuggestedBuildEntry {
    pub slot: String,
    #[serde(default)]
    pub candidates: Vec<String>,
    #[serde(default)]
    pub text: Option<String>,
}

/// A prepared-caster class's spellcasting shape, as the printed class entry
/// states it: tradition, prepared counts, spellbook size, and the school
/// extra slot. Transcription, never invention.
#[derive(Debug, Clone, Deserialize)]
pub struct SpellcastingDef {
    /// "arcane" (the only shipped tradition this slice).
    pub tradition: String,
    pub attack_proficiency: String,
    pub dc_proficiency: String,
    /// Cantrips prepared each day.
    pub cantrips_prepared: u32,
    /// Rank-1 spell slots (before the school's extra slot).
    pub rank1_slots: u32,
    /// Spellbook contents at level 1: freely chosen cantrips and rank-1
    /// spells, plus rank-1 spells added from the school's curriculum.
    pub spellbook_cantrips: u32,
    pub spellbook_rank1: u32,
    pub spellbook_curriculum_rank1: u32,
    /// Whether the arcane school grants the extra curriculum-only
    /// preparations (one cantrip, one spell of each castable rank — the
    /// printed wizard-spellcasting rule).
    pub school_extra_slot: bool,
}

/// One printed heightening entry on a spell. Exactly the two printed
/// shapes — "Heightened (+N)" and "Heightened (Nth)" — and nothing more
/// (architecture: the schema admits no other variants).
#[derive(Debug, Clone, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum HeighteningEntry {
    /// "Heightened (+step)": applies per `step` ranks above the base.
    PerRank { step: u32, text: String },
    /// "Heightened (rank)": applies at exactly that rank.
    Fixed { rank: u32, text: String },
}

#[derive(Debug, Clone, Deserialize)]
pub struct SpellRecord {
    pub id: String,
    pub name: String,
    /// 0 = cantrip.
    pub rank: u32,
    /// Focus spells never appear in spellbook catalogs; they are granted
    /// (by a school) and cast from the focus pool.
    #[serde(default)]
    pub focus: bool,
    pub traditions: Vec<String>,
    pub traits: Vec<String>,
    /// Action cost as printed: "1", "2", "3", "1 to 3", "reaction", "free".
    pub actions: String,
    /// The defense the spell targets, as printed: "AC" for attack-roll
    /// spells, "basic Reflex" and kin for saves; absent when none.
    #[serde(default)]
    pub defense: Option<String>,
    #[serde(default)]
    pub range: Option<String>,
    #[serde(default)]
    pub area: Option<String>,
    #[serde(default)]
    pub targets: Option<String>,
    #[serde(default)]
    pub duration: Option<String>,
    pub text: String,
    #[serde(default)]
    pub heightening: Vec<HeighteningEntry>,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ThesisRecord {
    pub id: String,
    pub name: String,
    pub text: String,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SchoolRecord {
    pub id: String,
    pub name: String,
    pub text: String,
    /// Curriculum spell IDs by rank, as the school's printed list states.
    pub curriculum_cantrips: Vec<String>,
    pub curriculum_rank1: Vec<String>,
    /// The school's granted focus spell (a `focus: true` spell record).
    pub focus_spell: String,
    pub source: SourceRef,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SpellsFile {
    pub spells: Vec<SpellRecord>,
    pub theses: Vec<ThesisRecord>,
    pub schools: Vec<SchoolRecord>,
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
    /// Choice-in-a-feat proficiency override (Canny Acumen): the record
    /// opens a chooser over `targets`; the pick folds as a concrete
    /// `ProficiencyOverride` at `rank`.
    ChooseProficiencyOverride {
        targets: Vec<String>,
        rank: String,
        source_label: String,
    },
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
    pub spells: &'a str,
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
    pub spells: SpellsFile,
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
            spells: parse("spells.json", files.spells)?,
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
            .chain(self.spells.spells.iter().map(|r| r.id.as_str()))
            .chain(self.spells.theses.iter().map(|r| r.id.as_str()))
            .chain(self.spells.schools.iter().map(|r| r.id.as_str()))
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
            let feat_resolves = |id: &str| self.general_feats.iter().any(|f| f.id == id);
            if !b.skill_feat.is_empty() && !feat_resolves(&b.skill_feat) {
                return Err(DataError::Integrity(format!(
                    "background '{}' skill_feat '{}' does not resolve in \
                     general_feats",
                    b.id, b.skill_feat
                )));
            }
            if !b.skill_feat_display.is_empty() && b.skill_feat.is_empty() {
                return Err(DataError::Integrity(format!(
                    "background '{}' carries skill_feat_display without a \
                     skill_feat to display",
                    b.id
                )));
            }
            for (key, feat) in &b.skill_feat_by_choice {
                if !b.skill_choice.contains(key) {
                    return Err(DataError::Integrity(format!(
                        "background '{}' skill_feat_by_choice key '{key}' is not \
                         in its skill_choice list",
                        b.id
                    )));
                }
                if !feat_resolves(feat) {
                    return Err(DataError::Integrity(format!(
                        "background '{}' skill_feat_by_choice feat '{feat}' does \
                         not resolve in general_feats",
                        b.id
                    )));
                }
            }
            for key in b.skill_feat_display_by_choice.keys() {
                if !b.skill_feat_by_choice.contains_key(key) {
                    return Err(DataError::Integrity(format!(
                        "background '{}' skill_feat_display_by_choice key '{key}' \
                         has no matching skill_feat_by_choice entry",
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
            if c.quick_build_deferred {
                if c.suggested_build.is_some() {
                    return Err(DataError::Integrity(format!(
                        "class '{}' both defers quick build and carries a \
                         suggested_build — drop the flag",
                        c.id
                    )));
                }
            } else {
                self.check_suggested_build(c)?;
            }
            if let Some(sc) = &c.spellcasting {
                if sc.tradition != "arcane" {
                    return Err(DataError::Integrity(format!(
                        "class '{}' names unshipped tradition '{}'",
                        c.id, sc.tradition
                    )));
                }
            }
        }
        self.check_spells()?;
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
                let prof_targets: &[String] = match e {
                    Effect::ProficiencyOverride { target, .. } => std::slice::from_ref(target),
                    Effect::ChooseProficiencyOverride { targets, .. } => {
                        if targets.is_empty() {
                            return Err(DataError::Integrity(format!(
                                "record '{id}' choose_proficiency_override has no targets"
                            )));
                        }
                        targets
                    }
                    _ => &[],
                };
                for t in prof_targets {
                    if !matches!(t.as_str(), "fortitude" | "reflex" | "will" | "perception") {
                        return Err(DataError::Integrity(format!(
                            "record '{id}' proficiency override names unknown target '{t}'"
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

    /// Spell/thesis/school integrity: every cross-reference resolves to a
    /// shipped spell of the right rank and kind; heightening entries carry
    /// text; focus spells stay out of the spellbook catalogs by
    /// construction (the `focus` flag).
    fn check_spells(&self) -> Result<(), DataError> {
        for s in &self.spells.spells {
            if s.traditions.is_empty() {
                return Err(DataError::Integrity(format!(
                    "spell '{}' lists no traditions",
                    s.id
                )));
            }
            for h in &s.heightening {
                let (ok, what) = match h {
                    HeighteningEntry::PerRank { step, text } => {
                        (*step >= 1 && !text.trim().is_empty(), "per_rank")
                    }
                    HeighteningEntry::Fixed { rank, text } => {
                        (*rank > s.rank && !text.trim().is_empty(), "fixed")
                    }
                };
                if !ok {
                    return Err(DataError::Integrity(format!(
                        "spell '{}' has a malformed {what} heightening entry",
                        s.id
                    )));
                }
            }
        }
        let spell = |id: &str| self.spells.spells.iter().find(|s| s.id == id);
        for school in &self.spells.schools {
            for (list, rank) in [
                (&school.curriculum_cantrips, 0u32),
                (&school.curriculum_rank1, 1u32),
            ] {
                for id in list {
                    let Some(s) = spell(id) else {
                        return Err(DataError::Integrity(format!(
                            "school '{}' curriculum references unknown spell '{id}'",
                            school.id
                        )));
                    };
                    if s.rank != rank || s.focus {
                        return Err(DataError::Integrity(format!(
                            "school '{}' curriculum entry '{id}' is not a rank-{rank} \
                             non-focus spell",
                            school.id
                        )));
                    }
                }
            }
            match spell(&school.focus_spell) {
                Some(s) if s.focus => {}
                Some(_) => {
                    return Err(DataError::Integrity(format!(
                        "school '{}' focus_spell '{}' is not a focus spell",
                        school.id, school.focus_spell
                    )));
                }
                None => {
                    return Err(DataError::Integrity(format!(
                        "school '{}' focus_spell '{}' does not resolve",
                        school.id, school.focus_spell
                    )));
                }
            }
        }
        Ok(())
    }

    /// Suggested-build integrity: every class ships a block, every entry
    /// names a known slot, every candidate ID resolves (records, kit
    /// options, attribute/proficiency/language option IDs), and each entry
    /// is either candidates or text, never both. A dangling reference is a
    /// build-time refusal — runtime never discovers it.
    fn check_suggested_build(&self, c: &ClassRecord) -> Result<(), DataError> {
        let Some(block) = &c.suggested_build else {
            return Err(DataError::Integrity(format!(
                "class '{}' has no suggested_build block — every shipped class \
                 must carry one (quick build, spec req 7)",
                c.id
            )));
        };
        if block.entries.is_empty() {
            return Err(DataError::Integrity(format!(
                "class '{}' suggested_build has no entries",
                c.id
            )));
        }
        let known_slots = crate::mechanics::known_slot_ids();
        let mut seen_slots: BTreeSet<&str> = BTreeSet::new();
        for entry in &block.entries {
            if !known_slots.contains(&entry.slot.as_str()) {
                return Err(DataError::Integrity(format!(
                    "class '{}' suggested_build references unknown slot '{}'",
                    c.id, entry.slot
                )));
            }
            if !seen_slots.insert(&entry.slot) {
                return Err(DataError::Integrity(format!(
                    "class '{}' suggested_build has two entries for slot '{}'",
                    c.id, entry.slot
                )));
            }
            match &entry.text {
                Some(text) => {
                    if !entry.candidates.is_empty() {
                        return Err(DataError::Integrity(format!(
                            "class '{}' suggested_build entry for '{}' carries \
                             both text and candidates",
                            c.id, entry.slot
                        )));
                    }
                    if text.trim().is_empty() {
                        return Err(DataError::Integrity(format!(
                            "class '{}' suggested_build entry for '{}' has empty text",
                            c.id, entry.slot
                        )));
                    }
                }
                None => {
                    for candidate in &entry.candidates {
                        if !self.suggested_candidate_resolves(candidate) {
                            return Err(DataError::Integrity(format!(
                                "class '{}' suggested_build candidate '{candidate}' \
                                 (slot '{}') does not resolve to any shipped \
                                 record or option",
                                c.id, entry.slot
                            )));
                        }
                    }
                }
            }
        }
        Ok(())
    }

    /// Whether a suggested-build candidate ID resolves in shipped content:
    /// a record ID, a kit-option ID, the no-kit sentinel, an attribute
    /// option (`attr.*`), a proficiency-target option (`prof.*`), or a
    /// language option (`lang.*`, name-derived from an ancestry's lists).
    fn suggested_candidate_resolves(&self, candidate: &str) -> bool {
        if candidate.starts_with("attr.") {
            return crate::mechanics::ALL_ATTRIBUTES
                .into_iter()
                .any(|a| a.option_id().as_str() == candidate);
        }
        if let Some(target) = candidate.strip_prefix("prof.") {
            return matches!(target, "fortitude" | "reflex" | "will" | "perception");
        }
        if candidate.starts_with("lang.") {
            return self.ancestries.iter().any(|a| {
                a.languages
                    .iter()
                    .chain(a.additional_languages.iter())
                    .any(|lang| crate::mechanics::lang_option_id(lang) == candidate)
            });
        }
        if candidate == "equipment.no-kit" {
            return true;
        }
        self.ancestries.iter().any(|r| r.id == candidate)
            || self.spells.spells.iter().any(|r| r.id == candidate)
            || self.spells.theses.iter().any(|r| r.id == candidate)
            || self.spells.schools.iter().any(|r| r.id == candidate)
            || self.heritages.iter().any(|r| r.id == candidate)
            || self.ancestry_feats.iter().any(|r| r.id == candidate)
            || self.backgrounds.iter().any(|r| r.id == candidate)
            || self.classes.iter().any(|r| r.id == candidate)
            || self.class_feats.iter().any(|r| r.id == candidate)
            || self.general_feats.iter().any(|r| r.id == candidate)
            || self.skills.iter().any(|r| r.id == candidate)
            || self.equipment.weapons.iter().any(|r| r.id == candidate)
            || self.equipment.armor.iter().any(|r| r.id == candidate)
            || self.equipment.shields.iter().any(|r| r.id == candidate)
            || self.equipment.gear.iter().any(|r| r.id == candidate)
            || self.equipment.kits.iter().any(|r| r.id == candidate)
            || self
                .equipment
                .kits
                .iter()
                .flat_map(|k| k.options.iter())
                .any(|o| o.id == candidate)
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
    pub fn spell(&self, id: &str) -> Option<&SpellRecord> {
        self.spells.spells.iter().find(|r| r.id == id)
    }
    pub fn thesis(&self, id: &str) -> Option<&ThesisRecord> {
        self.spells.theses.iter().find(|r| r.id == id)
    }
    pub fn school(&self, id: &str) -> Option<&SchoolRecord> {
        self.spells.schools.iter().find(|r| r.id == id)
    }
}
