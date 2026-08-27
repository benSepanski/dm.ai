//! Boundary-crossing shapes: IDs, decisions, checklist entries, the
//! presentation contract, and the WASM/API message enums. The single source
//! of truth for every shape that crosses a process or language boundary.
//!
//! This crate is identity-blind and game-vocabulary-free: it knows slots,
//! decisions, and sheets as presentation, never PF2e semantics.
#![forbid(unsafe_code)]
