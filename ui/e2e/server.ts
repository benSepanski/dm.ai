// Spawns the real server binary (the same one Ben runs) over a fresh data
// directory, with SIGKILL and restart controls for the crash story.
import { type ChildProcess, execFileSync, spawn } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), '../..');

let built = false;
function serverBinary(): string {
  // A prebuilt binary (e.g. CI's release build, or a local one while the
  // workspace is mid-change) skips the build step.
  const prebuilt = process.env['DMAI_SERVER_BIN'];
  if (prebuilt !== undefined && prebuilt !== '') {
    return prebuilt;
  }
  if (!built) {
    execFileSync('cargo', ['build', '-p', 'server', '--quiet'], { cwd: repoRoot });
    built = true;
  }
  return join(repoRoot, 'target/debug/server');
}

export class TestServer {
  private child: ChildProcess | null = null;
  url = '';
  readonly dataDir: string;

  constructor() {
    this.dataDir = mkdtempSync(join(tmpdir(), 'dmai-e2e-'));
  }

  /** The port the server is bound to (0 until started). */
  port = 0;

  /**
   * Extra CLI arguments for the next start (e.g. the hidden test-support
   * flag `--extra-known-versions` the version-guard walk uses to fabricate
   * a prior shipped data version).
   */
  extraArgs: string[] = [];

  async start(port = 0): Promise<void> {
    if (this.child === null) {
      // The harness owns this dir's only server; with no live child, any
      // lockfile is stale by construction (SIGKILL never removes it). The
      // guard's pid-liveness probe can false-positive when a CI runner
      // reuses the dead pid, so clear the stale lock before restarting.
      rmSync(join(this.dataDir, 'server.lock'), { force: true });
    }
    const child = spawn(
      serverBinary(),
      [
        '--data-dir',
        this.dataDir,
        '--port',
        String(port),
        // The harness's cwd is not the repo root, so the name-pools
        // default would miss; point at the repo's file explicitly.
        '--name-pools',
        join(repoRoot, 'app-data/name-pools.json'),
        ...this.extraArgs,
      ],
      {
        stdio: ['ignore', 'pipe', 'inherit'],
      },
    );
    this.child = child;
    this.url = await new Promise<string>((resolve, reject) => {
      let buffer = '';
      child.stdout.on('data', (chunk: Buffer) => {
        buffer += chunk.toString();
        const match = /Serving at (\S+)/.exec(buffer);
        if (match?.[1] !== undefined) {
          resolve(match[1]);
        }
      });
      child.on('exit', (code) => reject(new Error(`server exited early (${code})`)));
      setTimeout(() => reject(new Error('server did not print its URL')), 10_000);
    });
    this.port = Number(new URL(this.url).port);
  }

  /** SIGKILL — the crash story's kill -9. */
  killNine(): void {
    this.child?.kill('SIGKILL');
    this.child = null;
  }

  async stop(): Promise<void> {
    this.killNine();
  }
}
