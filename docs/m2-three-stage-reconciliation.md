# M2 operating contract — 14 September 2026

This owner-directed contract supersedes conflicting active workflow assumptions in older Signal/Studio/YouTube handoffs. It does not rewrite their historical evidence. The product has three stages: **Research → Scripting, generation and shooting → Post-production**. Instagram Reels is the active research corpus. The frozen YouTube census contributes only dated background knowledge, never the Reel coverage denominator or reference ranking.

## 1. Research: observable records before interpretation

Inputs: an approved creator roster, dated Hiker responses, retained Reel media, immutable transcript attempts, decoded frames, and a versioned audience/taxonomy contract. Hiker supplies metadata and media locators; it does not prove spoken language, acoustic transcription quality or customer relevance. A caption is not a transcript. A frame file is not a scene or a semantic finding.

Store one canonical Reel identity per platform/code, many metric observations per Reel and snapshot, many acquisition/ASR attempts per media hash, and an explicit selected evidence version. Never add local and server transcript totals without an overlap join on code and source version. Preserve conflicting original texts as separate attempts. Deduplicate exact artifacts by hash; do not discard repeated metric snapshots.

Each transcript attempt needs source code and URL, media hash, processor/model/version, original-language detection method and probability, start/end timestamps, original raw text, segment and word timing availability, completion status, quality flags and selected/rejected reason. A normalized display text may coexist, but must never replace the raw transcription. Translation is excluded from this English-only research route.

Run initial language detection before consuming the full ASR iterator. Detected non-English ends the transcription route as EXCLUDED_NON_ENGLISH; unknown or low-confidence speech needs LANGUAGE_REVIEW. English detection is provisional, not proof of perfect recognition. Mixed-language clips require review; classify the observed speech, not the creator's nationality or name. Older forced-English output has unknown original language until audio is rechecked.

Distinguish these measures:

| Measure | Numerator / denominator | Meaning |
|---|---|---|
| Acquisition rate | decoded media / eligible unique Reels | Media availability |
| ASR attempt rate | unique Reels attempted / eligible unique Reels | Processing coverage |
| Nonempty transcript rate | nonempty original outputs / eligible unique Reels | Text existence, including explicitly flagged failures |
| Completed ASR rate | nonempty completed attempts / eligible unique Reels | Machine completion; suspicious timings separate |
| Detected-English rate | language-detected English / language-detected attempts | Observed model classification |
| Verified-English usable rate | accepted full-speech English transcripts / English-eligible unique Reels | Main research coverage; unknown until review |
| Semantic coverage | accepted whole-transcript analysis / verified-English usable Reels | Meaning extracted |
| Frame coverage | verified frame-bearing Reels / eligible unique Reels | Visual availability; count files separately |
| Reference readiness | language + transcript + relevant visual + metric + independent review gates / eligible unique Reels | Usable references |

`last_segment_end / media_duration` is **endpoint reach**, not transcript completeness. One sentence at the end can score 100%; silent endings can make a complete transcript score lower. Validate speech coverage against VAD intervals, missing interior spans, repeated/hallucinated text, timestamp bounds, named tools and an audio-review sample. Do not silently promote a 0.9 endpoint ratio to "fully transcribed".

Analyze the complete original transcript in sequence before summarizing it. Retain text-span evidence for each pain, claim, hook, mechanism, proof, objection and CTA. Word timestamps absent from an existing artifact remain absent; segment timing does not become invented word timing. Every reference selected for writing needs accessible source evidence and a specific reason for reuse (hook structure, demonstrated mechanism, proof or visual treatment), not just a URL.

## 2. Categories, metrics and ranking

Categorical features are observations/annotations, not conclusions: audience role, business function, workflow, named pain, tool, solution mechanism, hook type, proof type, CTA type, production format, language, relevance, and evidence confidence. Allow multiple pains/insights per Reel through child rows with transcript spans. Keep missing values explicit; do not force one generic insight into every video.

