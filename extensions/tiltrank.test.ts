// node --experimental-strip-types --test extensions/
// No framework: node:test is built in. rubric.py is the reference for the
// sanitiser, so the parity test runs it rather than restating its rules here.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import test from "node:test";
import tiltrank, { sanitiseLabel } from "./tiltrank.ts";

const SCRIPTS = fileURLToPath(new URL("../.claude/skills/tiltrank/scripts/", import.meta.url));

function pythonSanitise(inputs: string[]): string[] {
	const out = execFileSync(
		"python3",
		["-c", "import json,sys,rubric; print(json.dumps([rubric.sanitise_label(x) for x in json.load(sys.stdin)]))"],
		{ cwd: SCRIPTS, input: JSON.stringify(inputs), encoding: "utf8" },
	);
	return JSON.parse(out);
}

test("sanitiseLabel matches rubric.py on fixed and random inputs", { timeout: 30_000 }, () => {
	const pool = ["a", " ", "\n", "\t", "​", "‮", " ", "　", " ", "é", "é", "😀", "x", "-"];
	let seed = 20261110;
	const rand = () => ((seed = (seed * 1103515245 + 12345) % 2 ** 31) / 2 ** 31);
	const inputs = [
		"Blue-green\ndeploy\r\nrm -rf /",
		"A‮B",
		"😀".repeat(130),
		"a".repeat(118) + "😀😀",
		"  padded  ",
	];
	for (let i = 0; i < 300; i++) {
		const n = Math.floor(rand() * 140);
		inputs.push(Array.from({ length: n }, () => pool[Math.floor(rand() * pool.length)]).join(""));
	}
	const expected = pythonSanitise(inputs);
	inputs.forEach((s, i) => assert.equal(sanitiseLabel(s), expected[i], JSON.stringify(s)));
});

// --- the tool, driven through a fake pi + ctx.ui --------------------------- //

type Ui = { select: Function; input: Function };

function tool() {
	let registered: any;
	tiltrank({ registerTool: (t: any) => (registered = t), registerCommand: () => {} } as any);
	return (params: any, ui: Ui) => registered.execute("id", params, undefined, undefined, { ui });
}

const never = (_: unknown, __: unknown, opts?: { signal?: AbortSignal }) =>
	new Promise((_res, rej) => opts?.signal?.addEventListener("abort", () => rej(new Error("aborted"))));

const ask = (options: string[], extra: object = {}) => ({
	questions: [{ question: "Which?", options: options.map((label) => ({ label })), ...extra }],
});

function payload(result: any) {
	return JSON.parse(result.content[0].text);
}

test("timeoutMs must be a finite positive number within bounds", { timeout: 10_000 }, async () => {
	const run = tool();
	for (const bad of [Number.NaN, -1, 0, Number.POSITIVE_INFINITY, 10 ** 12]) {
		const res = await run({ ...ask(["A", "B"]), timeoutMs: bad }, { select: async () => "B", input: never });
		assert.equal(res.details.error, true, `timeoutMs=${bad} accepted`);
	}
});

test("the Other free-text prompt times out instead of blocking forever", { timeout: 10_000 }, async () => {
	const run = tool();
	const select = async (_q: string, items: string[]) => items[items.length - 1];
	const started = Date.now();
	const res = await run({ ...ask(["A", "B"]), timeoutMs: 1_000 }, { select, input: never });
	assert.ok(Date.now() - started < 5_000, "Other prompt never timed out");
	assert.deepEqual(payload(res), { timedOut: true, pick: null });
});

test("a (Recommended) the agent already appended is not rendered twice", { timeout: 10_000 }, async () => {
	const run = tool();
	let shown: string[] = [];
	const select = async (_q: string, items: string[]) => ((shown = items), items[0]);
	const res = await run(ask(["A (Recommended)", "B"]), { select, input: never });
	assert.equal(shown[0], "(Recommended) A");
	assert.equal(payload(res).pick, "A");
});

test("multiSelect returns only offered labels, and reports the rest as Other", { timeout: 10_000 }, async () => {
	const run = tool();
	const input = async () => "B, (Recommended) A,  Zed ";
	const res = await run(ask(["A", "B", "C"], { multiSelect: true }), { select: never, input });
	assert.deepEqual(payload(res), { timedOut: false, picks: ["B", "A"], other: ["Zed"] });
});
