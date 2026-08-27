//! Pathfinder 2e ruleset: slot definitions, option catalogs, validators,
//! and sheet derivation. Rules-data records are passed in as bytes/values —
//! this crate never touches the filesystem.
//!
//! Layering inside the crate (enforced by checks/crate_layering.rs):
//! kind modules (ancestry, background, class, feats, skills, equipment)
//! never import each other; kinds -> mechanics -> engine-core.
#![forbid(unsafe_code)]
