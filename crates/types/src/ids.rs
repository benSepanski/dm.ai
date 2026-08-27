//! Newtyped identifiers. All are opaque strings on the wire; meaning lives
//! with whoever minted them (server: characters; ruleset: slots/options;
//! client: decision IDs for idempotent confirms).

use serde::{Deserialize, Serialize};

macro_rules! string_id {
    ($(#[$doc:meta])* $name:ident) => {
        $(#[$doc])*
        #[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
        #[cfg_attr(feature = "ts", derive(tsify::Tsify))]
        #[serde(transparent)]
        pub struct $name(pub String);

        impl $name {
            pub fn new(value: impl Into<String>) -> Self {
                Self(value.into())
            }
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }

        impl std::fmt::Display for $name {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                f.write_str(&self.0)
            }
        }
    };
}

string_id!(
    /// A character (draft or finalized); also its filename stem in the data dir.
    CharacterId
);
string_id!(
    /// A ruleset-defined choice slot, e.g. `pf2e.ancestry` or `pf2e.boosts.free`.
    SlotId
);
string_id!(
    /// A stable rules-data record ID, e.g. `ancestry.dwarf`.
    OptionId
);
string_id!(
    /// Client-minted per confirm; a replayed ID appends nothing (idempotency).
    DecisionId
);
string_id!(
    /// A wizard step grouping slots, e.g. `ancestry` or `equipment`.
    StepId
);
