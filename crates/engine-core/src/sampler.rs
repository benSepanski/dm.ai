//! The standalone pick source for random suggestion sources and fuzz
//! drivers. Pure arithmetic over a caller-supplied seed — randomness is
//! data here, never a dependency or an entropy source: the same seed
//! always yields the same picks, which is what makes random mints
//! reproducible and replay-safe. The legality filter is deliberately NOT
//! part of this type: callers choose what list to sample from
//! (available-only for the mint path; everything for fuzz walks).

/// A deterministic sequence of picks over caller-supplied seeds
/// (SplitMix64 — a well-mixed, dependency-free generator; statistical
/// quality far beyond what shuffling option lists needs).
#[derive(Debug, Clone)]
pub struct Sampler {
    state: u64,
}

impl Sampler {
    pub fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    /// Seed from arbitrary key text (e.g. a client request ID): FNV-1a
    /// into the SplitMix64 state. Deterministic across runs and platforms.
    pub fn from_key(key: &str) -> Self {
        let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
        for byte in key.as_bytes() {
            hash ^= u64::from(*byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
        Self { state: hash }
    }

    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9e37_79b9_7f4a_7c15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^ (z >> 31)
    }

    /// An index into a list of `len` items; `None` for an empty list.
    /// Modulo bias is negligible at option-catalog sizes (len << 2^64).
    pub fn pick_index(&mut self, len: usize) -> Option<usize> {
        if len == 0 {
            return None;
        }
        Some((self.next_u64() % len as u64) as usize)
    }

    /// A reference to one item, or `None` for an empty list.
    pub fn pick<'a, T>(&mut self, items: &'a [T]) -> Option<&'a T> {
        self.pick_index(items.len()).map(|i| &items[i])
    }

    /// The items in a fresh uniform order (Fisher–Yates over a copy).
    pub fn shuffled<T: Clone>(&mut self, items: &[T]) -> Vec<T> {
        let mut out = items.to_vec();
        for i in (1..out.len()).rev() {
            let j = (self.next_u64() % (i as u64 + 1)) as usize;
            out.swap(i, j);
        }
        out
    }
}
