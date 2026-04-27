# PROJECT JARVIS V3.0 (Autonomous Proto-AGI) 

This repository houses a highly modular, low-latency, and autonomous AI systems agent built for a macOS environment.

## ⚡ What Is Implemented?

### 1. Robust Production Scaffolding (Phase 1 & 2)
- Over **15 discrete micro-modules** spanning logical boundaries.
- Interfaces for extreme functionality are pre-built (Playwright web scrapers, AST python self-compilers, Home Assistant bindings).

### 2. The Production Core & Orchestration (Phase 3)
- **Hacker Bootloader UI:** Powered by the `rich` UI library and strictly validated utilizing **Pydantic V2**. `first_boot.py` verifies the OS capabilities.
- **Stream Interpolation & Tool Parsing Engine:** `llm_engine.py` operates natively on `AsyncGroq(stream=True)`. It structurally separates conversational text blocks (`delta.content`) from fragmented JSON object streams representing function schemas (`delta.tool_calls`), reliably formatting the outputs.

### 3. The Audio Sensory Matrix (Phase 4)
- **Continuous STT Ring Buffers:** `SensoryPipeline` uses an indefinite PyAudio stream feeding a 300-count array queue, preventing `pyaudio` socket collisions and completely negating "missed syllables" on quick trigger words natively mapped by Porcupine.
- **Biometric Security Engine:** `pyannote.audio` isolates 10 seconds of source target audio generating an `.pt` embedding. Every wake word immediately processes a 3s live chunk against it using cosine similarity arrays.
- **Global TTS Interface:** A Singleton `TTSManager` housing native macOS and premium `ElevenLabs` streams, mapped directly to an AST-swept OS tool (`voice_settings.py`) granting the Groq loop the ability to toggle its absolute global rendering state at will.

## 🧠 Application Processing Flow
1. **Initiation:** If context parameters lack definition in `/config`, `first_boot.py` securely bridges terminal inputs into a serialized `user_profile.json`. Same loop explicitly requires a `owner_voice_baseline.pt` matrix.
2. **Schema Generation:** The `DynamicLoader` searches the `/tools` directory. Utilizing AST and library introspection, it deduces the available tool methods and parameters.
3. **Continuous Execution:** The primary `Live` Rich dashboard loads. The continuous PyAudio listener (`audio/stt.py`) listens blindly until the Porcupine array identifies the wake phrase. It isolates the immediately trailing audio segment, pings the biometrics, and finally submits to `faster_whisper` creating the payload.
4. **Action Logging:** Groq natively determines to output a raw string or to enforce macro tool usage. Rather than immediately routing macros to macOS components locally, JARVIS securely halts implementation, mapping the parsed dictionary directly onto the right pane (`Active Context`). **NOTE: Phase 4 introduces an Explicit Macro Override purely to allow Groq to execute the TTS Toggle tool locally so the Singleton switch manifests visually.**

## 🔜 Remaining To Implement
- **Phase 5 (Full Physical Execution Privileges):** Disabling the NO-EXECUTE flag safely. Translating parsed Groq logic natively through `dynamic_loader.py` to trigger local AppleScript OS functions, Playwright background queries, and Docker resets.
- **Phase 6 (Vectorized Retention):** Mapping the `reflection_daemon.py` chronological thread cycles back to active state loops syncing into `chromadb`.
