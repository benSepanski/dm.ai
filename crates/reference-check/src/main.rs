//! reference-check — compares shipped rules-data against a pinned,
//! content-hash-verified Foundry pf2e snapshot and writes the committed
//! attestation. Skeleton for now; the real tool lands with ticket T6.

fn main() {
    eprintln!(
        "reference-check: not yet implemented (chargen-content ticket T6).\n\
         Will fetch the pinned ground-truth tag into a gitignored cache and \
         write rules-data/attestation.json."
    );
    std::process::exit(2);
}
