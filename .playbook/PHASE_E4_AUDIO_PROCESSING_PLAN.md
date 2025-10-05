# Phase E.4 - Audio Processing Implementation

**Status**: 🔜 **NEXT IN QUEUE**  
**Priority**: MEDIUM (completes multi-channel experience)  
**Estimated Duration**: 4-5 hours  
**Dependencies**: E.2 (WhatsApp client), E.3 (Rasa NLP)

---

## 🎯 Objective

Complete audio processing infrastructure with production-ready Speech-to-Text (STT), Text-to-Speech (TTS), and audio conversion capabilities for real-time voice interactions via WhatsApp.

---

## 📋 Current State Analysis

### Existing Implementation ✅
- ✅ Basic `AudioProcessor` class structure
- ✅ `WhisperSTT` skeleton (mock implementation)
- ✅ `ESpeakTTS` skeleton (stub implementation)
- ✅ Temporary file management (context managers)
- ✅ Integration with `Orchestrator` (line 7, 30, 42-47)
- ✅ `audio_converter.py` with `ogg_to_wav()` function
- ✅ Settings: `audio_enabled`, `tts_engine` enum

### Missing Implementation ❌
- ❌ Real Whisper STT integration (currently mock)
- ❌ Real eSpeak TTS implementation (returns None)
- ❌ Audio download from WhatsApp (`_download_audio`)
- ❌ Audio conversion (`_convert_to_wav`)
- ❌ Audio quality optimization
- ❌ Prometheus metrics for audio operations
- ❌ Comprehensive error handling
- ❌ Tests (integration + E2E)
- ❌ Documentation

### Settings Available
```python
audio_enabled: bool = True
tts_engine: TTSEngine = TTSEngine.ESPEAK  # or COQUI
```

---

## 🔧 Tasks Breakdown

### Task 1: Complete Whisper STT Integration (60 min)
**File**: `app/services/audio_processor.py` - `WhisperSTT` class  
**Status**: Mock implementation, needs real Whisper integration

**Requirements**:
- Install `openai-whisper` dependency (or `faster-whisper`)
- Load Whisper model (`base` or `small` for speed/accuracy balance)
- Implement real `transcribe()` method
- Support Spanish language (`language="es"`)
- Return confidence score (word-level or segment-level)
- Handle different audio formats (wav, ogg, mp3)
- Add timeout handling (max 30s per transcription)
- Structured logging (transcription start, duration, confidence)
- Error handling (`TranscriptionError`, `ModelLoadError`)

**Expected Output**:
```python
{
    "text": "Hola, quisiera reservar una habitación doble para mañana",
    "confidence": 0.87,
    "language": "es",
    "duration_sec": 3.5,
    "success": True
}
```

---

### Task 2: Complete eSpeak TTS Implementation (45 min)
**File**: `app/services/audio_processor.py` - `ESpeakTTS` class  
**Status**: Returns None, needs full implementation

**Requirements**:
- Install `espeak-ng` system package
- Use `subprocess` or `pyttsx3` for synthesis
- Generate audio in OGG Opus format (WhatsApp compatible)
- Support Spanish voice (`-v es` or `voice="spanish"`)
- Adjust speech rate for clarity (`-s 160` words/min)
- Use FFmpeg to convert WAV → OGG Opus
- Add timeout handling (max 10s per synthesis)
- Structured logging (synthesis start, duration, output size)
- Error handling (`SynthesisError`, `FFmpegError`)

**Expected Output**:
```python
bytes  # OGG Opus audio data (WhatsApp compatible)
```

---

### Task 3: Implement Audio Download from WhatsApp (30 min)
**File**: `app/services/audio_processor.py` - `_download_audio()` method  
**Status**: Commented out, needs implementation

**Requirements**:
- Use `WhatsAppMetaClient.download_media()` (already implemented in E.2)
- Download audio from `media_url` (requires access token)
- Save to temporary file (use existing context manager)
- Support WhatsApp audio formats (opus, ogg, m4a, amr)
- Add timeout handling (max 30s per download)
- Retry logic (3 attempts with exponential backoff)
- Structured logging (download start, size, format)
- Error handling (`MediaDownloadError`, `MediaNotFoundError`)

**Integration**:
```python
async def _download_audio(self, media_url: str, output_path: Path):
    from .whatsapp_client import WhatsAppMetaClient
    client = WhatsAppMetaClient()
    audio_bytes = await client.download_media(media_url)
    output_path.write_bytes(audio_bytes)
```

