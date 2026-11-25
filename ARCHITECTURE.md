# ARCHITECTURE.md — Pipeline Architecture & Technical Contract

## 1. System Overview & Philosophy

The pipeline is structured as an **automated, deterministic, multi-stage studio in code**. It takes a single machine-readable contract—`storyboard.json`—and translates it into broadcast-ready video deliverables without human timeline editing.

```
                                  [storyboard.json]
                                          │
                                          ▼
                         [Stage 1: Schema Validation]
                        (fastjsonschema / jsonschema)
                                          │
         ┌──────────────────┬─────────────┴─────────────┬──────────────────┐
         │                  │                           │                  │
         ▼                  ▼                           ▼                  ▼
[Stage 2: Narration] [Stage 3: Keyframes]     [Stage 4: Moving Shots] [Stage 5: Music Score]
 Gemini Flash TTS      FLUX.2 klein /            Wan 2.2 TI2V /          ACE-Step 1.5 /
   (WAV per shot)     Cloudflare Workers        Ken Burns Pan-Zoom       Acoustic Score
         │                  │                           │                  │
         └──────────────────┼───────────────────────────┴──────────────────┘
                            │
                            ▼
                  [Stage 6: Assembly & Export]
                  FFmpeg Programmatic Compositor
                  - Subtitle burn-in (SRT)
                  - Sidechain audio ducking
                  - EBU R128 loudness normalisation (-14 LUFS)
                  - Dual export: 16:9 (Landscape) & 9:16 (Vertical)
                            │
                            ▼
                  [outputs/exports/film_*.mp4]
```

---

## 2. The Single Source of Truth: `storyboard.json`

Every stage is a standalone executable Python module inside `pipeline/` that reads `storyboard.json` and writes its artifacts into `outputs/<stage>/`. 

### Key Principles of the Contract:
1. **Explicit Prompts**: All visual prompts, motion prompts, and audio lyrics are declared explicitly in the JSON. No dynamic prompt formatting is hidden inside stage code.
2. **Fixed Random Seeds**: Each shot is assigned an explicit integer `seed` to guarantee deterministic reproduction across model runs.
3. **Declared Stated Reason**: In accordance with design thinking principles, every shot carries a `stated_reason` property defining its emotional narrative function.

---

## 3. Content-Addressable Caching Engine

To protect GPU quotas, prevent wasteful API spend, and enable fast incremental iteration:
- Each stage calculates an **Input Hash (SHA-256)** over all inputs relevant to a given artifact:
  $$\text{Hash} = \text{SHA256}(\text{StageName} + \text{ModelVersion} + \text{Prompt} + \text{Seed} + \text{Parameters})$$
- Output files are keyed by shot ID and input hash:
  `outputs/keyframes/shot_03_<hash>.png`
- When a stage executes:
  1. Computes the target hash.
  2. If the file exists and is valid, logs `cached: true` in `runs.jsonl` and skips inference.
  3. If missing or changed, performs inference, saves the artifact, and logs `cached: false` with measured latency.
- **Walkthrough Video Verification**: Changing a single sentence in Shot 7's prompt causes **only Shot 7** to invalidate its cache, leaving the remaining 11 shots untouched.

---

## 4. Resilience & Fallback Hierarchy

Network timeouts, GPU out-of-memory errors, and rate limits are expected in AI production. The pipeline implements an active fallback matrix:

```
[Moving Shot Request]
         │
         ├──► 1. Attempt Wan 2.2 TI2V-5B (Remote GPU / Kaggle API)
         │       └── Success ──► Write MP4 clip
         │
         └──► 2. If Quota / Timeout / Out of Memory:
                 └── Fallback: Smooth Ken Burns Pan & Zoom (FFmpeg zoompan)
                     applied to FLUX Keyframe ──► Broadcast-quality 24fps motion shot
```

```
[Narration TTS Request]
         │
         ├──► 1. Gemini 3.8 Flash TTS (Cloud API)
         │       └── Success ──► High-fidelity natural speech
         │
         └──► 2. If Network Drop / Rate Limit 429:
                 └── Exponential backoff retry (3 attempts)
                 └── Secondary Fallback: Local acoustic synthesis / pre-rendered golden WAV
```

---

## 5. Audio Engineering & Master Mix Specification

The audio track follows professional post-production standards:
1. **Loudness Normalization**: Master audio is processed via FFmpeg's `loudnorm` filter (EBU R128 standard):
   - Integrated Loudness target: **$-14.0\text{ LUFS}$**
   - Loudness Range (LRA): **$7.0\text{ LU}$**
   - True Peak ceiling: **$-1.0\text{ dBFS}$**
2. **Dynamic Voice Ducking**: The score is dynamically ducked under the voice using `sidechaincompress`:
   - Threshold: **$0.02$**
   - Ratio: **$6.0$**
   - Attack: **$300\text{ ms}$**
   - Release: **$1200\text{ ms}$**
   This ensures zero frequency masking, keeping narration crisp and intelligible while letting music swell in pauses.

---

## 6. Dual-Aspect Ratio Rendering (16:9 vs 9:16)

Social platforms demand vertical $9:16$ video, while traditional displays require horizontal $16:9$. 
- The pipeline composes all keyframe subjects with center-weighted framing.
- The assembly stage renders:
  1. **Horizontal (1920x1080)**: Native cinematic composition.
  2. **Vertical (1080x1920)**: Intelligent center-crop with safe-area subtitle positioning (leaving the top and bottom $15\%$ free from UI obstruction).
