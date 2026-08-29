//! Boundary-crossing shapes: IDs, decisions, checklist entries, the
//! presentation contract, and the WASM/API message enums. The single source
//! of truth for every shape that crosses a process or language boundary.
//!
//! This crate is identity-blind and game-vocabulary-free: it knows slots,
//! decisions, and sheets as presentation, never PF2e semantics.
//!
//! The `ts` feature adds tsify derives so the wasm crate can weld TypeScript
//! declarations into its generated `.d.ts`; native consumers never enable it.
#![forbid(unsafe_code)]

mod api;
mod checklist;
mod decision;
mod engine_msg;
mod ids;
mod roster;
mod scoped;
mod sheet;
mod version;
mod wizard;

pub use api::*;
pub use checklist::*;
pub use decision::*;
pub use engine_msg::*;
pub use ids::*;
pub use roster::*;
pub use scoped::*;
pub use sheet::*;
pub use version::*;
pub use wizard::*;