For each group report N Reels, N creators, missingness, mean, median, p25/p75, p10/p90 and standard deviation of views and available rates. Compare unique Reel observations at similar exposure ages. Account totals and category totals must reveal overlap when labels are multi-valued. Do not sum overlapping categories as an exclusive partition.

Use views as exposure, not customer conversion. Saves and reshares are separate provider-reported measures with distinct availability. A combined `(shares+saves)/views` is defined only when both counts are observed; missing is not zero. Rate per thousand is rate multiplied by 1,000. `view_multiple=views/baseline`; `relative_lift=view_multiple-1`. Never label relative lift as "x".

Three ranking options to evaluate on the same English/relevance-qualified cohort:

1. **Business relevance first (recommended):** gate evidence and named SME use case, then rank share/save rates within creator and exposure-age cohorts; cap creator concentration. Best for useful scripts.
2. **Reach discovery:** creator-relative view percentile plus a minimum credible exposure and sample size. Keep this discovery score separate from proof/quality. Best for finding hooks.
3. **Balanced experiments:** stratified high/middle/low performers within categories and creators. Best for estimating category differences and avoiding a winners-only sample.

Do not declare a rule "works" from a selected top-only corpus. Show descriptive association and confidence intervals clustered by creator, control multiple comparisons, and validate directional hypotheses on a held-out run. An ordinal editorial score is a transparent preference, not a learned success probability. The English-only cohort must be rebuilt before reusing mixed-language rankings.

## 3. Scripting, generation and shooting

Input: accepted research capsule, exact reference IDs and spans, audience role, named workflow/pain/solution, claim evidence, and rights state. Output: an original script, source-to-claim map, shot list, storyboard, required owner footage and optional fal generation requests.

Owners/C-level need a recognizable business decision; managers need the mechanism and credible implementation proof; workers need a simple next action. A hook can state a concrete pain, result or decision immediately. Generic "AI saves time" fails. Do not turn internal pipeline defects into the default customer-facing content.

"Three workflows" was an earlier request for concrete demonstrable examples, not three required industries or three software modules. The current user-facing structure is the three stages above. Candidate examples should be chosen from the qualified research, then tested using owned or synthetic inputs. No scenario is claimed implemented merely because a card describes it.

fal.ai replaces Open-Generative-AI as the intended generation API route. No Open-Generative-AI checkout is required. Each model has its own input schema: prompt, duration/ratio where supported, approved reference images and optional seed. The application must select an admitted model, bind the exact request to rights and cost approval, store its request ID, and avoid blind resubmission after uncertain network failures. An empty balance/key does not imply execution readiness. Current integration is disabled pending a model-specific capability/quality/cost test.

## 4. Post-production

Input: generated or recorded media, hashes, explicit rights receipts, separate narration/music/SFX, captions and a locked edit decision list. Output: Remotion render, optional Resolve timeline/interchange package, technical QA and human review, then an approved deliverable. Generation supplies assets; it does not replace editing.

Remotion is the primary programmable compositor. Resolve is optional for supervised finishing and timeline edits; an installed MCP does not prove the current app bridge or import works. Test a supplied clip through the actual editor before claiming it integrated. Never infer owner-footage consent from an arbitrary supplied file. Generated UI imagery is illustration, not proof that a business workflow runs.

## 5. Reporting and knowledge

Notion is a projection of one signed/versioned analysis release, not a second analytical database. If a release is missing, show COVERAGE_ONLY with date, source and missing analysis, never a substitute "current analytics" table followed by unrelated historic recommendations. Project stage status, denominators, findings with evidence, limitations and next decisions in that order. Keep children and manual content; stage changes, compare them and read back before marking synchronization complete.

Obsidian contains durable synthesis, operating decisions and links; raw transcripts/frames remain in private source storage. Separate active Reel decisions from the frozen YouTube knowledge summary. Global reports should explain what changed, what it means, what is known and what decision follows, not scatter metrics without a shared cohort.
