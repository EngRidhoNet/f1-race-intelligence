# F1 Race Intelligence Backend

A production-ready backend for an F1 race intelligence dashboard with data-aware chatbot powered by **open-source LLMs** (Llama, Mistral, Qwen).

## 🚀 Features

- **F1 Data Ingestion**: Automated import of race data using FastF1
- **REST API**: Comprehensive endpoints for races, telemetry, and analysis
- **WebSocket Replay**: Real-time race replay with car positions
- **AI Chatbot**: Natural language race analysis using **free/open LLMs**
  - Pluggable LLM architecture (Ollama, OpenAI-compatible APIs)
  - Data-aware responses based on actual race telemetry
  - Support for Llama, Mistral, Qwen, and other open models

## 🛠 Tech Stack

- **Framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL + SQLAlchemy 2.x + Alembic
- **F1 Data**: FastF1 + pandas
- **LLM**: Pluggable (Ollama / OpenAI-compatible)
- **Real-time**: WebSocket

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration
│   ├── db.py                   # Database session
│   ├── core/                   # Core utilities
│   │   ├── logging.py
│   │   ├── exceptions.py
│   │   └── deps.py
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── f1.py
│   │   └── telemetry.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── common.py
│   │   ├── f1.py
│   │   ├── telemetry.py
│   │   └── chat.py
│   ├── routers/                # API endpoints
│   │   ├── health.py
│   │   ├── races.py
│   │   ├── telemetry.py
│   │   ├── chat.py
│   │   └── realtime.py
│   └── services/               # Business logic
│       ├── f1_ingestion.py
│       ├── f1_queries.py
│       ├── replay_service.py
│       ├── chat_service.py
│       └── llm_client.py       # LLM abstraction
├── alembic/                    # Database migrations
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🔧 Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- (Optional) Ollama for local LLMs

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration
```

### 2. Database Setup

```bash
# Create PostgreSQL database
createdb f1_intelligence

# Update DATABASE_URL in .env
# DATABASE_URL=postgresql://user:password@localhost:5432/f1_intelligence

# Run migrations
alembic upgrade head
```

### 3. LLM Setup

#### Option A: Local Ollama (Recommended for Free Models)

```bash
# Install Ollama: https://ollama.ai
curl https://ollama.ai/install.sh | sh

# Pull a model (e.g., Llama 3)
ollama pull llama3

# Configure in .env
LLM_PROVIDER=ollama
LLM_API_BASE_URL=http://localhost:11434
LLM_MODEL_NAME=llama3
```

#### Option B: OpenAI-Compatible API

```bash
# For vLLM, OpenRouter, or other services
LLM_PROVIDER=openai_compatible
LLM_API_BASE_URL=https://api.openrouter.ai/v1
LLM_MODEL_NAME=meta-llama/llama-3-70b-instruct
LLM_API_KEY=your_api_key_here
```

### 4. Run Application

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📊 Data Ingestion

Ingest F1 race data from FastF1:

```bash
# Ingest a specific race
python -m app.services.f1_ingestion --year 2024 --round 1

