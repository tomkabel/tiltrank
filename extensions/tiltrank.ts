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
const MAX_LABEL_LEN = 120;
// Mirrors rubric.py sanitise_label. Scoring stays in the script; this only
// stops a label or an Other answer from carrying newlines or bidi into the
// next prompt before that re-score.
const CONTROL_RE =
	/[\u0000-\u001f\u007f-\u009f\u00a0\u00ad\u200b-\u200f\u2028\u2029\u202a-\u202e\u2066-\u2069\ufeff]/g;

function sanitiseLabel(raw: string): string {
	let text = raw.normalize("NFC").replace(CONTROL_RE, " ").replace(/\s+/g, " ").trim();
	if (text.length > MAX_LABEL_LEN) {
		text = text.slice(0, MAX_LABEL_LEN - 1).trimEnd() + "…";
	}
	return text;
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

function renderOptions(options: OptionItem[]): string[] {
	// First option = recommended (position is the marker; we make it visible).
	return options.map((o, i) => {
		const label = sanitiseLabel(o.label);
		return i === 0 ? `(Recommended) ${label}` : label;
	});
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
		async execute(toolCallId, params, _signal, _onUpdate, ctx) {
			const timeoutMs = params.timeoutMs ?? DEFAULT_TIMEOUT_MS;
			const q: QuestionItem = params.questions[0];
			if (!q) {
				return {
					content: [{ type: "text", text: "error: questions[0] required" }],
					details: { error: true },
				};
			}
			if (q.options.length === 0) {
				return {
					content: [{ type: "text", text: "error: at least one option required" }],
					details: { error: true },
				};
			}

			const labels = renderOptions(q.options);
			const withOther = [...labels, "Other (type your own)"];

			const controller = new AbortController();
			const timer = setTimeout(() => controller.abort(), timeoutMs);
			let choice: string | undefined;
			try {
				if (q.multiSelect) {
					// ctx.ui.select is single-choice; multiSelect falls back to
					// a free-text ask naming the options — the honest simple UI.
					choice = await ctx.ui.input(
						q.question +
							" — pick any of: " +
							labels.join("; ") +
							" (comma-separated)",
						"your picks",
						{ signal: controller.signal },
					);
				} else {
					choice = await ctx.ui.select(q.question, withOther, {
						signal: controller.signal,
					});
				}
			} catch {
				choice = undefined;
			} finally {
				clearTimeout(timer);
			}

			if (controller.signal.aborted) {
				return {
					content: [
						{
							type: "text",
							text: JSON.stringify({ timedOut: true, pick: null }),
						},
					],
					details: { timedOut: true },
				};
			}

			if (choice === undefined || choice === null || choice === "") {
				// user cancelled (Esc) — same honest shape as timeout
				return {
					content: [
						{
							type: "text",
							text: JSON.stringify({ timedOut: false, cancelled: true, pick: null }),
						},
					],
					details: { cancelled: true },
				};
			}

			if (choice === "Other (type your own)") {
				const own = await ctx.ui.input("Your own choice:", "free text");
				const ownLabel = sanitiseLabel(own ?? "");
				if (ownLabel === "") {
					return {
						content: [
							{
								type: "text",
								text: JSON.stringify({ timedOut: false, cancelled: true, pick: null }),
							},
						],
						details: { cancelled: true },
					};
				}
				return {
					content: [
						{
							type: "text",
							text: JSON.stringify({
								timedOut: false,
								pick: ownLabel,
								source: "other",
							}),
						},
					],
					details: { pick: ownLabel, source: "other" },
				};
			}

			// Strip the "(Recommended) " prefix we added for rendering.
			const rawPick = choice.startsWith("(Recommended) ")
				? choice.slice("(Recommended) ".length)
				: choice;
			const picked = sanitiseLabel(rawPick);

			return {
				content: [
					{
						type: "text",
						text: JSON.stringify({ timedOut: false, pick: picked }),
					},
				],
				details: { pick: picked },
			};
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