---

### Task 4: Implement Audio Conversion (30 min)
**File**: `app/services/audio_processor.py` - `_convert_to_wav()` method  
**Status**: Commented out, needs implementation

**Requirements**:
- Use existing `audio_converter.py` → `ogg_to_wav()` function
- Convert OGG/Opus/M4A → WAV (16kHz, mono, PCM)
- Use FFmpeg with optimized flags
- Add timeout handling (max 15s per conversion)
- Validate output file exists and non-empty
- Structured logging (conversion start, duration, file sizes)
- Error handling (`ConversionError`, `FFmpegNotFoundError`)

**Implementation**:
```python
async def _convert_to_wav(self, input_path: Path, output_path: Path):
    from ..utils.audio_converter import ogg_to_wav
    result = await ogg_to_wav(input_path)
    if result:
        result.rename(output_path)
```

---

### Task 5: Add Prometheus Metrics (30 min)
**File**: `app/services/audio_processor.py`  
**Status**: No metrics, needs comprehensive instrumentation

**Requirements**:
- Add audio operation counters:
  - `audio_transcriptions_total{status=success|error}`
  - `audio_synthesis_total{status=success|error, engine=espeak|coqui}`
  - `audio_downloads_total{status=success|error}`
  - `audio_conversions_total{status=success|error}`
  
- Add latency histograms:
  - `audio_transcription_latency_seconds{model=base|small}`
  - `audio_synthesis_latency_seconds{engine=espeak|coqui}`
  - `audio_download_latency_seconds`
  - `audio_conversion_latency_seconds`

- Add audio quality gauges:
  - `audio_transcription_confidence` (histogram)
  - `audio_file_size_bytes{type=input|output}`
  - `audio_duration_seconds`

**Implementation Pattern**:
```python
from prometheus_client import Counter, Histogram

audio_transcriptions_total = Counter(
    "audio_transcriptions_total",
    "Total audio transcriptions",
    ["status"]
)

audio_transcription_latency = Histogram(
    "audio_transcription_latency_seconds",
    "Audio transcription latency",
    ["model"]
)

# In transcribe():
with audio_transcription_latency.labels(model="base").time():
    result = await whisper_transcribe(...)
    audio_transcriptions_total.labels(status="success").inc()
```

---

### Task 6: Enhanced Error Handling (30 min)
**File**: `app/exceptions/audio_exceptions.py` (NEW)  
**Status**: No audio-specific exceptions, needs hierarchy

**Requirements**:
- Create exception hierarchy:
  - `AudioProcessingError` (base)
  - `TranscriptionError` (STT failures)
  - `SynthesisError` (TTS failures)
  - `AudioDownloadError` (download failures)
  - `AudioConversionError` (FFmpeg failures)
  - `ModelLoadError` (Whisper model loading)
  - `FFmpegNotFoundError` (FFmpeg not installed)

- Structured error context:
  - `audio_url`, `file_path`, `format`
  - `error_code`, `status_code` (for HTTP errors)
  - `duration`, `file_size`

**Implementation**:
```python
class AudioProcessingError(Exception):
    def __init__(self, message: str, context: dict = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)
    
    def to_dict(self):
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "context": self.context
        }
```

---

### Task 7: Integration Tests (60 min)
**File**: `tests/integration/test_audio_integration.py` (NEW)  
**Status**: No audio tests, needs comprehensive coverage

**Requirements**:
- TestWhisperSTT (5 tests):
  - `test_transcribe_spanish_audio` - Spanish WAV transcription
  - `test_transcribe_different_formats` - OGG, MP3, M4A support
  - `test_transcribe_confidence_score` - Confidence ≥0.7 for clear audio
  - `test_transcribe_timeout` - 30s timeout handling
  - `test_transcribe_model_not_loaded` - Graceful fallback

- TestESpeakTTS (5 tests):
  - `test_synthesize_spanish_text` - Spanish voice generation
  - `test_synthesize_ogg_format` - WhatsApp-compatible OGG output
  - `test_synthesize_long_text` - Text >200 chars (chunking)
  - `test_synthesize_timeout` - 10s timeout handling
  - `test_synthesize_ffmpeg_error` - FFmpeg failure handling

