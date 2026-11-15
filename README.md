---
title: AI Subtitle Generator
description: Free AI subtitle generator for video and audio
sdk: docker
app_port: 7860
---

# AI Subtitle Generator

Upload video/audio, transcribe speech with faster-whisper, edit subtitle text and timestamps, then export SRT or VTT.

This Space runs the open-source faster-whisper model on CPU. The first transcription may take time while the model is downloaded and loaded. Free hosting has limited CPU/RAM and may sleep when idle, so long videos can be slow or fail.