# With debug logging
python -m app.services.f1_ingestion --year 2024 --round 5 --log-level DEBUG
```

**What gets ingested:**
- Season and race metadata
- Race results (classification)
- Lap-by-lap data
- Tyre stints
- Telemetry (position, speed, throttle, brake, gear)
- Track shape polyline

## 🌐 API Endpoints

### Health
- `GET /health` - Health check

### Seasons & Races
- `GET /seasons` - List all seasons
- `GET /seasons/{year}/races` - List races in a season
- `GET /races/{race_id}` - Get race details
- `GET /races/{race_id}/summary` - Get race summary
- `GET /races/{race_id}/results` - Get race results
- `GET /races/{race_id}/drivers` - Get race drivers

### Telemetry
- `GET /races/{race_id}/stints` - Get tyre stints
- `GET /races/{race_id}/laps?driver_code=VER` - Get lap data
- `GET /races/{race_id}/track-shape` - Get track polyline

### Chatbot
- `POST /races/{race_id}/chat` - Ask questions about the race

**Example Request:**
```json
{
  "question": "Why was Leclerc slower in the second stint?",
  "driver_codes": ["LEC", "VER"],
  "focus": "comparison",
  "lap_range": [20, 40]
}
```

**Example Response:**
```json
{
  "answer": "Leclerc's performance in the second stint was impacted by...",
  "used_context": {
    "race_id": 123,
    "drivers": ["LEC", "VER"],
    "lap_range": [20, 40],
    "short_stats": {...}
  }
}
```

### WebSocket Replay
- `WS /ws/races/{race_id}/replay` - Real-time race replay

**Example Usage:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/races/123/replay');

ws.onmessage = (event) => {
  const frame = JSON.parse(event.data);
  // frame.t: current time (seconds)
  // frame.cars: [{driver_code, x, y, speed_kph, lap}, ...]
  
  // Update track map visualization
  updateCarPositions(frame.cars);
};
```

## 🐳 Docker Deployment

### Using Docker Compose (Easiest)

```bash
# Start everything (database + backend)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run migrations
docker-compose exec backend alembic upgrade head

# Ingest data
docker-compose exec backend python -m app.services.f1_ingestion --year 2024 --round 1

# Stop
docker-compose down
```

### Using Dockerfile Only

```bash
# Build image
docker build -t f1-backend .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host/db \
  -e LLM_PROVIDER=ollama \
  -e LLM_API_BASE_URL=http://host.docker.internal:11434 \
  -e LLM_MODEL_NAME=llama3 \
  f1-backend
```

## 🤖 LLM Configuration Details

### Supported Providers

1. **Ollama** (`LLM_PROVIDER=ollama`)
   - Local deployment of open-source models
   - Free and private
   - Models: Llama 3, Mistral, Qwen, etc.
   - Endpoint: `http://localhost:11434/api/chat`

2. **OpenAI-Compatible** (`LLM_PROVIDER=openai_compatible`)
   - Works with any OpenAI-compatible API
   - Examples: vLLM, OpenRouter, Text Generation Inference
   - Supports authentication via `LLM_API_KEY`
   - Endpoint: `{LLM_API_BASE_URL}/v1/chat/completions`

### How It Works

The chatbot:
1. Receives a question about a race
2. Queries the database for relevant data (laps, stints, results)
3. Builds a structured JSON context with race statistics
4. Sends context + question to the LLM
5. Returns the LLM's natural language explanation

**Key Design**: The LLM sees ONLY actual race data. It cannot invent facts.

## 🧪 Testing

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

## 📈 Performance Tips

1. **Database Indexing**: Already optimized with indexes on frequently queried columns
2. **Telemetry Sampling**: Adjust `sample_rate` in ingestion (default: 10)
3. **Track Shape Decimation**: Adjust `decimate_factor` (default: 20)
4. **WebSocket FPS**: Configure `REPLAY_FPS` (default: 10)
5. **Connection Pooling**: Adjust `pool_size` in `db.py`

## 🔐 Security Considerations

- Use environment variables for sensitive config
- Enable CORS only for trusted origins
- Use PostgreSQL user with limited privileges
- Consider rate limiting for production (use nginx or similar)
- Keep LLM API keys secure (if using external services)

## 📝 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **FastF1**: For excellent F1 data API
- **FastAPI**: For modern Python web framework
- **Ollama**: For easy local LLM deployment
- **F1 Community**: For making this data accessible

## 🐛 Troubleshooting

### FastF1 Cache Issues
```bash
# Clear cache
rm -rf fastf1_cache/*
```

### Database Connection Issues
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check connection string
psql $DATABASE_URL
```

### LLM Connection Issues
```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Test OpenAI-compatible
curl -X POST $LLM_API_BASE_URL/v1/chat/completions \
  -H "Authorization: Bearer $LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3","messages":[{"role":"user","content":"test"}]}'
```

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review API docs at /docs endpoint

---

**Built with ❤️ for F1 fans and data enthusiasts**