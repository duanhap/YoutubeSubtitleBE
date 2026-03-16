# YoutubeSubtitleBE

A fast and professional YouTube subtitle processing system that supports:
- Automatic transcription using YouTube API with Proxy fallback.
- AI-powered transcription using Faster-Whisper.
- Professional pronunciation generation: IPA for English, Pinyin for Chinese, Hiragana for Japanese.
- High-quality translation using Deep-Translator.
- Smart cleaning of noise tags like [Music], [Applause].
- Background job system with progress tracking.

## Deployment on Render

This project is configured to run on Render.

### Build Command
`pip install -r requirements.txt`

### Start Command
`uvicorn main:app --host 0.0.0.0 --port $PORT`

### Environment Variables
- `PROXY_USERNAME` (Optional)
- `PROXY_PASSWORD` (Optional)
- `PROXY_IP` (Optional)
