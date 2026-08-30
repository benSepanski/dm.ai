//! Random-mint rows of the roster-ergonomics architecture: seed-sweep
//! soundness (every shipped class fills, finalizes, replays verify-clean),
//! mint determinism (same entropy ⇒ identical character), mint variety
//! (no slot pinned to the published suggestion), and the name-pool
//! failure fixtures (malformed ⇒ typed error and nothing written;
//! absent/empty pool ⇒ default-pool name). Tests land with the feature
//! tickets; this file is wired first per ticket 1.
