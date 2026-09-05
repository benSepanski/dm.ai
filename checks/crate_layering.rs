//! Crate layering — the workspace dependency graph is an explicit edge
//! allowlist (architecture doc, "Constraints emitted"). A new crate or a new
//! edge is a reviewed edit to this file, never silent accretion.
//!
//! Also enforced here, per the same table:
//! - crates named common/utils/helpers/shared are rejected
//! - engine crates (`types`, `engine-core`, `ruleset-*`) carry no I/O,
//!   clock, randomness, env, or unsafe (source scan + dependency ban)
//! - only `wasm` has wasm-bindgen in its resolved tree; `server` never does
//! - ruleset kind modules never import each other (kinds -> mechanics ->
//!   engine-core; module-level import scan)
//! - no storage-document type is exported from the server's persistence
//!   module (wire != storage spot-assertion)

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::path::Path;

use cargo_metadata::{CargoOpt, MetadataCommand};

/// Workspace-internal edges. Sorted, exact: extra or missing edges fail.
const ALLOWED_INTERNAL_EDGES: &[(&str, &str)] = &[
    ("checks", "engine-core"),
    ("checks", "ruleset-pf2e"),
    ("checks", "types"),
    ("engine-core", "types"),
    // Verification-only dev tool; nothing depends on it (the exact
    // allowlist makes any inbound edge an unexpected-edge failure).
    ("reference-check", "ruleset-pf2e"),
    ("reference-check", "types"),
    ("ruleset-pf2e", "engine-core"),
    ("ruleset-pf2e", "types"),
    ("server", "engine-core"),
    ("server", "ruleset-pf2e"),
    ("server", "types"),
    ("wasm", "engine-core"),
    ("wasm", "ruleset-pf2e"),
    ("wasm", "types"),
];

const BANNED_CRATE_NAMES: &[&str] = &["common", "utils", "helpers", "shared"];

/// Crates whose code must stay pure: no fs, net, clock, env, randomness.
const ENGINE_CRATES: &[&str] = &["types", "engine-core", "ruleset-pf2e"];

/// Tokens banned from engine-crate sources. Coarse text scan by design —
/// the goal is tripping review, not outsmarting obfuscation.
const BANNED_ENGINE_TOKENS: &[&str] = &[
    "std::fs",
    "std::net",
    "std::env",
    "SystemTime",
    "Instant::now",
    "unsafe ",
];

/// Ruleset option-kind modules: no kind may reference another kind.
const RULESET_KIND_MODULES: &[&str] = &[
    "ancestry",
    "background",
    "class",
    "feats",
    "skills",
    "equipment",
];

fn metadata() -> cargo_metadata::Metadata {
    MetadataCommand::new()
        .manifest_path(checks::workspace_root().join("Cargo.toml"))
        .features(CargoOpt::AllFeatures)
        .exec()
        .expect("cargo metadata")
}

#[test]
fn internal_dependency_graph_matches_allowlist() {
    let meta = metadata();
    let workspace: BTreeSet<&str> = meta
        .workspace_packages()
        .iter()
        .map(|p| p.name.as_str())
        .collect();

    let mut edges = BTreeSet::new();
    for pkg in meta.workspace_packages() {
        for dep in &pkg.dependencies {
            if workspace.contains(dep.name.as_str()) {
                edges.insert((pkg.name.to_string(), dep.name.clone()));
            }
        }
    }

    let allowed: BTreeSet<(String, String)> = ALLOWED_INTERNAL_EDGES
        .iter()
        .map(|(a, b)| (a.to_string(), b.to_string()))
        .collect();

    let unexpected: Vec<_> = edges.difference(&allowed).collect();
    let missing: Vec<_> = allowed.difference(&edges).collect();
    assert!(
        unexpected.is_empty() && missing.is_empty(),
        "workspace dependency graph diverges from the allowlist in \
         checks/crate_layering.rs\n  unexpected edges: {unexpected:?}\n  \
         missing edges: {missing:?}\n(a new crate or edge is a deliberate, \
         reviewed edit to this file)"
    );
}

#[test]
fn no_banned_crate_names() {
    let meta = metadata();
    for pkg in meta.workspace_packages() {
        let name = pkg.name.to_lowercase();
        assert!(
            !BANNED_CRATE_NAMES
                .iter()
                .any(|b| name == *b || name.ends_with(&format!("-{b}"))),
            "crate name '{}' is banned: shared functionality gets a \
             purpose-named crate with one narrow contract, born by extraction \
             from a second concrete use",
            pkg.name
        );
    }
}

