//! Shared helpers for the checks suite (workspace discovery; later: spawning
//! the real server binary for the crash harness and API checks).
#![forbid(unsafe_code)]

use std::path::PathBuf;

/// Absolute path to the workspace root, resolved from this crate's manifest.
pub fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("checks crate sits directly under the workspace root")
        .to_path_buf()
}

/// Load and parse the repo's rules-data files through the ruleset crate —
/// exactly what the server and wasm builds embed.
pub fn load_rules_data() -> ruleset_pf2e::RulesData {
    let root = workspace_root().join("rules-data");
    let read = |name: &str| std::fs::read_to_string(root.join(name)).expect("rules-data file");
    let manifest = read("manifest.json");
    let ancestries = read("ancestries.json");
    let heritages = read("heritages.json");
    let ancestry_feats = read("ancestry-feats.json");
    let backgrounds = read("backgrounds.json");
    let classes = read("classes.json");
    let class_feats = read("class-feats.json");
    let general_feats = read("general-feats.json");
    let skills = read("skills.json");
    let equipment = read("equipment.json");
    ruleset_pf2e::RulesData::parse(&ruleset_pf2e::RulesDataFiles {
        manifest: &manifest,
        ancestries: &ancestries,
        heritages: &heritages,
        ancestry_feats: &ancestry_feats,
        backgrounds: &backgrounds,
        classes: &classes,
        class_feats: &class_feats,
        general_feats: &general_feats,
        skills: &skills,
        equipment: &equipment,
    })
    .expect("rules data parses and passes integrity checks")
}
