# The Wisdom of Our Mothers (የእናቶቻችን ጥበብ)
### A 75-Second Heritage Short Film & Automated Multi-Model Studio Pipeline

> *"They were not given every opportunity to learn, but they made sure we had the opportunity they never had."*

This repository contains both a short film paying tribute to unlettered Ethiopian mothers who made education their supreme sacrifice, and the **fully automated AI studio in code** that creates it. 

A stranger can clone this repository, run **one command**, and deterministically regenerate the film from its storyboard contract.

---

## 1. Quickstart: One-Command Run

### Prerequisites
- Python 3.10+
- FFmpeg installed and in PATH (or Gyan.FFmpeg on Windows)

### Installation
```bash
git clone https://github.com/your-username/ai-content-generation.git
cd ai-content-generation
pip install -r requirements.txt
```

### Run the Pipeline
```bash
python run_pipeline.py
```
This executes all 6 stages sequentially, computes content-addressable SHA-256 hashes, logs every call to `runs.jsonl`, and renders both aspect ratios to `outputs/exports/`.

---

## 2. Advanced Usage & Live Shot Regeneration

The pipeline supports modular stage runs, cache bypass, and selective shot regeneration:

```bash
# Run only a specific stage
python run_pipeline.py --stage stage1   # Schema validation only
python run_pipeline.py --stage stage2   # Narration and radio cut
python run_pipeline.py --stage stage6   # Assembly and master exports

# Force regeneration (ignore cache)
python run_pipeline.py --force

# Live Demo: Change one prompt in storyboard.json and rerun
python run_pipeline.py
# (Only the modified shot will regenerate; all other shots hit the cache!)
```

---

## 3. Repository Architecture

```
├── README.md                 # Project overview, one-command run, instructions
├── storyboard.json           # Central contract: 13 shots, prompts, cues, durations, seeds
├── schema/
│   └── storyboard.schema.json# JSON Schema validated before every pipeline run
├── pipeline/
│   ├── config.py             # Constants, media specs, paths, environment loader
│   ├── logger.py             # Structured audit logger writing to runs.jsonl
│   ├── cache.py              # Content-addressable SHA-256 caching engine
│   ├── stage1_schema_validate.py # Validates storyboard against schema
│   ├── stage2_narration.py   # Generates narration & Phase 1 Radio Cut
│   ├── stage3_keyframes.py   # Generates keyframes with character consistency
│   ├── stage4_shots.py       # Animates keyframes to 24fps motion clips
│   ├── stage5_music.py       # Original score generation (ACE-Step 1.5)
│   ├── stage6_assemble.py    # FFmpeg sidechain ducking, loudnorm, subtitles, exports
│   └── run.py                # Master orchestrator
├── runs.jsonl                # Immutable audit log for every model call
├── outputs/                  # Generated assets cached by SHA-256 hash
│   ├── narration/            # WAV voice lines per shot
│   ├── keyframes/            # 1920x1080 keyframe still images
│   ├── shots/                # 24fps MP4 video clips
│   ├── music/                # ACE-Step candidates and selected score
│   ├── assembly/             # Subtitles (SRT), video reel, radio cut, mixed audio
│   └── exports/              # Final film exports (16:9 and 9:16)
├── DESIGN.md                 # Audience, emotional intent, user testing records
├── ARCHITECTURE.md           # Technical architecture, contracts, caching, retries
├── EXPERIMENTS.md            # 10 logged hypothesis -> change -> result experiments
├── FAILURES.md               # Real blockers encountered and how they were solved
├── COSTS.md                  # Latency, GPU minutes, list-price equivalent ($0 actual spend)
└── ETHICS.md                 # Consent declaration, model licenses, AI labeling plan
```

---

## 4. The 5 Pipeline Stages & Contracts

1. **Stage 1: Validation**: `storyboard.json` is validated against `schema/storyboard.schema.json` using `jsonschema`.
2. **Stage 2: Narration (Gemini Flash TTS)**: Generates line-by-line speech and compiles the Phase 1 Radio Cut (`radio_cut.wav` and `radio_cut_preview.mp4`).
3. **Stage 3: Keyframes (FLUX.1 / FLUX.2 klein)**: Renders 1920x1080 keyframes conditioned on our Ethiopian cultural style block and character sheet.
4. **Stage 4: Moving Shots (Wan 2.2 / Ken Burns zoompan)**: Animates stills into 24fps video clips with smooth pan and zoom physics.
5. **Stage 5: Music (ACE-Step 1.5)**: Auditions 3 candidate heritage acoustic scores (Begena harp, Masenqo, acoustic guitar, warm cello) and selects the best underscore.
6. **Stage 6: Assembly (FFmpeg Compositor)**:
   - Dynamic voice ducking (`sidechaincompress`: attack 300ms, release 1200ms, threshold 0.02)
   - Loudness normalization (`loudnorm`: $-14\text{ LUFS}$, true peak $-1\text{ dBFS}$)
   - Burned-in subtitles with platform safe-area margins
   - Mandatory AI disclosure and dedication end card
   - Exports: `film_16x9_heritage_short.mp4` & `film_9x16_heritage_short.mp4`

---

## 5. Compute, Quotas & Costs

- **Actual Project Spend**: **$0.00** (Runs entirely on free developer tiers: Google AI Studio, Cloudflare Workers AI, Kaggle 2x T4 GPU, local FFmpeg).
- **Equivalent Frontier Commercial Cost**: **~$14.70** per 75-second film.
- **Cache Efficiency**: A full cold run takes ~20 minutes; a cached verification run completes in **under 0.25 seconds**.

---

## 6. Ethics, Consent & Provenance

- **Consent Policy**: All characters and voices are $100\%$ synthetic AI archetypes honoring our collective mothers. No private living person's biometric likeness was cloned without consent.
- **Licenses**: Wan 2.2 (Apache 2.0), ACE-Step 1.5 (MIT), FLUX (Apache 2.0 / open weights), FFmpeg (LGPL 2.1+).
- **Disclosure**: Platform AI labels toggled ON; final end card visibly declares *"Made with AI • Dedicated to our mothers • የእናቶቻችን ጥበብ"*.
