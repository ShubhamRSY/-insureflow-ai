# P-072 — Remove the "; no cooking" add from operations entirely

- Text as approved by the user, 2026-10-23 (D-124), Claude Code session: remove the "; no cooking" add from operations entirely. Files where cooking is not clearly stated keep their existing review flag; no automatic "no cooking" in any case. Revert the P-070/P-071 add logic; keep any harmless refactoring only if it changes no behaviour. The H1 scoring gap moves to the next scorer version.
- Raised because @model-risk's T-118 re-check (`deliverables/model-risk/T-118-recheck.md`) found P-071's word list missed plain cooking words, so the add still made false completes.
