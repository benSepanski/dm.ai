//! The one place entropy enters the app (dnd-dice architecture). A roll
//! route draws faces here, tags the set as the app's own dice, and records
//! it through the ordinary validated write; nothing else in the workspace
//! rolls. Two sources stand behind one trait: the operating system's bytes
//! for play, and a keyed deterministic mixer for checks and scripted
//! sessions (`--dice-seed`). The draw carries a key — the character id and
//! the decision id — so the deterministic source yields independent
//! streams per roll with no shared mutable state, and a retried decision
//! id yields the same faces by construction. No seed is ever written to a
//! file, and no read path ever regenerates a roll: the log is the record.

use types::{RollOrigin, RolledSet};

/// What a draw is for: the character and the decision it will become.
/// The production source ignores it; the deterministic source mixes it.
pub struct RollKey<'a> {
    pub character: &'a str,
    pub decision: &'a str,
}

#[derive(Debug, thiserror::Error)]
#[error("{0}")]
pub struct EntropyError(pub String);

pub trait Entropy: Send + Sync {
    /// `count` faces on a `sides`-sided die, each uniform in `1..=sides`.
    fn faces(&self, key: &RollKey, sides: u8, count: usize) -> Result<Vec<u8>, EntropyError>;
}

/// The operating system's entropy: rejection-sampled bytes, never a
/// modulo over the full range (which would bias toward low faces).
pub struct OsEntropy;

impl Entropy for OsEntropy {
    fn faces(&self, _key: &RollKey, sides: u8, count: usize) -> Result<Vec<u8>, EntropyError> {
        let sides = u16::from(sides.max(1));
        // Accept a byte only below the largest multiple of `sides` that fits.
        let limit = 256 - (256 % sides);
        let mut out = Vec::with_capacity(count);
        let mut buf = [0u8; 64];
        while out.len() < count {
            // The one sanctioned entropy draw in the workspace.
            #[allow(clippy::disallowed_methods)]
            getrandom::getrandom(&mut buf).map_err(|e| EntropyError(e.to_string()))?;
            for b in buf {
                if out.len() == count {
                    break;
                }
                let b = u16::from(b);
                if b < limit {
                    out.push((b % sides) as u8 + 1);
                }
            }
        }
        Ok(out)
    }
}

/// A deterministic source for checks and scripted sessions: the root seed
/// mixed with the key through SplitMix64, so streams are independent
/// across characters and rolls and identical for an identical key.
pub struct SeededEntropy {
    pub seed: u64,
}

impl Entropy for SeededEntropy {
    fn faces(&self, key: &RollKey, sides: u8, count: usize) -> Result<Vec<u8>, EntropyError> {
        let sides = u64::from(sides.max(1));
        let mut state = self.seed;
        for part in [key.character, key.decision] {
            state = splitmix64(state ^ fnv1a(part));
        }
        // Rejection sampling over the mixer's 64-bit output.
        let limit = u64::MAX - (u64::MAX % sides);
        let mut out = Vec::with_capacity(count);
        while out.len() < count {
            state = splitmix64(state);
            if state < limit {
                out.push((state % sides) as u8 + 1);
            }
        }
        Ok(out)
    }
}

fn splitmix64(x: u64) -> u64 {
    let mut z = x.wrapping_add(0x9E37_79B9_7F4A_7C15);
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
    z ^ (z >> 31)
}

fn fnv1a(s: &str) -> u64 {
    let mut h: u64 = 0xCBF2_9CE4_8422_2325;
    for b in s.bytes() {
        h ^= u64::from(b);
        h = h.wrapping_mul(0x0100_0000_01B3);
    }
    h
}

/// Draw one rolled set of `groups` groups of `dice` faces and tag it as
/// the app's own dice — the only place that tag is minted.
pub fn roll_set(
    entropy: &dyn Entropy,
    key: &RollKey,
    sides: u8,
    dice: u8,
    groups: u8,
) -> Result<RolledSet, EntropyError> {
    let per_group = usize::from(dice);
    let faces = entropy.faces(key, sides, per_group * usize::from(groups))?;
    Ok(RolledSet {
        groups: faces.chunks(per_group.max(1)).map(|c| c.to_vec()).collect(),
        origin: RollOrigin::App,
    })
}

/// Whether a client-submitted history claims the app's own tag — refused
/// at the routes: app-rolled sets come only from the roll route.
pub fn claims_app_origin(sets: &[RolledSet]) -> bool {
    sets.iter().any(|s| s.origin == RollOrigin::App)
}

/// Stamp every submitted set as entered by hand: the client never names
/// an origin the server has not produced.
pub fn stamp_entered(sets: &[RolledSet]) -> Vec<RolledSet> {
    sets.iter()
        .map(|s| RolledSet {
            groups: s.groups.clone(),
            origin: RollOrigin::Entered,
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key<'a>(c: &'a str, d: &'a str) -> RollKey<'a> {
        RollKey {
            character: c,
            decision: d,
        }
    }

    #[test]
    fn seeded_draws_are_identical_for_an_identical_key_and_differ_otherwise() {
        let a = SeededEntropy { seed: 7 };
        let x = a.faces(&key("ysolde", "r1"), 6, 24).unwrap();
        let y = a.faces(&key("ysolde", "r1"), 6, 24).unwrap();
        assert_eq!(x, y);
        assert_ne!(x, a.faces(&key("ysolde", "r2"), 6, 24).unwrap());
        assert_ne!(x, a.faces(&key("marrow", "r1"), 6, 24).unwrap());
        assert_ne!(
            x,
            SeededEntropy { seed: 8 }
                .faces(&key("ysolde", "r1"), 6, 24)
                .unwrap()
        );
        assert!(x.iter().all(|f| (1..=6).contains(f)));
    }

    #[test]
    fn seeded_streams_cover_every_face_and_show_no_obvious_correlation() {
        // Over many keys, every face appears roughly equally and adjacent
        // draws do not repeat more often than chance (a bounded sample).
        let e = SeededEntropy { seed: 42 };
        let mut counts = [0usize; 10];
        let mut repeats = 0usize;
        let mut total = 0usize;
        for i in 0..400 {
            let c = format!("c{i}");
            let faces = e.faces(&key(&c, "d"), 10, 50).unwrap();
            for w in faces.windows(2) {
                total += 1;
                if w[0] == w[1] {
                    repeats += 1;
                }
            }
            for f in faces {
                counts[usize::from(f) - 1] += 1;
            }
        }
        let expected = 400.0 * 50.0 / 10.0;
        for c in counts {
            assert!((c as f64 - expected).abs() < expected * 0.15, "{counts:?}");
        }
        // Chance of a repeat on a d10 is 10%; allow a wide band.
        let rate = repeats as f64 / total as f64;
        assert!((0.06..0.14).contains(&rate), "repeat rate {rate}");
    }

    #[test]
    fn os_faces_are_on_the_die() {
        let faces = OsEntropy.faces(&key("c", "d"), 6, 200).unwrap();
        assert_eq!(faces.len(), 200);
        assert!(faces.iter().all(|f| (1..=6).contains(f)));
        let set = roll_set(&OsEntropy, &key("c", "d"), 10, 1, 1).unwrap();
        assert_eq!(set.groups.len(), 1);
        assert_eq!(set.groups[0].len(), 1);
        assert!(claims_app_origin(std::slice::from_ref(&set)));
        assert!(!claims_app_origin(&stamp_entered(&[set])));
    }
}