- TestAudioProcessor (8 tests):
  - `test_transcribe_whatsapp_audio_success` - Full flow (download → convert → transcribe)
  - `test_transcribe_audio_download_error` - Media not found
  - `test_transcribe_conversion_error` - FFmpeg failure
  - `test_generate_audio_response_success` - TTS generation
  - `test_generate_audio_response_synthesis_error` - TTS failure
  - `test_temporary_file_cleanup` - No file leaks
  - `test_audio_metrics` - Prometheus counters incremented
  - `test_audio_latency_tracking` - Latency histograms updated

**Mock Strategy**:
```python
@pytest_asyncio.fixture
async def audio_processor():
    processor = AudioProcessor()
    # Mock Whisper model
    processor.stt.model = MagicMock()
    processor.stt.model.transcribe.return_value = {
        "text": "Hola, quisiera reservar",
        "segments": [{"avg_logprob": -0.3}]
    }
    return processor
```

---

### Task 8: E2E Tests (45 min)
**File**: `tests/e2e/test_audio_e2e.py` (NEW)  
**Status**: No E2E audio tests

**Requirements**:
- TestWhatsAppAudioFlow (4 tests):
  - `test_whatsapp_audio_to_text_reservation` - Audio msg → STT → NLP → reservation
  - `test_whatsapp_audio_with_tts_response` - Audio msg → process → TTS response
  - `test_whatsapp_audio_low_confidence` - Low STT confidence → clarification
  - `test_whatsapp_audio_unsupported_format` - Unsupported audio format error

**Sample Test**:
```python
async def test_whatsapp_audio_to_text_reservation(test_client):
    # 1. Webhook receives audio message
    payload = sample_whatsapp_webhook_audio
    
    # 2. Mock STT transcription
    with patch("app.services.audio_processor.WhisperSTT.transcribe") as mock_stt:
        mock_stt.return_value = {
            "text": "Quiero reservar una habitación doble para mañana",
            "confidence": 0.89,
            "success": True
        }
        
        # 3. Post webhook
        response = await test_client.post("/webhooks/whatsapp", json=payload)
        
        # 4. Verify STT called
        assert mock_stt.called
        
        # 5. Verify NLP processed text
        # (orchestrator should have received transcribed text)
```

---

### Task 9: Documentation (30 min)
**File**: `PROJECT_GUIDE.md`  
**Status**: No audio processing section

**Requirements**:
- New section: "## 🎤 Audio Processing & Voice Interactions"
- Prerequisites:
  - System packages: `espeak-ng`, `ffmpeg`
  - Python packages: `openai-whisper` (or `faster-whisper`), `pyttsx3`
- Configuration:
  - `.env`: `AUDIO_ENABLED=true`, `TTS_ENGINE=espeak`
- Audio flow diagram:
  - WhatsApp audio → Download → Convert → Transcribe → NLP → Respond
- Model selection:
  - Whisper: `base` (fast, 0.5s), `small` (balanced, 1s), `medium` (accurate, 3s)
  - TTS: `espeak` (fast, robotic), `coqui` (slow, natural)
- Performance targets:
  - STT latency: <2s (base), <5s (small)
  - TTS latency: <1s (espeak), <3s (coqui)
  - Total audio flow: <8s end-to-end
- Monitoring:
  - 8 Prometheus metrics (counters, histograms, gauges)
  - Grafana dashboard: "Audio Performance"
- Testing:
  - Commands: `pytest tests/integration/test_audio_integration.py -v`
- Troubleshooting:
  - Whisper model loading errors
  - FFmpeg installation issues
  - Audio format compatibility
  - Performance optimization tips
- Resources:
  - Whisper docs: https://github.com/openai/whisper
  - eSpeak docs: http://espeak.sourceforge.net/
  - FFmpeg audio docs: https://ffmpeg.org/ffmpeg-formats.html

---

## 📊 Success Criteria

### Functionality ✅
- [ ] Whisper STT transcribing Spanish audio (≥85% accuracy)
- [ ] eSpeak TTS generating Spanish audio (clear, intelligible)
- [ ] Audio download from WhatsApp (all formats)
- [ ] Audio conversion (OGG/M4A → WAV)
- [ ] Temporary file cleanup (no leaks)
- [ ] Audio metrics tracked (Prometheus)

### Performance ✅
- [ ] STT latency: <2s (base model), <5s (small model)
- [ ] TTS latency: <1s (espeak), <3s (coqui)
- [ ] Audio download: <5s (typical 5s audio)
- [ ] Audio conversion: <2s (5s audio)
- [ ] Total audio flow: <8s end-to-end

