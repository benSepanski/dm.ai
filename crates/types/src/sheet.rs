//! The presentation contract: a derived sheet as labeled, render-ready
//! values. The UI (web today, TUI someday) renders this without knowing any
//! game semantics; every number was computed inside the engine.

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct SheetView {
    pub name: String,
    /// Identity line(s), e.g. "Dwarf (Rock Dwarf) Fighter 1".
    pub summary: Vec<String>,
    pub sections: Vec<SheetSection>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct SheetSection {
    pub title: String,
    pub entries: Vec<SheetEntry>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct SheetEntry {
    pub label: String,
    /// Render-ready value, e.g. "18" or "+7" or "2 Bulk, 3 L".
    pub value: String,
    /// Optional provenance/breakdown, e.g. "10 + 2 Dex + 4 scale mail + 2 trained".
    pub detail: Option<String>,
}

impl SheetView {
    /// Look up an entry by section and label (test/verify convenience).
    pub fn entry(&self, section: &str, label: &str) -> Option<&SheetEntry> {
        self.sections
            .iter()
            .find(|s| s.title == section)?
            .entries
            .iter()
            .find(|e| e.label == label)
    }
}
