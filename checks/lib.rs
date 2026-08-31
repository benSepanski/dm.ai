//! Shared helpers for the checks suite (workspace discovery; later: spawning
//! the real server binary for the crash harness and API checks).
#![forbid(unsafe_code)]

use std::path::PathBuf;

/// Absolute path to the workspace root, resolved from this crate's manifest.
pub fn workspace_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .expect("checks crate sits directly under the workspace root")
        .to_path_buf()
}

/// Load and parse the repo's rules-data files through the ruleset crate —
/// exactly what the server and wasm builds embed.
pub fn load_rules_data() -> ruleset_pf2e::RulesData {
    let root = workspace_root().join("rules-data");
    let read = |name: &str| std::fs::read_to_string(root.join(name)).expect("rules-data file");
    let manifest = read("manifest.json");
    let ancestries = read("ancestries.json");
    let heritages = read("heritages.json");
    let ancestry_feats = read("ancestry-feats.json");
    let backgrounds = read("backgrounds.json");
    let classes = read("classes.json");
    let class_feats = read("class-feats.json");
    let general_feats = read("general-feats.json");
    let skills = read("skills.json");
    let equipment = read("equipment.json");
    let spells = read("spells.json");
    ruleset_pf2e::RulesData::parse(&ruleset_pf2e::RulesDataFiles {
        manifest: &manifest,
        ancestries: &ancestries,
        heritages: &heritages,
        ancestry_feats: &ancestry_feats,
        backgrounds: &backgrounds,
        classes: &classes,
        class_feats: &class_feats,
        general_feats: &general_feats,
        skills: &skills,
        equipment: &equipment,
        spells: &spells,
    })
    .expect("rules data parses and passes integrity checks")
}

// ---- Real-server harness for the persistence/crash/API checks ----

use std::io::BufRead;
use std::process::{Child, Command, Stdio};

/// Path to the freshly built server binary (builds it if stale).
pub fn server_binary() -> PathBuf {
    static BUILT: std::sync::OnceLock<PathBuf> = std::sync::OnceLock::new();
    BUILT
        .get_or_init(|| {
            let root = workspace_root();
            let status = Command::new(env!("CARGO"))
                .args(["build", "-p", "server", "--quiet"])
                .current_dir(&root)
                .status()
                .expect("cargo build -p server");
            assert!(status.success(), "server build failed");
            root.join("target/debug/server")
        })
        .clone()
}

/// A live server over a data directory. Killed (SIGKILL) on drop.
pub struct TestServer {
    child: Child,
    pub url: String,
    data_dir: std::path::PathBuf,
}

impl TestServer {
    /// Spawn on an OS-assigned port and wait for the printed URL.
    pub fn spawn(data_dir: &std::path::Path) -> TestServer {
        Self::spawn_with_args(data_dir, &[])
    }

    /// Spawn with extra CLI arguments (e.g. the version-guard tests pass the
    /// hidden test-support flag `--extra-known-versions <file>`).
    pub fn spawn_with_args(data_dir: &std::path::Path, extra_args: &[&str]) -> TestServer {
        // Tests run with the package dir as cwd, so the server's relative
        // name-pools default would miss; point it at the workspace file
        // unless the caller overrides (the pool-failure fixtures do).
        let mut command = Command::new(server_binary());
        if !extra_args.contains(&"--name-pools") {
            command
                .arg("--name-pools")
                .arg(workspace_root().join("app-data/name-pools.json"));
        }
        let mut child = command
            .args(["--data-dir"])
            .arg(data_dir)
            .args(["--port", "0"])
            .args(extra_args)
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit())
            .spawn()
            .expect("spawn server");
        let stdout = child.stdout.take().expect("piped stdout");
        let mut reader = std::io::BufReader::new(stdout);
        let mut line = String::new();
        reader.read_line(&mut line).expect("server prints its URL");
        let url = line
            .trim()
            .strip_prefix("Serving at ")
            .unwrap_or_else(|| panic!("unexpected server output: {line:?}"))
            .to_string();
        // Keep draining stdout so the child never blocks on a full pipe.
        std::thread::spawn(move || {
            let mut sink = String::new();
            while let Ok(n) = reader.read_line(&mut sink) {
                if n == 0 {
                    break;
                }
                sink.clear();
            }
        });
        TestServer {
            child,
            url,
            data_dir: data_dir.to_path_buf(),
        }
    }

    /// Try to spawn where startup is expected to fail; returns stderr.
    pub fn spawn_expect_failure(data_dir: &std::path::Path) -> (i32, String) {
        let output = Command::new(server_binary())
            .args(["--data-dir"])
            .arg(data_dir)
            .args(["--port", "0"])
            .output()
            .expect("run server");
        (
            output.status.code().unwrap_or(-1),
            String::from_utf8_lossy(&output.stderr).to_string(),
        )
    }

    /// Run the `verify` subcommand over a data directory; returns the exit
    /// code and combined stdout.
    pub fn run_verify(data_dir: &std::path::Path, extra_args: &[&str]) -> (i32, String) {
        let output = Command::new(server_binary())
            .args(["--data-dir"])
            .arg(data_dir)
            .args(extra_args)
            .arg("verify")
            .output()
            .expect("run server verify");
        (
            output.status.code().unwrap_or(-1),
            String::from_utf8_lossy(&output.stdout).to_string(),
        )
    }

    pub fn pid(&self) -> u32 {
        self.child.id()
    }

    /// SIGKILL — the crash-harness path; also used by Drop. The lockfile is
    /// renamed aside afterward (renames, never unlinks — the workspace
    /// no-unlink lint applies here too): this harness owns the dir's only
    /// server, so once the child is dead the lock is stale by construction,
    /// and leaving it in place would make a restart on the same dir depend
    /// on the guard's pid-liveness probe not colliding with a reused pid
    /// (a real CI flake). Production stale-lock recovery stays covered by
    /// the dedicated persistence test.
    pub fn kill(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
        let lock = self.data_dir.join("server.lock");
        let _ = std::fs::rename(&lock, self.data_dir.join("server.lock.stale"));
    }
}

impl Drop for TestServer {
    fn drop(&mut self) {
        self.kill();
    }
}
