# Prototype Showcase: LyricGen AI
> The next generation of high-fidelity lyric video production.

---

## 1. Product Vision
LyricGen is an AI-powered, browser-based **Non-Linear Editor (NLE)** designed for independent artists and visual directors. It transforms raw audio into production-ready 1080p lyric videos in minutes, combining state-of-the-art Speech-to-Text with cinematic motion design.

## 2. Core Innovation Pillars

### 🪄 AI "Magic" Auto-Lyrics
*   **Zero-Input Production:** Leverages **AssemblyAI** (2026 Universal Model) to transcribe audio with word-level precision.
*   **Smart Grouper Algorithm:** Intelligently clusters raw words into poetic lyric lines based on musical phrasing and natural breath gaps.

### 🎬 Professional NLE Timeline
*   **Multi-Track Architecture:** Dedicated layers for **Video (Cinematic Backgrounds)**, **Audio (Waveform)**, and **Lyrics (Clips)**.
*   **Precision Editing:** Full support for professional workflows: Visual Drag-and-Drop, Edge Trimming, and Playhead Splitting (Scissors Tool).
*   **Dynamic Ruler:** Frame-accurate time scale that auto-scales with zoom (up to 500px/s).

### 🎞️ Cinematic Preview Engine
*   **Real-time Compositor:** A high-performance stage that renders video, overlays, and typography layers in a single unified frame.
*   **Continuous Credit-Roll:** Moves beyond "jumping" lyrics to a smooth, movie-credit style scroll with predictive sub-pixel interpolation.
*   **Live Theme Sync:** Over 25+ aesthetic controls (Glow, Strokes, Gradients, Branding) that update instantly.

## 3. The 3-Step Production Workflow

1.  **Ingest:** Drop an MP3. Check the "Magic AI" box.
2.  **Compose:** Refine timings on the NLE timeline. Customize fonts and cinematic overlays in the Theme Editor.
3.  **Deliver:** Preview in Fullscreen. Export at 1080p (24/30/60 FPS).

## 4. Technical Architecture
*   **Frontend:** React (TypeScript) + Vite + Wavesurfer.js (Visual Engine).
*   **Backend:** FastAPI + MoviePy (Production Renderer) + Pillow (Typography Engine).
*   **AI Layer:** AssemblyAI Webhook-ready Transcription Service.
*   **Design System:** Dual-Theme (Micro Light for Marketing / OpenSea Dark for Production).

## 5. Multi-Platform Ready
*   **Responsive Canvas:** 16:9 (YouTube), 9:16 (TikTok), 4:5 (Instagram), 1:1 (Square).
*   **Dynamic Scaling:** Pixel-perfect rendering across all devices, from iPads to 4K monitors.
