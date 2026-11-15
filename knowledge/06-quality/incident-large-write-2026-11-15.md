---
id: INC-001
type: incident
status: draft
tldr: Qwen3-Coder via Ollama and OpenCode lost a 1,000-line write at about line 627. Root cause unknown. Lists confirmed facts, hypotheses, experiments.
---
# INC-001 Large write failure (2026-11-15)
Setup: Qwen3-Coder, served by Ollama, driven by OpenCode. Model size and
configured context window: [owner to fill in].

## Confirmed observations
- T1 small Markdown file: structured tool call, executed, file verified. OK.
- T2 "1,000 numbered lines to large_output_probe.md": output stopped near
  line 627, mid-line. The file was never created (checked on disk).
- In some tests the model printed tool-call-like text instead of an
  executable tool call.

## Not established
Which component failed. The context window has NOT been proven responsible.

## Hypotheses (all untested)
- H1 Generation cut off by an output-token or context limit (check the
  configured Ollama context length and the OpenCode output limit).
- H2 Incomplete or malformed structured tool call from the model.
- H3 Runtime did not recognise the call and treated it as text.
- H4 Tool executed but the write failed (permissions, path, size).

## Logs to capture for the next attempt
Ollama server log with debug enabled; OpenCode log; the raw model output;
`ls -l` and `wc -l` of the target; the time of each step.

## Experiments (all NOT RUN)
E1 100 lines, one write. E2 500 lines. E3 1,000 lines. E4 1,000 lines in
10 chunks. E5 chunked run with a simulated restart. E6 invalid tool call and
interrupted generation. E7 duplicate writes and retries.
Record per run: completeness, tool-call status, execution result, file
exists, content integrity (artifact_check --numbered N), duration, recovery.
Results go in this file as dated lines, with the real command output.

## Mitigation adopted
ENG-002 and the AGENTS.md write rule. These are precautions that hold
whatever the root cause turns out to be.

## Open
Q: which Qwen3-Coder size and context setting were used? What are the
measured limits from E1-E4?
