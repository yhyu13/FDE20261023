import { strict as assert } from "node:assert";
import { test } from "node:test";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, join, relative, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

// Standalone install: this test ships inside the `hyperframes` skill only, so it
// scans that skill's own scripts. In the upstream plugin repo, skills/ holds the
// whole bundle and packages/cli/src/media-use sits beside it.
const SKILL_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const CLI_MEDIA_USE = resolve(SKILL_ROOT, "../../packages/cli/src/media-use");

// Agents install skills by symlinking the skills dir, so each script must still run its CLI.
test("skill CLIs run when invoked through a symlinked skills dir", (t) => {
  const script = "media-use/audio/scripts/heygen-voice.mjs";
  if (!existsSync(join(SKILL_ROOT, script))) {
    return t.skip(`${script} not installed in this standalone skills tree`);
  }
  const dir = mkdtempSync(join(tmpdir(), "skills-link-"));
  try {
    try {
      symlinkSync(SKILL_ROOT, join(dir, "skills"), "dir");
    } catch {
      return t.skip("symlinks not permitted on this machine (no developer mode)");
    }
    for (const entry of [script]) {
      const run = spawnSync(process.execPath, [join(dir, "skills", entry), "not-a-command"], {
        encoding: "utf8",
      });
      assert.notEqual(run.status, 0, `${entry} exited ${run.status} without running its CLI`);
      assert.match(run.stderr, /usage/, entry);
    }
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

function skillScripts(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === "node_modules" ? [] : skillScripts(path);
    return /\.(mjs|js)$/.test(entry.name) && !/\.test\.mjs$/.test(entry.name) ? [path] : [];
  });
}

test("skill scripts detect their CLI entry through lib/main-module.mjs only", () => {
  const roots = [SKILL_ROOT];
  if (existsSync(CLI_MEDIA_USE)) roots.push(CLI_MEDIA_USE);
  const handRolled = roots.flatMap(skillScripts).filter(
    (path) =>
      !path.endsWith("main-module.mjs") && readFileSync(path, "utf8").includes("process.argv[1]"),
  );
  assert.deepEqual(
    handRolled.map((path) => relative(SKILL_ROOT, path)),
    [],
  );
});
