# 🍌 Nanobanana MCP Server

> **Gemini 2.5 Flash Image MCP Server for Claude Code**

A Model Context Protocol (MCP) server that brings Google's powerful Gemini 2.5 Flash Image generation capabilities directly to Claude Code. Generate, edit, and blend images using natural language through Claude's intelligent interface.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://github.com/modelcontextprotocol/specification)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

## ✨ Features

### 🎨 **Text-to-Image Generation**
- Generate high-quality images from text prompts
- Multiple aspect ratios (1:1, 16:9, 9:16, etc.)
- Style control (photorealistic, digital-art, etc.)
- Batch generation (up to 4 images)
- Intelligent prompt optimization

### ✏️ **Image Editing**
- Edit existing images with natural language
- Selective editing with mask support
- Background replacement
- Style transfer and modifications
- Preserve or modify specific elements

### 🎭 **Image Blending**
- Combine multiple images (2-4 sources)
- Create artistic compositions
- Maintain character consistency
- Surreal and creative blending
- Style harmonization

### 📊 **Server Management**
- Real-time API status monitoring
- Usage statistics and cost tracking
- Performance metrics
- Health checks and diagnostics
- Automatic error recovery

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/your-username/nanobanana_mcp.git
cd nanobanana_mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your Google AI API key
GOOGLE_AI_API_KEY=your_api_key_here
```

### 3. Claude Desktop Integration

Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  \"mcpServers\": {
    \"nanobanana\": {
      \"command\": \"python\",
      \"args\": [\"-m\", \"src.server\"],
      \"cwd\": \"/path/to/nanobanana_mcp\",
      \"env\": {
        \"GEMINI_API_KEY\": \"YOUR_API_KEY_HERE\",
        \"GOOGLE_API_KEY\": \"YOUR_API_KEY_HERE\",
        \"GOOGLE_AI_API_KEY\": \"YOUR_API_KEY_HERE\"
      }
    }
  }
}
```

### 4. Start Using

```bash
# Test the server
python -m src.server --check-health

# Run basic usage example
python examples/basic_usage.py
```

## 📖 Usage Guide

### Basic Image Generation

Ask Claude Code:
```
\"나노바나나를 사용해서 고양이가 모자를 쓰고 있는 사진을 생성해줘\"
```

Claude will use:
```python
nanobanana_generate(
    prompt=\"A cat wearing a hat, photorealistic style\",
    aspect_ratio=\"1:1\",
    quality=\"high\"
)
```

### Image Editing

Ask Claude Code:
```
\"이 이미지의 배경을 바다로 바꿔줘\"
```

Claude will use:
```python
nanobanana_edit(
    image_path=\"./image.png\",
    edit_prompt=\"Change the background to ocean view\"
)
```

### Image Blending

Ask Claude Code:
```
\"이 두 이미지를 합성해서 환상적인 풍경을 만들어줘\"
```

Claude will use:
```python
nanobanana_blend(
    image_paths=[\"./mountain.png\", \"./castle.png\"],
    blend_prompt=\"Create a fantasy landscape combining both images\"
)
```

## 🛠️ API Reference

### `nanobanana_generate`

Generate images from text prompts using Gemini 2.5 Flash Image.

