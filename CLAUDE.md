# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoVideo is an AI-powered automated promotional video generation system built in Python. It combines multiple AI technologies including LLM script generation, text-to-speech, semantic material matching, and video editing to automatically create high-quality promotional videos from user descriptions.

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Install GPU support (optional)
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Running the Application
```bash
# Start web interface (default)
python main.py

# Custom configuration
python main.py --config my_config.toml

# Custom host/port
python main.py --host 0.0.0.0 --port 8080

# Debug mode
python main.py --debug

# Public sharing
python main.py --share
```

### Code Quality
```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Run tests
pytest tests/ -v --cov=src
```

## Architecture Overview

### Core Components

**WorkflowManager** (`src/core/workflow_manager.py`) - Central orchestrator that coordinates the entire video generation pipeline from user input to final video output.

**ConfigManager** (`src/core/config.py`) - Handles TOML configuration file loading, validation, and provides centralized access to all system settings.

**GradioApp** (`src/ui/gradio_app.py`) - Web interface built with Gradio that provides user-friendly access to all functionality through tabs for video generation, material management, and settings.

### Processing Pipeline

The video generation follows this sequence:
1. **Script Generation** - LLM client creates video script based on user description
2. **Scene Parsing** - Script is parsed into individual scenes with timing
3. **Material Selection** - Random or semantic material matching for each scene
4. **TTS Synthesis** - Text-to-speech generates segmented audio with timing info
5. **Video Assembly** - Materials are compiled and trimmed to match audio duration
6. **Audio Integration** - TTS audio is merged with video
7. **Subtitle Generation** - Subtitles created from TTS timing information
8. **Final Rendering** - Subtitles rendered onto video with custom styling

### Key Modules

**LLMClient** (`src/modules/llm_client.py`) - Interfaces with DeepSeek API for script generation and scene analysis.

**TTSEngine** (`src/modules/tts_engine.py`) - Supports multiple TTS engines (Edge-TTS, SiliconFlow, pyttsx3) with segmented synthesis for accurate timing.

**SiliconFlowTTS** (`src/modules/siliconflow_tts.py`) - SiliconFlow API adapter for high-quality Chinese/English TTS with model switching support.

**VideoEditor** (`src/modules/video_editor.py`) - Uses FFmpeg for video processing, trimming, concatenation, and audio integration.

**SubtitleRenderer** (`src/modules/subtitle_renderer.py`) - Renders custom-styled subtitles with support for colors, fonts, positioning, and XML markup.

**MaterialSearcher/RandomMaterialSelector** (`src/modules/material_searcher.py`, `src/modules/random_material_selector.py`) - Manages material library with semantic search and random selection capabilities.

## Configuration

The system uses `config.toml` for all configuration. Key sections:
- `[llm]` - DeepSeek API settings
- `[tts]` - Text-to-speech engine configuration (engine selection)
- `[siliconflow_tts]` - SiliconFlow TTS API settings (api_key, model, voice)
- `[video]` - Video output settings (resolution, codec, etc.)
- `[subtitle]` - Typography and styling options
- `[paths]` - Directory structure for materials, output, temp files

## Important Implementation Details

### Dual Material Selection
The system supports both semantic matching (via sentence-transformers) and random selection. Random selection is currently preferred for reliability.

### Segmented TTS Processing
Text is split by punctuation and synthesized in segments to enable precise subtitle timing and better handling of long content. SiliconFlow TTS provides native segment support with better timing accuracy.

### Multiple TTS Engine Support
The system supports Edge TTS (free, Microsoft-based), SiliconFlow TTS (high-quality, API-based), and pyttsx3 (offline). SiliconFlow offers superior voice quality and wider parameter ranges but requires API key and internet connection.

### Duration Synchronization
The pipeline calculates actual TTS audio duration and adjusts material selection accordingly to ensure proper timing synchronization.

### Temporary File Management
All intermediate files are tracked and cleaned up automatically. Each task gets a unique ID for file organization.

### Error Handling
Comprehensive exception handling with fallback mechanisms (e.g., semantic search → random selection, segmented TTS → fallback synthesis).

## File Structure Conventions

- Source code in `src/` with organized subdirectories
- Configuration in TOML format
- Materials organized by type in `data/materials/`
- Output videos in `data/output/`
- Temporary files in `data/temp/`
- Logs in `logs/`

## Development Notes

- The system prioritizes reliability over advanced features
- FFmpeg is used directly instead of MoviePy for better performance
- All text processing supports Chinese characters and punctuation
- Subtitle rendering includes XML color tag support
- The workflow is designed to be resilient and provide meaningful error messages