//! The generic decision-log engine: choice slots, slot-graph resolution,
//! log append/replay, validation into the checklist, the derivation fold,
//! and the draft lifecycle.
//!
//! No I/O, no clock, no randomness, no game vocabulary. Ancestry,
//! background, class are not concepts here — each is a slot a ruleset
//! defines, differing only in what its options unlock and contribute.
#![forbid(unsafe_code)]

mod engine;
mod sampler;
mod slot;

pub use engine::*;
pub use sampler::*;
pub use slot::*;

#[cfg(test)]
mod tests;
