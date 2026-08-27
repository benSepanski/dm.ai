//! The generic decision-log engine: choice slots, slot-graph resolution,
//! log append/replay, validation into the checklist, the derivation fold,
//! and the draft lifecycle.
//!
//! No I/O, no clock, no randomness, no game vocabulary. Ancestry,
//! background, class are not concepts here — each is a slot a ruleset
//! defines.
#![forbid(unsafe_code)]
