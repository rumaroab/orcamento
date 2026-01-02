# Quick Setup Guide: Qwen2.5:3b-instruct with Ollama

This guide shows you how to use Qwen2.5:3b-instruct locally with Ollama for budget document processing.

## Prerequisites

1. Install Ollama from https://ollama.ai
2. Pull the Qwen2.5:3b-instruct model

## Setup Steps

### 1. Install and Start Ollama

```bash
# Install Ollama (follow instructions at https://ollama.ai)
# On macOS:
brew install ollama

# Start Ollama service (usually runs automatically)
ollama serve
```

### 2. Pull Qwen2.5:3b-instruct Model

```bash
ollama pull qwen2.5:3b-instruct
```

This will download the model (approximately 2.1 GB). The model is optimized for instruction following and structured outputs, making it ideal for budget document extraction.

### 3. Verify Model is Available

```bash
ollama list
```

You should see `qwen2.5:3b-instruct` in the list.

### 4. Configure the Application

Create or update your `.env` file:

```bash
# LLM Provider Configuration
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b-instruct

# Optional: Force chat API (auto-detected by default for instruction models)
# OLLAMA_USE_CHAT_API=true
```

### 5. Test the Setup

You can test if Ollama is working:

```bash
curl http://localhost:11434/api/tags
```

Or test the model directly:

```bash
ollama run qwen2.5:3b-instruct "Extract budget items from: Revenue: 1000 EUR"
```

### 6. Start the Application

```bash
# With Docker Compose
docker-compose up -d

# Or locally
cd backend
uvicorn app.main:app --reload
```

## Why Qwen2.5:3b-instruct?

- **Small size**: Only ~2.1 GB, runs on most machines
- **Fast**: Processes requests quickly on local hardware
- **Instruction-tuned**: Optimized for following structured prompts
- **Good JSON output**: Better at generating valid JSON than base models
- **No API costs**: Runs completely locally
- **Privacy**: All data stays on your machine

## Performance Tips

1. **GPU Acceleration**: If you have a compatible GPU, Ollama will automatically use it for faster inference
2. **Model Size**: The 3b parameter model is a good balance. For faster processing, you could use smaller models, but accuracy may decrease
3. **Memory**: Ensure you have at least 4GB RAM available for the model

## Troubleshooting

### Model not found
```bash
# Re-pull the model
ollama pull qwen2.5:3b-instruct
```

### Ollama not responding
```bash
# Check if Ollama is running
ollama serve

# Check logs
ollama list
```

### Connection refused
- Ensure Ollama is running: `ollama serve`
- Check the base URL matches: `http://localhost:11434`
- If using Docker, ensure Ollama is accessible from the container

### Slow performance
- Check if GPU is being used (Ollama logs will show)
- Consider using a smaller model variant
- Ensure sufficient RAM is available

## Alternative Models

If Qwen2.5:3b-instruct doesn't work well for your use case, try:

```bash
# Smaller and faster
ollama pull phi

# Larger and more capable
ollama pull qwen2.5:7b-instruct

# Different architecture
ollama pull mistral
```

Then update `OLLAMA_MODEL` in your `.env` file.

