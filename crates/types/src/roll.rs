//! Recorded inputs: dice as the faces that came up. A rolled set is groups
//! of faces on a die of `sides` sides, tagged with who produced them; a
//! roll slot declares its shape (sides, dice per group, groups). Nothing
//! here knows what a group is for or what a total means — that is a
//! ruleset's derivation over the faces. No seed lives on these types: the
//! log is the record, and replay reads faces, never regenerates them.

use serde::{Deserialize, Serialize};

/// Who produced a rolled set's faces. Exactly two: the app's own dice, or
/// physical dice the player entered by hand.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
#[serde(rename_all = "snake_case")]
pub enum RollOrigin {
    /// Rolled by the app (the server's entropy) — minted only by the
    /// server's dice helper.
    App,
    /// Entered by the player from physical dice.
    Entered,
}

/// One rolled set: the faces, grouped as the slot's shape groups them
/// (six groups of four for a 4d6-six-times method; one group of one for a
/// single hit die).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[cfg_attr(feature = "ts", derive(tsify::Tsify))]
pub struct RolledSet {
    pub groups: Vec<Vec<u8>>,
    pub origin: RollOrigin,
}

/// The one game-free shape check every roll slot's `apply` calls: each
/// set has exactly `groups` groups of exactly `dice` faces, every face in
/// `1..=sides`, and there is at least one set. Returns the rule broken,
/// render-ready.
pub fn check_roll_shape(sides: u8, dice: u8, groups: u8, sets: &[RolledSet]) -> Result<(), String> {
    if sets.is_empty() {
        return Err("a roll records at least one set".into());
    }
    for (n, set) in sets.iter().enumerate() {
        if set.groups.len() != groups as usize {
            return Err(format!(
                "set {} has {} groups; this roll takes {groups}",
                n + 1,
                set.groups.len()
            ));
        }
        for (g, faces) in set.groups.iter().enumerate() {
            if faces.len() != dice as usize {
                return Err(format!(
                    "set {} group {} has {} dice; this roll takes {dice} per group",
                    n + 1,
                    g + 1,
                    faces.len()
                ));
            }
            if let Some(face) = faces.iter().find(|f| **f < 1 || **f > sides) {
                return Err(format!(
                    "a face of {face} is not on a {sides}-sided die (set {}, group {})",
                    n + 1,
                    g + 1
                ));
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn set(groups: Vec<Vec<u8>>) -> RolledSet {
        RolledSet {
            groups,
            origin: RollOrigin::Entered,
        }
    }

    #[test]
    fn shape_check_names_the_rule_broken() {
        assert!(check_roll_shape(6, 4, 2, &[]).is_err());
        assert!(
            check_roll_shape(6, 4, 2, &[set(vec![vec![1, 2, 3, 4], vec![6, 6, 6, 6]])]).is_ok()
        );
        let err = check_roll_shape(6, 4, 2, &[set(vec![vec![1, 2, 3, 4]])]).unwrap_err();
        assert!(err.contains("groups"), "{err}");
        let err =
            check_roll_shape(6, 4, 2, &[set(vec![vec![1, 2, 3], vec![1, 2, 3, 4]])]).unwrap_err();
        assert!(err.contains("dice"), "{err}");
        let err = check_roll_shape(6, 4, 1, &[set(vec![vec![1, 2, 3, 7]])]).unwrap_err();
        assert!(err.contains("7") && err.contains("6-sided"), "{err}");
        let err = check_roll_shape(10, 1, 1, &[set(vec![vec![0]])]).unwrap_err();
        assert!(err.contains("0"), "{err}");
    }

    #[test]
    fn serializes_legibly() {
        let s = serde_json::to_string(&set(vec![vec![6, 5, 3, 1]])).unwrap();
        assert_eq!(s, r#"{"groups":[[6,5,3,1]],"origin":"entered"}"#);
    }
}