#[test]
fn engine_crates_have_no_impure_dependencies() {
    let meta = metadata();
    let resolve = meta.resolve.as_ref().expect("resolved dep graph");
    let by_id: BTreeMap<_, _> = meta.packages.iter().map(|p| (&p.id, p)).collect();

    for root in ENGINE_CRATES {
        let root_pkg = meta
            .workspace_packages()
            .into_iter()
            .find(|p| p.name.as_str() == *root)
            .unwrap_or_else(|| panic!("engine crate {root} missing from workspace"));

        // Walk the resolved graph from the engine crate.
        let mut stack = vec![&root_pkg.id];
        let mut seen = BTreeSet::new();
        while let Some(id) = stack.pop() {
            if !seen.insert(id) {
                continue;
            }
            let node = resolve
                .nodes
                .iter()
                .find(|n| &n.id == id)
                .expect("node in resolve graph");
            for dep in &node.deps {
                // Dev-dependencies (proptest et al.) never ship in the
                // engine; only normal edges matter for purity.
                if !dep
                    .dep_kinds
                    .iter()
                    .any(|k| k.kind == cargo_metadata::DependencyKind::Normal)
                {
                    continue;
                }
                let name = by_id[&dep.pkg].name.as_str();
                assert!(
                    !name.starts_with("rand"),
                    "{root} transitively depends on '{name}': randomness is \
                     banned in engine crates (derivation is a pure fold)"
                );
                stack.push(&dep.pkg);
            }
        }
    }
}

