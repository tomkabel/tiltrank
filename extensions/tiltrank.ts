/**
 * tiltrank extension for pi (badlogic's pi-mono coding agent).
 *
 * Provides the interactive ask surface the tiltrank skill needs:
 *
 * - `tiltrank` tool: same JSON shape as Claude Code's AskUserQuestion
 *   (questions[] with label/description/multiSelect), rendered through
 *   ctx.ui. The recommended option goes FIRST in the list; the extension
 *   prefixes its label with "(Recommended)" per the cross-harness
 *   convention. "Other" is always offered, with a free-text input path —
 *   the un-scored-candidate escape hatch in step 5 of the skill.
 * - `/panel` command: deterministic opt-in to escalation. Sends a user
 *   message that names the request as a panel request, so it arrives in
 *   the conversation as a normal user message the skill can recognize.
 *
 * Timeout policy mirrors the skill's SKILL.md "When the ask times out":
 * the tool auto-cancels after timeoutMs (default 120s) and returns
 * `{"timedOut": true, "pick": null}` so the agent logs
 * `pick: null, timed_out: true` and either blocks (interactive) or
 * proceeds with the recommendation saying no user answer existed
 * (explicitly autonomous runs only).
 *
 * The extension is rendering + returning the pick ONLY. All scoring,
 * gating, ranking, and the audit log live in rubric.py — never duplicate
 * logic here (the extension runs with full system permissions; keeping it
 * dumb is the containment).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

const DEFAULT_TIMEOUT_MS = 120_000;
const MAX_TIMEOUT_MS = 3_600_000; // setTimeout overflows past 2**31-1 and fires at once
const MAX_LABEL_LEN = 120;
const RECOMMENDED = "(Recommended)";
const OTHER = "Other (type your own)";
// Mirrors rubric.py sanitise_label. Scoring stays in the script; this only
// stops a label or an Other answer from carrying newlines or bidi into the
// next prompt before that re-score.
const CONTROL_RE =
	/[\u0000-\u001f\u007f-\u009f\u00a0\u00ad\u200b-\u200f\u2028\u2029\u202a-\u202e\u2066-\u2069\ufeff]/g;

export function sanitiseLabel(raw: string): string {
	const text = raw.normalize("NFC").replace(CONTROL_RE, " ").replace(/\s+/g, " ").trim();
	// Code points, as Python counts them: .length and .slice split surrogate pairs.
	const chars = Array.from(text);
	if (chars.length <= MAX_LABEL_LEN) return text;
	return chars.slice(0, MAX_LABEL_LEN - 1).join("").trimEnd() + "…";
}

/** The label as scored: sanitised, and without a marker the agent already added. */
function bareLabel(raw: string): string {
	let label = sanitiseLabel(raw);
	if (label.startsWith(RECOMMENDED)) label = label.slice(RECOMMENDED.length);
	if (label.endsWith(RECOMMENDED)) label = label.slice(0, -RECOMMENDED.length);
	return label.trim();
}

function reply(body: object, details: object = body) {
	return { content: [{ type: "text" as const, text: JSON.stringify(body) }], details };
}

function error(message: string) {
	return reply({ error: message }, { error: true });
}

interface OptionItem {
	label: string;
	description?: string;
}

interface QuestionItem {
	question: string;
	options: OptionItem[];
	multiSelect?: boolean;
}

function renderOptions(labels: string[]): string[] {
	// First option = recommended (position is the marker; we make it visible).
	return labels.map((label, i) => (i === 0 ? `${RECOMMENDED} ${label}` : label));
}

