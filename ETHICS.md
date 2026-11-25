# ETHICS.md — Ethics, Consent, Licenses & Provenance

## 1. Consent Policy & Likeness Gate
> **Mandatory Rubric Gate**: If a real person appears or is voiced without a recorded consent record in `ETHICS.md`, the film scores zero.

### Subject & Voice Likeness Declaration
- **Visual Likeness**: All human characters portrayed in *The Wisdom of Our Mothers* (the mother, the child, the classmates, the elder) are **$100\%$ synthetic AI-generated archetypes** produced via generative diffusion models (FLUX.2 / Wan 2.2). **No real living person's face, photograph, biometric scan, or likeness was cloned, trained upon, or utilized as an input image.**
- **Voiceover Likeness**: The narration audio is generated via **Gemini 3.8 Flash TTS standard multilingual synthetic voice endpoints** (Voice profile: warm, calm, unhurried). **No voice cloning, voice conversion, or imitation of any identifiable individual's voice** was performed.
- **Real Person Clearance**: Because all visual and audio elements depict composite fictional archetypes paying homage to a shared cultural experience rather than a specific living individual, no private non-consensual biometric processing occurred.
- If any real family photographs or voices are integrated in future custom cuts, explicit signed informed consent forms adhering to the template in Section 1.1 must be logged prior to inference.

### 1.1 Informed Consent Protocol Template (Future Family Archive Version)
```
[INFORMED CONSENT FOR AI MEDIA ARCHIVE]
Subject Name: [Composite Archetype - Fictional Representation]
Grantor: Creative Producer / Direct Family Descendant
Permitted Use: Heritage Short Film "The Wisdom of Our Mothers"
Scope: Academic submission (10 Academy), educational showcase, public social release.
Disclosure: The subject has been informed that generative AI tools will render video, voice, and score.
Watermark/Metadata: All outputs will retain AI provenance markers.
```

---

## 2. Model Licenses & Attribution Registry

All generative models and open-source libraries used throughout this project are verified for legal, commercial, and research distribution:

| Pipeline Component | Model / Tool | Source / Origin | License | Usage Terms & Attributions |
| :--- | :--- | :--- | :--- | :--- |
| **Pipeline Core & CLI** | Python 3.11, Pydantic, FastJSONSchema | Open Source | MIT / Python Software License | Fully permissive for all pipeline stages. |
| **Scripting & Prompts** | Gemini 3.8 Flash | Google DeepMind / Google Cloud | Google Terms of Service / API Terms | Commercial & educational API access; non-retraining on enterprise/studio calls. |
| **Narration (TTS)** | Gemini 3.8 Flash TTS | Google AI Studio | Google API Terms | Free tier usage; multi-language speech generation (Amharic & English). |
| **Keyframe Generation** | FLUX.1 schnell / FLUX.2 klein | Black Forest Labs | Apache 2.0 / Permissive open-weight | Open weights; commercial and non-commercial generation permitted. |
| **Motion Generation** | Wan 2.2 TI2V-5B | Wan-Video / Alibaba Cloud | Apache 2.0 | Fully open weights; free commercial & academic video generation. |
| **Audio Scoring** | ACE-Step 1.5 | ACE-Step Community | MIT License | Permissive open weights; outputs usable commercially. |
| **Video Assembly** | FFmpeg (libavcodec, libavfilter) | FFmpeg Project | LGPL 2.1+ / GPL | Industry-standard open-source media transcoding engine. |

---

## 3. Labeling, Transparency & AI Disclosure Plan

### Visible On-Screen AI Disclosure
- In compliance with challenge specifications and international synthetic media guidelines, **every export (both 16:9 and 9:16) concludes with a mandatory 4-second end card**:
  ```
  "Made with AI • Dedicated to our mothers • የእናቶቻችን ጥበብ"
  "Created with Gemini, FLUX, Wan 2.2, ACE-Step & FFmpeg"
  ```

### Platform-Level Synthetic Media Disclosures
When published to social platforms, the respective built-in AI labels will be actively toggled:
- **YouTube Shorts & YouTube Studio**: *"Altered or synthetic content: Sound or visuals were significantly altered or generated digitally."* Checked **YES**.
- **TikTok**: *"AI-generated content"* tag activated during upload.
- **Instagram / Meta**: *"AI info: Content created or edited using AI"* toggle activated.

### Metadata Preservation (C2PA & SynthID)
- Audio and video containers are processed through FFmpeg without stripping provenance tags.
- Generation logs (`runs.jsonl`) are committed directly to the public GitHub repository to provide complete cryptographic transparency of all prompts, seeds, model versions, and outputs.

---

## 4. Privacy & Data Protection Safeguards
- No private personal records, identification numbers, addresses, or private family disputes are included in prompt tokens or metadata.
- All API interactions use isolated environment variables (`.env`) which are strictly excluded from git tracking via `.gitignore`.