**Parameters:**
- `prompt` (str, required): Text description of the image to generate
- `aspect_ratio` (str, optional): Image aspect ratio (\"1:1\", \"16:9\", \"9:16\")
- `style` (str, optional): Generation style (\"photorealistic\", \"digital-art\", etc.)
- `quality` (str, optional): Image quality (\"auto\", \"high\", \"medium\", \"low\")
- `output_format` (str, optional): Output format (\"png\", \"jpeg\", \"webp\")
- `candidate_count` (int, optional): Number of images to generate (1-4)
- `additional_keywords` (List[str], optional): Extra keywords for enhancement
- `optimize_prompt` (bool, optional): Enable automatic prompt optimization

**Returns:**
```json
{
  \"success\": true,
  \"images\": [
    {
      \"filepath\": \"./outputs/generated_20240101_120000.png\",
      \"filename\": \"generated_20240101_120000.png\",
      \"size\": [1024, 1024],
      \"format\": \"PNG\",
      \"file_size\": 2048576,
      \"hash\": \"abc123def456\"
    }
  ],
  \"metadata\": {
    \"request_id\": \"req_123\",
    \"generation_time\": 3.2,
    \"cost_usd\": 0.039,
    \"optimized_prompt\": \"Enhanced prompt text\"
  }
}
```

### `nanobanana_edit`

Edit existing images with natural language instructions.

**Parameters:**
- `image_path` (str, required): Path to the image file to edit
- `edit_prompt` (str, required): Natural language editing instructions
- `mask_path` (str, optional): Path to mask image for selective editing
- `output_format` (str, optional): Output format (\"png\", \"jpeg\", \"webp\")
- `quality` (str, optional): Output quality
- `optimize_prompt` (bool, optional): Enable prompt optimization

**Returns:**
```json
{
  \"success\": true,
  \"edited_image\": {
    \"filepath\": \"./outputs/edited_20240101_120000.png\",
    \"original_path\": \"./inputs/original.png\",
    \"edit_applied\": \"Changed background to ocean view\",
    \"size\": [1024, 1024]
  },
  \"metadata\": {
    \"editing_time\": 2.8,
    \"cost_usd\": 0.039
  }
}
```

### `nanobanana_blend`

Blend multiple images into a new composition.

**Parameters:**
- `image_paths` (List[str], required): List of 2-4 image paths to blend
- `blend_prompt` (str, required): Instructions for how to blend the images
- `maintain_consistency` (bool, optional): Maintain character/style consistency
- `output_format` (str, optional): Output format
- `quality` (str, optional): Output quality
- `optimize_prompt` (bool, optional): Enable prompt optimization

**Returns:**
```json
{
  \"success\": true,
  \"blended_image\": {
    \"filepath\": \"./outputs/blended_20240101_120000.png\",
    \"blend_description\": \"Fantasy landscape with castle on mountain\",
    \"source_count\": 2
  },
  \"source_images\": [
    {\"path\": \"./img1.png\", \"contribution\": 0.6},
    {\"path\": \"./img2.png\", \"contribution\": 0.4}
  ],
  \"metadata\": {
    \"blend_time\": 4.1,
    \"complexity_score\": 7.2
  }
}
```

### `nanobanana_status`

Check server status and API connectivity.

**Parameters:**
- `detailed` (bool, optional): Include detailed system information
- `include_history` (bool, optional): Include recent operation history
- `reset_stats` (bool, optional): Reset performance statistics

**Returns:**
```json
{
  \"success\": true,
  \"server_name\": \"nanobanana\",
  \"version\": \"1.0.0\",
  \"status\": \"healthy\",
  \"uptime_seconds\": 3600,
  \"api_status\": {
    \"status\": \"healthy\",
    \"model\": \"gemini-2.5-flash-image-preview\",
    \"api_accessible\": true,
    \"last_check\": \"2024-01-01T12:00:00\"
  },
  \"performance_stats\": {
    \"total_requests\": 25,
    \"total_images_generated\": 30,
    \"total_cost_usd\": 1.17,
    \"average_response_time\": 3.2,
    \"success_rate\": 0.96
  }
}
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
GOOGLE_AI_API_KEY=your_google_ai_api_key

# Optional - Directories
NANOBANANA_OUTPUT_DIR=./outputs
NANOBANANA_TEMP_DIR=./temp
NANOBANANA_CACHE_DIR=./cache

# Optional - Image Settings
NANOBANANA_MAX_IMAGE_SIZE=10          # Max image size in MB
NANOBANANA_DEFAULT_QUALITY=high       # Default image quality
NANOBANANA_DEFAULT_FORMAT=png         # Default output format

# Optional - Behavior
NANOBANANA_OPTIMIZE_PROMPTS=true      # Enable prompt optimization
NANOBANANA_AUTO_TRANSLATE=true        # Auto-translate Korean to English
NANOBANANA_SAFETY_LEVEL=moderate      # Content safety level

# Optional - Performance
NANOBANANA_ENABLE_CACHE=true          # Enable result caching
NANOBANANA_CACHE_EXPIRY=24            # Cache expiry hours
NANOBANANA_MAX_CACHE_SIZE=1000        # Max cached items
NANOBANANA_MAX_CONCURRENT_REQUESTS=3  # Max concurrent API calls
NANOBANANA_REQUEST_TIMEOUT=300        # API timeout seconds

# Optional - Server
NANOBANANA_HOST=localhost             # Server host
NANOBANANA_PORT=8000                  # Server port
NANOBANANA_DEV_MODE=false             # Development mode
NANOBANANA_LOG_LEVEL=INFO             # Logging level
```

### Claude Desktop Configuration

#### Windows
File location: `%APPDATA%\\Claude\\claude_desktop_config.json`

#### macOS  
File location: `~/Library/Application Support/Claude/claude_desktop_config.json`

#### Linux
File location: `~/.config/Claude/claude_desktop_config.json`

## 📁 Project Structure

```
nanobanana_mcp/
├── src/
│   ├── server.py              # Main MCP server
│   ├── gemini_client.py       # Gemini API client
│   ├── config.py              # Configuration management
│   ├── constants.py           # Project constants
│   ├── tools/                 # MCP tools implementation
│   │   ├── generate.py        # Text-to-image generation
│   │   ├── edit.py            # Image editing
│   │   ├── blend.py           # Image blending
│   │   └── status.py          # Server status
│   ├── utils/                 # Utility modules
│   │   ├── image_handler.py   # Image processing
│   │   ├── prompt_optimizer.py # Prompt enhancement
│   │   └── file_manager.py    # File management
│   └── models/
│       └── schemas.py         # Pydantic models
├── tests/                     # Unit tests
├── examples/                  # Usage examples
├── outputs/                   # Generated images
├── logs/                      # Log files
├── requirements.txt           # Python dependencies
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test category
pytest -m \"not integration\"  # Unit tests only
pytest -m \"integration\"      # Integration tests only
```

### Development Mode

```bash
# Start server in development mode
python -m src.server --dev --debug

# Run with custom settings
python -m src.server --host 0.0.0.0 --port 8080

# Check API health
python -m src.server --check-health
```

### Code Quality

```bash
# Format code
black src/ tests/ examples/

# Lint code  
flake8 src/ tests/ examples/

# Type checking
mypy src/
```

## 🔍 Troubleshooting

### Common Issues

#### MCP Server Not Appearing in Claude

1. **Check Claude Desktop config location and syntax**
   ```bash
   # Validate JSON syntax
   python -c \"import json; json.load(open('claude_desktop_config.json'))\"
   ```

2. **Verify project path**
   - Use absolute paths in `cwd` field
   - Ensure Python is in system PATH

3. **Restart Claude Desktop completely**
   - Close all Claude windows
   - Quit Claude Desktop application
   - Restart

#### API Key Issues

1. **Verify API key format**
   ```bash
   # Test API key
   python -m src.server --check-health
   ```

2. **Check API quotas and billing**
   - Visit [Google AI Studio](https://makersuite.google.com/)
   - Verify API usage limits

#### Image Generation Failures

1. **Content Policy Violations**
   - Try rephrasing prompts
   - Use English prompts for better results
   - Avoid restricted content

2. **File Permission Issues**
   ```bash
   # Check output directory permissions
   ls -la outputs/
   chmod 755 outputs/
   ```

### Debug Commands

```bash
# Health check
python -m src.server --check-health

# Debug mode with verbose logging
NANOBANANA_LOG_LEVEL=DEBUG python -m src.server --dev

# Test basic functionality
python examples/basic_usage.py

# Reset statistics
python -m src.server --reset-stats
```

### Log Files

Logs are written to `./logs/nanobanana_mcp.log`:

```bash
# View recent logs
tail -f logs/nanobanana_mcp.log

# Search for errors
grep ERROR logs/nanobanana_mcp.log

# View startup logs
grep \"Starting\\|Started\" logs/nanobanana_mcp.log
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Set up development environment:
   ```bash
   pip install -r requirements-dev.txt
   pre-commit install
   ```
4. Make your changes
5. Run tests and ensure they pass
6. Submit a pull request

### Coding Standards

- Follow PEP 8 style guidelines
- Add type hints for all functions
- Write docstrings for public APIs
- Include unit tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google AI** for the Gemini 2.5 Flash Image API
- **Anthropic** for Claude and MCP specifications
- **FastMCP** for the excellent MCP server framework
- **Community** for feedback and contributions

## 📚 Additional Resources

- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs/models)
- [Model Context Protocol Specification](https://github.com/modelcontextprotocol/specification)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Google AI Studio](https://makersuite.google.com/)

## 🆕 Changelog

### v1.0.0 (2024-08-28)
- Initial release
- Text-to-image generation with Gemini 2.5 Flash
- Image editing capabilities
- Multi-image blending
- Server status monitoring
- Complete Claude Code integration
- Comprehensive test suite
- Usage examples and documentation

---

