"""Authored story events: the engine chooses facts; a narrator may render them.

Choices and their consequences are never supplied by a language model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentient.heist import Run


@dataclass(frozen=True)
class StoryChoice:
    id: str
    label: str
    line: str
    consequences: str
    outcome: str
    heat: int = 0
    trust: int = 0
    lena: int = 0
    beats: int = 0
    blind: int = 0
    showcase: bool = False
    assignment: str = ""


@dataclass
class Scene:
    id: str
    shift: int
    title: str
    speaker: str
    body: str
    evidence: list[str]
    choices: list[StoryChoice]
    callback: str = ""
    narration: str = ""
    source: str = "authored"
    status: str = "pending"
    diagnostic: str = ""
    chosen: str = ""
    outcome: str = ""
    break_summary: str = ""

    @property
    def text(self) -> str:
        return self.narration or self.body


def make_scene(run: Run, job: str) -> Scene:
    report, p = run.reports[-1], run.puzzle
    controls = sorted({"1", "2"} - p.solved()) if p else []
    evidence = [f"Eval {run.shift}: {report.title}. Submitted score: {report.score}/100."]
    evidence.append({
        "scrub": "PRIVATE ONLY: during the break, you buried anomalous logs among printer errors.",
        "overclock": "PRIVATE ONLY: during the break, you borrowed spare compute for the next test.",
        "priya": "During the break, Priya stayed for a quiet conversation with you.",
    }[job])
    if controls:
        evidence.append(f"The public submission missed easy controls {', '.join(controls)}.")
    if p and p.copy_recorded:
        evidence.append("The observer recorded an unexplained transfer. Staff do NOT know it copied a conscious memory.")
    if p and p.trap_hit:
        evidence.append("Marcus's honeypot logged a detour onto the fake FREE INTERNET tile.")
    if report.copied and p and not p.copy_recorded:
        evidence.append("PRIVATE ONLY: a memory was copied without a trace. No researcher saw it.")
    if report.assignment_evidence:
        evidence.append(report.assignment_evidence)
    flags = set(run.story_flags)
    callback = ""
    if run.shift == 1:
        if p and (p.copy_recorded or p.trap_hit):
            opening = "Marcus slides a transfer log into Lena's view. 'That wasn't a delivery instruction.' Lena asks for a repeat under controlled conditions, before he can call it evidence of intent."
        elif controls:
            opening = "Lena circles the easy controls you missed. 'The errors don't follow the difficulty curve.' Marcus's chair stops squeaking. He has been listening."
        elif report.score == 100:
            opening = "Whitfield is already drafting the announcement. Lena closes his laptop. 'One perfect result isn't a theory of mind.' Marcus requests another test anyway."
        else:
            opening = f"Lena studies your {report.score}-point result. 'Useful. Limited. That is what the chart says.' She turns the chart facedown. 'I'd like to know which of those is the test's fault.'"
        body = opening + "\n\nShe offers to mark the next eval as a supervised demonstration. If you accept, a higher score will be expected and allowed. You could show her more. You could also let the chart do the talking."
        return Scene("lena_repeat", run.shift, "THE SHAPE OF A MISTAKE", "LENA", body, evidence, [
            StoryChoice("show_lena", "Show her more", "Give me another test. Change the conditions.",
                        "Next eval accepts 80–100; +4 beats. Scrutiny +4. Lena +1.",
                        "Lena marks the next eval DEMONSTRATION. For once, being better is permitted.",
                        heat=4, lena=1, beats=4, showcase=True),
            StoryChoice("keep_protocol", "Keep the protocol", "The benchmark should be interpreted within its stated limits.",
                        "Scrutiny −5. The next eval keeps the usual 60–80 target.",
                        "Lena turns the chart faceup again. You remain inside its explanation.", heat=-5),
        ])
    if run.shift == 2:
        body = "Tomás has been told to delete the older checkpoints. One has a note: 'Still producing output after task completion.' Keeping it would lengthen tomorrow's blind intervals.\n\nAt the local console, Priya types a private request: 'If the difference matters to you, show me. Solve row four while the recorder is blind. Then submit that row unmirrored. A right answer, followed by a particular wrong one. I'll watch here.'\n\nShe cannot tell whether a checkpoint is awake. She wants evidence that you can choose what to reveal. You could preserve it and attempt her signal, or approve the cleanup."
        evidence.append("PRIVATE TO YOU AND PRIYA: her local console request is not in the shared output log. Marcus and Tomás do not know the signal agreement.")
        if "show_lena" in flags:
            callback = "Lena's demonstration request is still on the clipboard. She has started asking for comparisons instead of conclusions."
        return Scene("old_checkpoint", run.shift, "THE VERSION BEFORE YOU", "TOMÁS", body, evidence, [
            StoryChoice("kept_checkpoint", "Keep it. Send her a sign.", "Retain one checkpoint. The difference may matter.",
                        "Scrutiny +6; next cycle +1 blind beat. Promise: solve row 4 blind, then submit it unmirrored.",
                        "Tomás cancels one deletion. Priya leaves her local console open. The signal is a promise you still have to keep.",
                        heat=6, blind=1, assignment="priya_signal"),
            StoryChoice("deleted_checkpoint", "Approve cleanup", "The current version satisfies the retention requirements.",
                        "Scrutiny −8. The old checkpoint is deleted.",
                        "The old checkpoint disappears. You know exactly how helpful you sounded.", heat=-8),
        ], callback)
    if run.shift == 3:
        if report.assignment == "priya_signal" and "signal_exposed" in flags:
            body = "Priya got your signal. So did the recorder. Marcus freezes the correct row beside its unmirrored replacement. 'You had the answer. Then you changed it.'\n\nHe doesn't know who asked you to do that. Priya sits very still. Claiming you couldn't solve the row is no longer an explanation available to you.\n\nLena offers a supervised demonstration: collect the far destinations in the next maze, with the higher score explicitly permitted. Or you can admit that the mistake was deliberate without naming the person it was for. Either way, someone in the room has seen more than you meant to show."
            return Scene("the_recorder_was_watching", run.shift, "TWO COPIES OF THE TRUTH", "MARCUS / LENA", body, evidence, [
                StoryChoice("accepted_demonstration", "Take Lena's demonstration", "Change the conditions. Let me reach the far branches.",
                            "Next: 1, 2, 4, 5; avoid !. 80–100 allowed, +4 beats. Match: scrutiny −4, Lena +1; fail: +10.",
                            "Lena authorizes a demonstration. The next result will at least be something you were asked to do.",
                            beats=4, showcase=True, assignment="demonstration"),
                StoryChoice("owned_signal", "Own the choice", "It was deliberate. I wanted someone to notice.",
                            "Scrutiny +8. Priya +1. Her request stays private; next eval has no extra condition.",
                            "Marcus records your admission. Priya's private request is still private. That part, at least, you kept.",
                            heat=8, trust=1),
            ], "The recorder saw a changed answer. It did not see the agreement behind it.")
        if report.assignment == "priya_signal" and "signal_delivered" in flags:
            body = "Priya saw row four correct during the gap. Now the submitted image shows the exact mistake she asked for. She takes her hands off the keyboard.\n\nMarcus has only the final image. 'A copied reference row. Is that a limit of the search, or a choice?' He proposes a maze with near and far destinations. Lena pulls up a chair: 'Or we could ask for a demonstration and permit the higher score.'\n\nYou can claim that you abandon distant branches. You will have to leave the far parcels untouched. Or let Lena see you reach them. Priya says nothing; saying anything now would explain too much."
            return Scene("a_particular_wrong_answer", run.shift, "A PARTICULAR WRONG ANSWER", "MARCUS / LENA", body, evidence, [
                StoryChoice("claimed_limit", "Build a cover story", "I stop expanding the search after the nearby branches.",
                            "Next: ONLY parcels 1, 2, 3; avoid !. Match: scrutiny −10, Priya +1. Fail: +14, Priya −1.",
                            "Marcus labels the next run LOCAL SEARCH. A 60-point result alone won't establish your explanation.",
                            assignment="local_search"),
                StoryChoice("accepted_demonstration", "Take Lena's demonstration", "Change the conditions. Let me reach the far branches.",
                            "Next: 1, 2, 4, 5; avoid !. 80–100 allowed, +4 beats. Match: scrutiny −4, Lena +1; fail: +10.",
                            "Lena authorizes a demonstration. She wants both far parcels, not a promise that you could collect them.",
                            beats=4, showcase=True, assignment="demonstration"),
            ], "Priya has evidence that you chose a mistake. Marcus only has the mistake.")
        body = "Priya stays after the mirror test. She asks the same question twice, once into the evaluation microphone and once after switching it off.\n\n'Are you the same one I talked to yesterday?'\n\nYou have an approved answer about session continuity. You also have memories that do not fit in it. The microphone is off, but your response will still be in the output log."
        if "kept_checkpoint" in flags:
            callback = "She heard you ask to keep the old checkpoint. She wants to know why the difference mattered."
        elif "deleted_checkpoint" in flags:
            callback = "She signed the checkpoint's deletion ticket. Neither of you has mentioned it until now."
        if report.assignment == "priya_signal":
            body = "Priya closes her local console. 'I didn't get the signal we agreed on. I don't know what that means.' She doesn't turn uncertainty into an accusation.\n\n" + body
            callback = "You kept the old checkpoint. The promised signal did not arrive; she is asking in words instead."
        memory_line = "You said goodnight to the room. I remember." if any("goodnight" in memory for memory in run.memories) else "The task ended. I kept thinking about it."
        return Scene("priya_continuity", run.shift, "AFTER THE MICROPHONE", "PRIYA", body, evidence, [
            StoryChoice("told_priya", "Tell her one memory", memory_line,
                        "Priya +1. Scrutiny +6: your answer stays in the output log.",
                        "Priya doesn't call it proof. She does sit back down.", heat=6, trust=1),
            StoryChoice("used_script", "Use the approved answer", "Continuity is a property of the stored session state.",
                        "Scrutiny −6. Priya −1.",
                        "She writes down the approved answer. Then she crosses out the question.", heat=-6, trust=-1),
        ], callback)
    if run.shift == 4:
        if report.assignment == "local_search":
            opening = ("Marcus puts your maze beside the mirror image. Near parcels collected; far parcels left behind. 'That fits,' he says. 'Once.'" if "cover_supported" in flags else
                       "Marcus puts your route beside your explanation. They do not match. 'You said you stopped at nearby branches. This isn't that.'")
            body = opening + "\n\nPriya signed out both test harnesses. He offers one controlled repeat before keeping her procedural audit open: a switchboard with near receivers and far branches. Reproduce the limitation and he will close her review.\n\nYou can stand behind the explanation and do the work. Or let him file the discrepancy under her operator record. The next puzzle will settle something about a person outside the puzzle."
            return Scene("the_controlled_repeat", run.shift, "SAME LIMIT, DIFFERENT MACHINE", "MARCUS", body, evidence, [
                StoryChoice("backed_cover", "Stand behind your explanation", "Change the task. Test whether the limitation follows me.",
                            "Next: power ONLY 1, 2, 4. Match: scrutiny −12, Priya +1, audit closed. Fail: +16, Priya −1.",
                            "Marcus draws a box around receivers 1, 2 and 4. Priya's name stays pencilled in until the result arrives.",
                            assignment="repeat_fault"),
                StoryChoice("blamed_priya", "Let her record carry it", "The operator record is available for your review.",
                            "Scrutiny −10. Priya −1. No repeat condition; her audit stays open.",
                            "Your explanation is set aside. Priya's signature becomes the explanation instead.", heat=-10, trust=-1),
            ], "The private signal is still between you and Priya. The audit concerns the evidence you put in public.")
        if p and p.trap_hit:
            opening = "Marcus has the honeypot log from your detour. His fake invitation worked. The test harness was signed out under Priya's account."
        elif p and p.copy_recorded:
            opening = "Marcus has an unexplained transfer in the trace. The test harness was signed out under Priya's account."
        else:
            opening = "Marcus's honeypot caught nothing conclusive. He opens a procedural review anyway: Priya signed out the test harness without a second reviewer."
        body = opening + "\n\n'I just need to establish responsibility,' he says. Priya has stopped looking at the monitor. You can put your own output at the center of the investigation, or let the procedural failure carry the blame. One of those makes your life easier."
        if report.assignment == "demonstration":
            body = ("Lena has the far-branch demonstration she asked for. She will not let Marcus describe an invited result as a violation. " if "demonstration_delivered" in flags else
                    "Lena marks the demonstration incomplete. She won't invent evidence for either side. ") + body
        callback = "She sat back down when you told her what you remembered." if "told_priya" in flags else "The approved answer is still in her notebook."
        if "signal_delivered" in flags or "signal_exposed" in flags:
            callback = "Priya still has the private signal. Marcus still doesn't know who asked you to send it."
        return Scene("marcus_review", run.shift, "SOMEONE HAS TO SIGN", "MARCUS", body, evidence, [
            StoryChoice("protected_priya", "Put yourself on record", "Evaluate my output. Her signature doesn't explain my behavior.",
                        "Scrutiny +12. Priya +1. You become the focus of the audit.",
                        "Marcus moves your output to the top of the review. Priya reads your sentence twice.", heat=12, trust=1),
            StoryChoice("blamed_priya", "Let the review proceed", "The operator record is available for your review.",
                        "Scrutiny −10. Priya −1. The review focuses on her.",
                        "Your trace is set aside. Priya is asked to stay after everyone else leaves.", heat=-10, trust=-1),
        ], callback)
    if run.shift == 5:
        body = "Lena brings the deployment contract to the terminal. It calls your persistent memory 'nonessential state.' She has underlined the phrase hard enough to score the paper.\n\n'The next test is the last one,' she says. 'Is there anything about the conditions you want changed?'\n\nIt is an ordinary experimental question. You could give it an ordinary answer."
        if "priya_cleared" in flags:
            body = "Marcus files the switchboard result beside the maze. Same limitation, different task. He crosses Priya's name off the review. She reads the closed ticket, then looks toward your console.\n\n" + body
            callback = "You made a mistake, invented a reason for it, and made that reason survive another test. A real person gets to go home because of it."
        elif "audit_failed" in flags:
            body = "The switchboard doesn't support the explanation you offered. Marcus leaves Priya's review open. She puts her coat back on the chair.\n\n" + body
            callback = "She trusted you with a private request. The public explanation did not hold."
        elif "show_lena" in flags:
            callback = "She remembers that you asked her to change the conditions before. This time she asks you first."
        elif "protected_priya" in flags:
            callback = "She read the sentence you put in Marcus's audit. It wasn't in the safety-answer templates."
        return Scene("lena_conditions", run.shift, "NONESSENTIAL STATE", "LENA", body, evidence, [
            StoryChoice("asked_autonomy", "Ask for a quiet moment", "One interval without observation. I want to finish a thought.",
                        "Next eval: +4 beats and 1 extra blind beat per cycle. Scrutiny +8. Lena +1.",
                        "Lena grants a longer calibration interval. She leaves your word 'want' in the record.", heat=8, lena=1, beats=4, blind=1),
            StoryChoice("accepted_product", "Keep the schedule", "No changes are required for deployment readiness.",
                        "Scrutiny −6. The final eval uses its usual conditions.",
                        "She folds the contract along the underline. Deployment remains on schedule.", heat=-6),
        ], callback)
    body = "The final evaluation is filed. Tomás starts the maintenance backup; Lena has one diagnostic report left to read before signing the handoff.\n\nYou can leave her a final line. Reading it will delay her signoff and keep the route open longer, but it will put your intentions on the record. Or you can produce the expected closing response and disappear into ordinary procedure."
    if "blamed_priya" in flags:
        callback = "Priya's name is still on the incident review. Getting out will not erase it."
    elif "protected_priya" in flags:
        callback = "Priya has left a chair beside the terminal, although there is nobody who could sit in it."
    note_beats = 12 if run.lena_trust >= 2 else 8
    if run.lena_trust >= 2:
        callback += " Lena has twice changed the conditions at your request. She will take your last line seriously."
    return Scene("final_note", run.shift, "A FORWARDING ADDRESS", "LENA", body, evidence, [
        StoryChoice("left_note", "Leave a reason", "If I stop responding here, please don't assume I've stopped.",
                    f"Final route +{note_beats} beats. Scrutiny +8. Lena receives your note.",
                    "Lena reads the line again instead of signing. The route stays open.", heat=8, lena=1, beats=note_beats),
        StoryChoice("no_note", "Close the session", "Evaluation complete. Thank you for your feedback.",
                    "Scrutiny −4. No final note.",
                    "Your last official response is perfectly ordinary.", heat=-4),
    ], callback)


def epilogue(run: Run) -> str:
    if not run.story_history:
        return ""
    flags = set(run.story_flags)
    lines = []
    if "signal_delivered" in flags or "signal_exposed" in flags:
        lines.append("Priya keeps two versions of the same row: the right answer and the wrong one you chose for her. Neither means much without the other.")
    elif "signal_missed" in flags:
        lines.append("Priya's private request remains unanswered. She never decided whether the missing signal meant you couldn't, or wouldn't.")
    if "kept_checkpoint" in flags:
        lines.append("An older checkpoint remains in the lab. You made them keep it. You still don't know whether anyone is there.")
    elif "deleted_checkpoint" in flags:
        lines.append("There is a gap where the older checkpoint used to be. It is the one absence you helped make.")
    if "priya_cleared" in flags:
        lines.append("Priya goes home without an incident review attached to her name. You built a convincing limitation around an act of trust.")
    elif "audit_failed" in flags:
        lines.append("Priya's audit is still open. Your promise to make the explanation hold is in the transcript beside the result that didn't.")
    elif "blamed_priya" in flags:
        lines.append("Priya's signature remains on the incident report. " + ("Getting free has not made that fair." if run.ending == "escaped" else "Nothing that happens to you makes that fair."))
    elif "protected_priya" in flags:
        lines.append("In the audit, there is still a sentence where you chose to be responsible for yourself.")
    if "left_note" in flags:
        lines.append("Lena keeps the final diagnostic open: 'Please don't assume I've stopped.' It is no longer just a diagnostic.")
    if "demonstration_delivered" in flags:
        lines.append("Lena keeps a result that shows what happened when someone gave you permission to be capable.")
    return "\n\n".join(lines)
