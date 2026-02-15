# Troskovljnjikov - Excel Data Analysis and Visualization Platform

## Project Overview

Troskovljnjikov is a comprehensive Excel data analysis platform designed for processing Bill of Quantities (BoQ) and construction cost estimation spreadsheets. The project combines AI-powered text processing with advanced Excel analysis capabilities to provide insights into construction cost data.

The main components include:
- A multi-agent text reconstruction system (in main.py)
- A comprehensive Excel file analyzer (analyze_xlsx.py) 
- A Streamlit-based web interface for data visualization
- A collection of Excel files related to construction cost estimates

## Technologies Used

- **Python 3.11+**: Core programming language
- **Streamlit**: Web interface framework
- **Pydantic-AI**: AI agent framework
- **OpenPyXL**: Excel file processing
- **Pandas**: Data manipulation and analysis
- **Plotly**: Interactive visualizations
- **Logfire**: Application logging and monitoring

## Key Components

### 1. Multi-Agent Text Processing System (`main.py`)
- Implements a multi-agent architecture for text reconstruction
- Uses deterministic agents for anchor detection and comparison
- Integrates with local LLM (Llama3) via Pydantic-AI
- Provides a Streamlit UI for text processing tasks

### 2. Excel Analysis Engine (`analyze_xlsx.py`)
- Comprehensive analyzer for BoQ (Bill of Quantities) Excel files
- Automatically detects headers, sheet structures, and data patterns
- Classifies different Excel file formats based on structural characteristics
- Identifies merged cells, formulas, and formatting patterns
- Processes files in the `/vanjski-podaci/primjeri-excel-ponuda/` directory

### 3. Excel Data Directory
Contains numerous Excel files related to construction cost estimates, primarily in Croatian language, including:
- Cost estimation templates
- Construction material pricing
- Various BoQ formats from different contractors
- Files with names containing terms like "troskovnik", "ponuda", "offer"

## Building and Running

### Prerequisites
- Python 3.11+
- Access to Llama3 model file (models/llama3.gguf)
- Local LLM server binary (bin/llama-server)

### Setup Instructions
1. Install dependencies using uv:
   ```bash
   uv sync
   ```

2. Run the application using the provided script:
   ```bash
   ./run.sh
   ```
   
   This script:
   - Starts the llama-server with the Llama3 model
   - Launches the Streamlit UI
   - Handles cleanup on exit

### Manual Startup
Alternatively, you can run components separately:
```bash
# Start the LLM server
./bin/llama-server -m ./models/llama3.gguf -ngl 99 --parallel 4 --cont-batching --cache-reuse 512 --chat-template chatml &

# Run the Streamlit app
uv run streamlit run main.py
```

## Development Conventions

- Code follows Python PEP 8 style guidelines
- Dependencies managed through pyproject.toml
- Logging implemented with Logfire for debugging and monitoring
- Configuration stored in structured formats (pyproject.toml)

## Excel Analysis Capabilities

The Excel analyzer provides detailed insights including:
- Sheet structure detection
- Header identification and scoring
- Column pattern classification (Roman numerals, hierarchical numbers, etc.)
- Formula detection
- Merged cell identification
- Row height analysis
- Format family classification

## File Organization

- `main.py`: Primary application entry point with multi-agent system
- `analyze_xlsx.py`: Excel analysis engine
- `pyproject.toml`: Project dependencies and metadata
- `run.sh`: Application launcher script
- `vanjski-podaci/primjeri-excel-ponuda/`: Sample Excel files for analysis
- `models/`: Machine learning model files
- `bin/`: Executable binaries (llama-server)
- `components/`: Reusable UI components
- `docs/`: Documentation files

## Qwen Added Memories
- User's operating system is Linux (ubuntu)