export default function (pi: ExtensionAPI) {
	pi.registerTool({
		name: "tiltrank",
		label: "Tiltrank Ask",
		description:
			"Ask the user to choose between options. Use when a scored rubric " +
			"produced a ranked shortlist and the user must make the final pick. " +
			"First option is the recommended one. An Other/free-text path is " +
			"always available. One question, at most 4 options.",
		parameters: Type.Object({
			questions: Type.Array(
				Type.Object({
					question: Type.String({
						description: "Question text; may include runner-up steelman, exclusions, disclosures",
					}),
					options: Type.Array(
						Type.Object({
							label: Type.String({ description: "Short option label, no numbers" }),
							description: Type.Optional(
								Type.String({
									description: "Band + one real tradeoff clause. No numbers.",
								}),
							),
						}),
						{ maxItems: 4 },
					),
					multiSelect: Type.Optional(Type.Boolean()),
				}),
				{ maxItems: 1 },
			),
			timeoutMs: Type.Optional(
				Type.Number({ description: "Ask timeout in ms; default 120000. On timeout returns timedOut." }),
			),
		}),
		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			const timeoutMs = params.timeoutMs ?? DEFAULT_TIMEOUT_MS;
			if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > MAX_TIMEOUT_MS) {
				return error(`timeoutMs must be a number in (0, ${MAX_TIMEOUT_MS}], got ${timeoutMs}`);
			}
			const q: QuestionItem | undefined = params.questions[0];
			if (!q) return error("questions[0] required");
			if (q.options.length === 0) return error("at least one option required");

			const offered = q.options.map((o) => bareLabel(o.label));
			if (offered.some((l) => l === "") || new Set(offered).size !== offered.length) {
				return error("option labels must be non-empty and distinct");
			}
			const labels = renderOptions(offered);

			// One deadline for the whole ask, including the Other free-text step:
			// a second prompt without it could block the agent forever.
			const deadline = AbortSignal.any([AbortSignal.timeout(timeoutMs), ...(signal ? [signal] : [])]);
			const prompt = async (fn: () => Promise<string | undefined>) => {
				try {
					return await fn();
				} catch {
					return undefined;
				}
			};
			const expired = () => (deadline.aborted ? reply({ timedOut: true, pick: null }) : undefined);
			const cancelled = () => reply({ timedOut: false, cancelled: true, pick: null });

			if (q.multiSelect) {
				// ctx.ui.select is single-choice; multiSelect falls back to a
				// free-text ask naming the options. Split the answer back into
				// offered labels and Other text, so an unscored name is never
				// returned as if it had been on the menu.
				const raw = await prompt(() =>
					ctx.ui.input(`${q.question} — pick any of: ${labels.join("; ")} (comma-separated)`, "your picks", {
						signal: deadline,
					}),
				);
				const timedOut = expired();
				if (timedOut) return timedOut;
				const parts = (raw ?? "").split(",").map(bareLabel).filter(Boolean);
				if (parts.length === 0) return cancelled();
				const picks = [...new Set(parts.filter((p) => offered.includes(p)))];
				const other = [...new Set(parts.filter((p) => !offered.includes(p)))];
				return reply({ timedOut: false, picks, other });
			}

			const choice = await prompt(() => ctx.ui.select(q.question, [...labels, OTHER], { signal: deadline }));
			const timedOut = expired();
			if (timedOut) return timedOut;
			if (!choice) return cancelled(); // Esc: same honest shape as a timeout

			if (choice === OTHER) {
				const own = await prompt(() => ctx.ui.input("Your own choice:", "free text", { signal: deadline }));
				const late = expired();
				if (late) return late;
				const ownLabel = sanitiseLabel(own ?? "");
				if (ownLabel === "") return cancelled();
				return reply({ timedOut: false, pick: ownLabel, source: "other" });
			}

			return reply({ timedOut: false, pick: bareLabel(choice) });
		},
	});

	pi.registerCommand("panel", {
		description:
			"Force panel escalation for the current decision request (deterministic opt-in)",
		handler: async (args, ctx) => {
			const text = args.trim();
			if (ctx.isIdle()) {
				pi.sendUserMessage(
					text
						? `/panel ${text}`
						: "/panel — please escalate this decision to a panel review",
				);
			} else {
				pi.sendUserMessage(
					text ? `/panel ${text}` : "/panel — please escalate this decision to a panel review",
					{ deliverAs: "followUp" },
				);
			}
		},
	});
}