#[test]
fn server_tree_has_no_wasm_bindgen() {
    // The `ts` feature on `types` is only for the wasm crate. Workspace-wide
    // metadata unifies features, so ask cargo for the server's own
    // feature-resolved tree instead.
    let out = std::process::Command::new(env!("CARGO"))
        .args(["tree", "-p", "server", "-e", "normal", "--prefix", "none"])
        .current_dir(checks::workspace_root())
        .output()
        .expect("cargo tree");
    assert!(
        out.status.success(),
        "cargo tree failed: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    let tree = String::from_utf8_lossy(&out.stdout);
    for banned in ["wasm-bindgen", "tsify"] {
        assert!(
            !tree.contains(banned),
            "server's dependency tree contains '{banned}' — only the wasm \
             crate may use wasm-bindgen/tsify"
        );
    }
}

fn rust_sources(dir: &Path) -> Vec<(std::path::PathBuf, String)> {
    let mut out = Vec::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(d) = stack.pop() {
        let Ok(entries) = fs::read_dir(&d) else {
            continue;
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().is_some_and(|e| e == "rs") {
                let src = fs::read_to_string(&path).expect("readable source");
                out.push((path, src));
            }
        }
    }
    out
}

#[test]
fn engine_sources_are_pure() {
    let root = checks::workspace_root();
    for krate in ENGINE_CRATES {
        for (path, src) in rust_sources(&root.join("crates").join(krate).join("src")) {
            for token in BANNED_ENGINE_TOKENS {
                assert!(
                    !src.contains(token),
                    "{} contains banned token '{token}': engine crates carry \
                     no I/O, clock, env, or unsafe",
                    path.display()
                );
            }
        }
    }
}

#[test]
fn ruleset_kind_modules_do_not_reference_each_other() {
    let root = checks::workspace_root();
    for ruleset_src in [root.join("crates/ruleset-pf2e/src")] {
        for kind in RULESET_KIND_MODULES {
            let kind_dir = ruleset_src.join(kind);
            let kind_file = ruleset_src.join(format!("{kind}.rs"));
            let mut sources = rust_sources(&kind_dir);
            if kind_file.exists() {
                let src = fs::read_to_string(&kind_file).expect("readable source");
                sources.push((kind_file, src));
            }
            for (path, src) in sources {
                for other in RULESET_KIND_MODULES {
                    if other == kind {
                        continue;
                    }
                    for pattern in [
                        format!("crate::{other}::"),
                        format!("use crate::{other}"),
                        format!("super::{other}::"),
                    ] {
                        assert!(
                            !src.contains(&pattern),
                            "{} references sibling kind module '{other}' \
                             ({pattern}): kinds -> mechanics -> engine-core, \
                             no kind<->kind edges. Query engine-core about \
                             the log or folded state instead.",
                            path.display()
                        );
                    }
                }
            }
        }
    }
}

#[test]
fn storage_documents_stay_private_to_persistence() {
    // Wire != storage: nothing in the server's persistence module may be
    // `pub` to the whole crate's consumers, and storage-document names must
    // not appear in the types crate. Spot assertion — visibility does the
    // real enforcement at compile time.
    let root = checks::workspace_root();
    let persistence = root.join("crates/server/src/persistence");
    let persistence_file = root.join("crates/server/src/persistence.rs");
    let mut sources = rust_sources(&persistence);
    if persistence_file.exists() {
        let src = fs::read_to_string(&persistence_file).expect("readable source");
        sources.push((persistence_file, src));
    }
    for (path, src) in sources {
        for line in src.lines() {
            let trimmed = line.trim_start();
            let declares_type =
                trimmed.starts_with("pub struct") || trimmed.starts_with("pub enum");
            assert!(
                !declares_type,
                "{}: '{}' — storage documents are pub(crate) at most and \
                 never leave persistence; responses are built from view \
                 types in `types`",
                path.display(),
                trimmed
            );
        }
    }

    for (path, src) in rust_sources(&root.join("crates/types/src")) {
        for banned in ["StorageDoc", "StoredCharacter", "CharacterDocV"] {
            assert!(
                !src.contains(banned),
                "{} exports storage-document name '{banned}': wire types are \
                 not storage types",
                path.display()
            );
        }
    }
}

// ---- level-up architecture rows: level is derived; the marker is storage-private; one dialog machine ----

/// Level is a fact of the log, never a constant: the ruleset carries no
/// `const LEVEL` / `LEVEL:` token, and the wire types carry no
/// `finalized_through` (the marker is storage-private to persistence).
#[test]
fn level_is_derived_and_the_marker_is_storage_private() {
    let root = checks::workspace_root();
    for (path, src) in rust_sources(&root.join("crates/ruleset-pf2e/src")) {
        for token in ["const LEVEL", "LEVEL:"] {
            assert!(
                !src.contains(token),
                "{} contains '{token}': level is derived from the log's advance decisions, never a constant",
                path.display()
            );
        }
    }
    for (path, src) in rust_sources(&root.join("crates/types/src")) {
        assert!(
            !src.contains("finalized_through"),
            "{} names the finalized marker: it is storage-private, never on the wire",
            path.display()
        );
    }
}

/// One dialog machine, structural half: no level-specific wizard exists.
/// No `ui/src` file is named after level-up, no component named LevelUp*
/// is exported, and the wizard component contains no phase/level branch
/// token — it renders whatever steps the projection says are live.
#[test]
fn ui_has_no_level_specific_wizard() {
    let root = checks::workspace_root().join("ui/src");
    let mut stack = vec![root.clone()];
    while let Some(dir) = stack.pop() {
        for entry in std::fs::read_dir(&dir).unwrap().flatten() {
            let path = entry.path();
            if path.is_dir() {
                if path.file_name().is_some_and(|n| n == "pkg") {
                    continue;
                }
                stack.push(path);
                continue;
            }
            let name = path.file_name().unwrap().to_string_lossy().to_string();
            if !(name.ends_with(".ts") || name.ends_with(".tsx")) {
                continue;
            }
            assert!(
                !name.contains("LevelUp") && !name.to_lowercase().contains("level-up"),
                "{name}: no level-specific UI file — the wizard renders live steps"
            );
            let src = std::fs::read_to_string(&path).unwrap();
            for token in [
                "export function LevelUp",
                "export const LevelUp",
                "export class LevelUp",
            ] {
                assert!(
                    !src.contains(token),
                    "{name} exports a LevelUp component — one dialog machine"
                );
            }
        }
    }
    let wizard = std::fs::read_to_string(root.join("Wizard.tsx")).unwrap();
    for token in ["phase", "level ===", "isLeveling"] {
        assert!(
            !wizard.contains(token),
            "Wizard.tsx contains '{token}': the wizard never branches on a phase or level"
        );
    }
    // Gains and deltas render through the one shared diff table.
    assert!(
        wizard.contains("SheetDiffTable"),
        "the level-up gains render through the shared SheetDiffTable, not a new diff component"
    );
}
