# Emotion Detection Video Processor

A FastAPI service that accepts MP4 video uploads, stores them in MinIO, extracts audio, performs ASR transcription and emotion detection per timestamp, and persists metadata/results in MongoDB.

---

## Features

- **Upload**: Accepts MP4 video via `/process_video/`.
- **Storage**: Saves raw video & extracted WAV audio to MinIO.
- **Transcription**: Uses a Whisper-based ASR pipeline to generate text with timestamps.
- **Emotion Analysis**: Runs a Hugging Face text-classification model to detect emotions for each transcript chunk.
- **Persistence**: Stores metadata (paths, transcript text, timestamped chunks, emotion labels) in MongoDB under one document per upload.
- **Healthcheck**: `/healthcheck` endpoint to verify service is up.

---

## Tech Stack

- **FastAPI** — web framework  
- **MoviePy** — audio extraction  
- **Hugging Face Transformers** — ASR & emotion models  
- **MinIO (S3-compatible)** — object storage  
- **MongoDB** — metadata persistence  
- **Python 3.12+**  

---

## Requirements

- Python 3.12+  
- Docker

---

## Installation

### Clone this repository and run it:

   ```bash
   git clone https://github.com/your-org/emotion-detection-video.git
   cd emotion-detection-video
   docker compose up -d
   ```