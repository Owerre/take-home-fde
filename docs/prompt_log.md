# Authentic prompt record

The consolidated requirements are maintained in [build_brief.md](build_brief.md).

The session began with the user supplying the workspace and attachment path.
Codex read the attachment, inspected the directory and Git state, extracted the
exercise text from its DOCX XML, read the briefing, and ran local aggregate
profiling. Codex then prepared the M1 proposal and stopped for review.
No earlier AI transcript was supplied. The user's prior profiling findings are
claims in the supplied prompt, independently checked by the profiling script.
This is a manually maintained factual summary, not a complete tool transcript.
No hidden reasoning or reconstructed prompts are represented as conversation.


## Implementation record

The original supplied build brief is retained in the first Git commit, `35e1b93`.
The current brief consolidates requirements; it is not presented as an untouched
historical transcript. The four M1 specs were committed in `867d07d` before app
implementation. Application code was first committed in `cad1370`.

Codex translated the approved contracts into a bulk raw loader, set-based SQL
transformations, a deterministic metric compiler, and a typed model-client adapter.
The application is organized by responsibility; configuration and YAML prompts
are explicit artifacts. Tests use hand-computed synthetic ledger values and
independently authored SQL rather than compiler-generated expected answers.

Concrete corrections during the work: the profiler initially missed € and £
prefixes; source ingestion was changed from slow per-cell inserts to a bulk text
load; a test's invoice-ID check accidentally matched a rule-ID substring and was
corrected. Strict typing errors were fixed without disabling strict mode.
The briefing's FX rule was kept despite the source-generation pattern, and raw
negative-paid records were not counted twice as both duplicate losers and rejects.

This is a trimmed factual summary of work, not a complete transcript or a claim
that a live Anthropic evaluation occurred. No earlier transcript was supplied.

