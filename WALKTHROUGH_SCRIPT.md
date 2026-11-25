# WALKTHROUGH_SCRIPT.md — Walkthrough Video Recording Guide
**Target Duration**: 3 to 4 minutes (Strict rubric ceiling: at most 5 minutes)

---

## Shot-by-Shot Walkthrough Video Outline

### Section 1: Introduction & Emotional Motivation (0:00 – 0:45)
- **Visual**: Show the finished 16:9 or 9:16 film playing on screen (first 15 seconds) or opening shot.
- **What to Say**:
  > *"Hello! This is 'The Wisdom of Our Mothers' (የእናቶቻችን ጥበብ)—a 75-second heritage tribute to unlettered Ethiopian mothers who could not read their children's textbooks, but whose relentless sacrifices unlocked every classroom door their children now walk through.*
  > *Rather than editing this video by hand in Premiere or CapCut, we built a small studio in code: an automated, reproducible AI pipeline driven by a single machine-readable contract: `storyboard.json`."*

### Section 2: Pipeline Architecture & Contracts (0:45 – 1:45)
- **Visual**: Show `storyboard.json`, `schema/storyboard.schema.json`, and the `pipeline/` directory.
- **What to Say**:
  > *"The architecture follows clean stage boundaries:
  > 1. Stage 1 validates `storyboard.json` against a strict JSON Schema before every run.
  > 2. Stage 2 generates voice narration line-by-line using Gemini Flash TTS and assembles the Phase 1 Radio Cut.
  > 3. Stage 3 renders consistent keyframes using our cultural style block and character sheet.
  > 4. Stage 4 animates still frames into 24fps motion clips with Ken Burns physics or Wan 2.2.
  > 5. Stage 5 generates and auditions our ACE-Step 1.5 acoustic score featuring traditional Begena harp and cello.
  > 6. Stage 6 uses programmatic FFmpeg compositing to execute dynamic sidechain ducking, EBU R128 loudness normalization to minus 14 LUFS, and renders both horizontal 16:9 and vertical 9:16 exports with burned-in subtitles and our AI disclosure end card."*

### Section 3: One Hard Decision (1:45 – 2:30)
- **Visual**: Bring up `DESIGN.md` or `FAILURES.md` on screen.
- **What to Say**:
  > *"Our hardest engineering decision was overcoming cultural textile hallucination in text-to-image diffusion models. Early prompts generated generic pan-African wax prints or turbans. To achieve authentic Ethiopian representation, we engineered a dedicated style block enforcing pure white handwoven cotton Netela scarves with delicate geometric Tibeb embroidery and authentic highland domestic architecture.
  > In addition, our User Test 1 with three target audience members revealed that the opening narration pacing needed breathing room. We slowed down the delivery and added pauses between chapters to let the emotional reverence land."*

### Section 4: Live Shot Regeneration Demo (The Test of Caching) (2:30 – 3:30)
- **Visual**: Open terminal and `storyboard.json` side-by-side.
- **What to Say & Do**:
  1. Open terminal: run `python run_pipeline.py`.
     > *"Notice that because of our content-addressable SHA-256 caching engine, all 13 shots hit the cache instantly."*
  2. In `storyboard.json`, change Shot 7's subtitle or motion prompt slightly (e.g. change `"Extreme Close-Up"` to `"Macro Extreme Close-Up"` or edit one word).
  3. Rerun `python run_pipeline.py`.
  4. Point to terminal output and `runs.jsonl`:
     > *"Watch the terminal: Shot 1 through 6 and 8 through 13 report [CACHED] in milliseconds. ONLY Shot 7 is regenerated and re-rendered. This proves our pipeline is truly modular, saves GPU quota, and guarantees deterministic reproducibility."*

### Section 5: Conclusion & Reproducibility (3:30 – 4:00)
- **Visual**: Show `outputs/exports/film_16x9_heritage_short.mp4` and `film_9x16_heritage_short.mp4`.
- **What to Say**:
  > *"Every model call, parameter, seed, and latency is committed to `runs.jsonl`. A stranger can clone this repository, run `python run_pipeline.py`, and recreate this film from scratch. Thank you!"*
