//! The dm.ai table server: axum routes over the native engine, crash-safe
//! JSON persistence, and the built UI served from the binary.
//!
//! Wire types are not storage types: the structs serialized to disk live in
//! `persistence` and are `pub(crate)` at most; route handlers build
//! responses only from view types in `types`.

fn main() {
    println!("dm.ai server skeleton — routes land with ticket 6");
}
