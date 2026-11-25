# FAILURES.md — Blocker & Troubleshooting Log

This document candidly logs the technical failures, edge-case blockers, model limitations, and bugs encountered during pipeline development, detailing the diagnosis, attempted mitigations, and final solutions.

---

### Failure 01: Cultural Textile Hallucination (Pan-African Model Bias)
- **Symptom**: Early keyframe generations for Ethiopian mothers produced bright West African wax-print patterns (Ankara/Kente) or turban headwraps rather than traditional Ethiopian *Netela* and *Habesha Kemis*.
- **Root Cause**: Training bias in foundation text-to-image datasets where "African mother" strongly correlates with West and South African cultural attire.
- **What We Tried**: 
  1. Adding `"Ethiopian"` as a standalone keyword (insufficient; still produced multicolored headwraps).
  2. Specifying negative prompts (`"turban, kente, wax print, bright multicolored pattern"`).
- **Final Solution**: Combined negative prompting with explicit structural terminology: *"draped in pure white Ethiopian Netela woven cotton scarf with delicate gold, green and red Tibeb geometric border along hem, hair modestly covered in sheer white cotton, authentic highland Wollo aesthetic"*. Resulted in 100% accurate cultural attire.

---

### Failure 02: API Rate Limiting (HTTP 429) During Burst Narration
- **Symptom**: Calling Gemini 3.8 Flash TTS sequentially for 12 shots triggered `429 RESOURCE_EXHAUSTED: Too Many Requests` around shot 5.
- **Root Cause**: Free tier burst rate limits on Google AI Studio endpoints restrict concurrent or back-to-back inference calls.
- **What We Tried**:
  1. Manual sleep intervals of 1.0 second (still triggered intermittent 429 on network jitter).
- **Final Solution**: Implemented an exponential backoff retry decorator with jitter in `pipeline/cache.py` (`backoff_factor=2.0`, `max_retries=4`, base delay `2.5s`). Combined with content-addressable SHA-256 caching so successful calls are never re-fetched.

---

### Failure 03: Video Identity Drift and Limb Warping in Wan 2.2
- **Symptom**: In Shot 4 (mother walking with harvest basket), Wan 2.2 generated realistic motion for 3 seconds, but then morphed the woven basket into a metallic bucket and generated an extra phantom hand.
- **Root Cause**: Overly complex motion prompts combined with high motion amplitude guidance ($>6.0$) on video diffusion models.
- **What We Tried**:
  1. Adding detailed negative prompts against deformation (helped slightly, but reduced motion fidelity).
  2. Prompting the entire scene again from scratch (caused complete identity loss).
- **Final Solution**: Trimmed the clip duration to 5.0 seconds, reduced motion strength parameter to 0.45, and isolated the motion prompt to camera push-in and natural breeze. Configured programmatic Ken Burns animation fallback in the pipeline when GPU rendering is unavailable.

---

### Failure 04: "Pumping" Sound Artifacts in Dynamic Audio Ducking
- **Symptom**: During initial FFmpeg assembly, the background music loudly surged and dipped unnaturally every time the narrator breathed between sentences.
- **Root Cause**: Default compressor attack and release times were too rapid (attack $20\text{ ms}$, release $200\text{ ms}$), creating an aggressive volume pump.
- **What We Tried**:
  1. Fixed static volume reduction (set music to $-24\text{ dB}$ throughout the entire film). Result: Music felt lifeless and completely inaudible during cinematic pauses.
- **Final Solution**: Tuned `sidechaincompress` filter with human-speech envelope constants:
  `sidechaincompress=threshold=0.02:ratio=6:attack=300:release=1200`
  The 300 ms attack gently cushions the entry of speech, while the 1200 ms release allows music to bloom naturally only during genuine scene transitions.

---

### Failure 05: Subtitle Text Truncation in Vertical (9:16) Feeds
- **Symptom**: Long narration sentences rendered across 3 lines, which caused the bottom line to be obscured by platform UI elements (TikTok description, sound title, Instagram share button).
- **Root Cause**: Subtitle generator used default desktop video positioning and had no character wrapping limit.
- **What We Tried**:
  1. Decreasing font size (subtitles became unreadable on mobile screens).
- **Final Solution**: Implemented a two-tier subtitle formatter: maximum 42 characters per line, strictly capped at 2 lines, positioned at an elevated bottom margin (`MarginV=140` for 9:16 vertical, `MarginV=70` for 16:9 horizontal) to maintain full clearance within platform safe zones.