### Testing ✅
- [ ] 18+ integration tests passing (5 STT + 5 TTS + 8 AudioProcessor)
- [ ] 4+ E2E tests passing (WhatsApp audio flow)
- [ ] Mock Whisper model for tests
- [ ] No type errors

### Documentation ✅
- [ ] PROJECT_GUIDE.md updated (200+ lines audio section)
- [ ] Configuration documented (audio_enabled, tts_engine)
- [ ] Performance targets documented
- [ ] Troubleshooting guide
- [ ] Examples provided

### Observability ✅
- [ ] Structured logging (audio.* events)
- [ ] Prometheus metrics (8 new metrics)
- [ ] Audio quality tracking (confidence, duration)
- [ ] Performance monitoring (latency histograms)

---

## 📈 Expected Impact

### Metrics Before E.4:
- Quality Score: 9.8/10
- Test Coverage: 110 tests
- Audio Features: Mock STT, no TTS
- Code Completeness: ~95%
- Multi-channel: Text only (WhatsApp, Gmail)

### Metrics After E.4:
- Quality Score: **9.9/10** ⬆️ (+0.1)
- Test Coverage: **132+ tests** ⬆️ (+22 tests, +20%)
- Audio Features: **Real STT + TTS** ⬆️ (production-ready)
- Code Completeness: **~98%** ⬆️ (+3%)
- Multi-channel: **Text + Voice** ⬆️ (complete experience)

---

## ⏱️ Timeline

| Task | Duration | Status |
|------|----------|--------|
| 1. Whisper STT Integration | 60 min | ⏳ PENDING |
| 2. eSpeak TTS Implementation | 45 min | ⏳ PENDING |
| 3. Audio Download | 30 min | ⏳ PENDING |
| 4. Audio Conversion | 30 min | ⏳ PENDING |
| 5. Prometheus Metrics | 30 min | ⏳ PENDING |
| 6. Error Handling | 30 min | ⏳ PENDING |
| 7. Integration Tests | 60 min | ⏳ PENDING |
| 8. E2E Tests | 45 min | ⏳ PENDING |
| 9. Documentation | 30 min | ⏳ PENDING |
| **TOTAL** | **5h 30min** | **0%** |

---

## 🚀 Execution Plan

### Prerequisites
```bash
# Install system packages
sudo apt-get update
sudo apt-get install -y espeak-ng ffmpeg

# Install Python packages (add to requirements.txt)
pip install openai-whisper  # or faster-whisper for production
pip install pyttsx3  # optional, for TTS alternative
```

### Execution Order
1. **Task 6 first**: Create exception hierarchy (foundation)
2. **Task 3**: Implement audio download (enables testing)
3. **Task 4**: Implement audio conversion (pipeline)
4. **Task 1**: Complete Whisper STT (core feature)
5. **Task 2**: Complete eSpeak TTS (core feature)
6. **Task 5**: Add Prometheus metrics (observability)
7. **Task 7**: Integration tests (validation)
8. **Task 8**: E2E tests (end-to-end validation)
9. **Task 9**: Documentation (knowledge transfer)

### Validation Steps
```bash
# After each task, validate:
1. Run specific tests: pytest tests/integration/test_audio_integration.py::TestWhisperSTT -v
2. Check metrics: curl http://localhost:8000/metrics | grep audio_
3. Test E2E: pytest tests/e2e/test_audio_e2e.py -v
4. Validate errors: python -m pytest tests/ -k "audio" --tb=short
```

---

## 📦 Dependencies

### System Packages
- `espeak-ng` (Text-to-Speech engine)
- `ffmpeg` (Audio conversion)
- `libsndfile1` (Audio I/O, required by Whisper)

### Python Packages
- `openai-whisper==20230314` (or `faster-whisper` for production)
- `pyttsx3==2.90` (optional TTS alternative)
- Already installed: `httpx`, `prometheus_client`, `pytest-asyncio`

---

## 🎯 Next Action

**Start with Task 6 (Error Handling)**:
1. Create `app/exceptions/audio_exceptions.py`
2. Define 7-tier exception hierarchy
3. Implement `to_dict()` methods
4. Add structured context

**Then proceed with Task 3 (Audio Download)**:
1. Integrate `WhatsAppMetaClient.download_media()`
2. Implement `_download_audio()` method
3. Add retry logic and timeouts

---

**Phase**: E.4 - Audio Processing  
**Status**: 🔜 NEXT IN QUEUE  
**Date**: October 5, 2025  
**Priority**: MEDIUM (completes multi-channel guest experience)
