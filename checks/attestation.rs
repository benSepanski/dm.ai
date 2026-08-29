//! Attestation chain (architecture: chargen-content). T1 lands the offline
//! hygiene rows: the ground-truth cache is never committed and CI never
//! invokes the reference-check tool (network stays out of CI). The
//! attestation content assertions (coverage both ways, per-record hash
//! recompute, zero unwaived mismatches, values-free schema) land with the
//! tool in ticket T6 and extend this file.

use std::process::Command;

const CACHE_DIR: &str = ".reference-cache";

#[test]
fn ground_truth_cache_is_gitignored_and_untracked() {
    let root = checks::workspace_root();
    let gitignore = std::fs::read_to_string(root.join(".gitignore")).expect(".gitignore");
    assert!(
        gitignore
            .lines()
            .any(|l| l.trim() == format!("{CACHE_DIR}/")),
        ".gitignore must ignore {CACHE_DIR}/ — ground-truth bytes never land \
         in the repo"
    );

    // Nothing under the cache path is tracked (belt over the suspenders:
    // a force-add would slip past the ignore).
    let out = Command::new("git")
        .args(["ls-files", CACHE_DIR])
        .current_dir(&root)
        .output()
        .expect("git ls-files");
    let tracked = String::from_utf8_lossy(&out.stdout);
    assert!(
        tracked.trim().is_empty(),
        "tracked files under {CACHE_DIR}/: {tracked}\nground-truth content \
         must never be committed"
    );
}

#[test]
fn ci_never_invokes_the_reference_check_tool() {
    let root = checks::workspace_root();
    let workflows = root.join(".github/workflows");
    for entry in std::fs::read_dir(&workflows)
        .expect("workflows dir")
        .flatten()
    {
        let path = entry.path();
        if path.extension().is_none_or(|e| e != "yml" && e != "yaml") {
            continue;
        }
        let text = std::fs::read_to_string(&path).expect("workflow file");
        assert!(
            !text.contains("reference-check"),
            "{} invokes reference-check: the tool needs the network and runs \
             only as a deliberate local invocation; CI verifies the committed \
             attestation offline",
            path.display()
        );
    }
}
