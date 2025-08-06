# SMOOTH - Smart Mapping Operations Tool Hub

A comprehensive geospatial analysis and mapping platform built with Streamlit and FastAPI.

## Features

- **Campaign Preparation**: Generate geohash grids, plan coverage, and forecast budgets
- **Campaign Evaluation**: Compare plan vs actual results, analyze gaps, and find root causes
- **Tools Add-On**: File conversion, boundary to geohash conversion, and data format tools
- **Geospatial Analysis**: POI density analysis, road network analysis, and complete workflow automation
- **PostgreSQL Integration**: Data storage with PostGIS extension for geospatial operations

## Architecture

- **Frontend**: Streamlit application for interactive user interface
- **Backend**: FastAPI for RESTful API services
- **Database**: PostgreSQL with PostGIS extension for geospatial data
- **Containerization**: Docker and Docker Compose for easy deployment

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed on your system
- Git (to clone the repository)

### Running the Project

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd karta-tools
   ```

2. **Set up environment variables** (optional):
   ```bash
   cp .env.example .env
   # Edit .env file with your desired configuration
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

   This will start:
   - PostgreSQL database with PostGIS (port 5432)
   - FastAPI backend (port 8000)
   - Streamlit frontend (port 8501)

4. **Access the applications**:
   - **Streamlit App**: http://localhost:8501
   - **API Documentation**: http://localhost:8000/docs
   - **API Health Check**: http://localhost:8000/health

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Database Configuration
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=postgres
DATABASE_USER=postgres
DATABASE_PASSWORD=Nuril123!

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# Streamlit Configuration
STREAMLIT_PORT=8501

# OpenAI API Key for Chatbot (optional)
OPENAI_API_KEY=your_openai_api_key_here
```

## Docker Commands

### Basic Operations

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f streamlit
docker-compose logs -f api
docker-compose logs -f postgres

# Rebuild and restart services
docker-compose up -d --build

# Stop and remove all containers, networks, and volumes
docker-compose down -v
```

### Development Mode

For development with live code reloading:

```bash
# Start with volume mounts for live reloading
docker-compose up -d

# The docker-compose.yml already includes volume mounts for development
```

### Production Deployment

For production deployment, consider:

1. **Remove volume mounts** from docker-compose.yml
2. **Set environment variables** properly
3. **Use environment-specific configurations**
4. **Set up reverse proxy** (nginx) for HTTPS
5. **Configure proper logging** and monitoring

## Manual Installation (Development)

If you prefer to run without Docker:

### Prerequisites

- Python 3.11+
- PostgreSQL with PostGIS extension
- GDAL libraries

### Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL** with PostGIS extension

3. **Configure environment variables** in `.env` file

4. **Run the API**:
   ```bash
   python run_api.py
   ```

5. **Run Streamlit** (in another terminal):
   ```bash
   streamlit run Home.py
   ```

## Project Structure

```
karta-tools/
├── api/                    # FastAPI backend
│   ├── database/          # Database connection and models
│   ├── models/            # SQLAlchemy models
│   ├── routers/           # API endpoints
│   └── schemas/           # Pydantic schemas
├── pages/                 # Streamlit pages
├── cache/                 # Cache directory
├── config.py              # Configuration settings
├── main.py                # FastAPI main application
├── Home.py                # Streamlit main page
├── requirements.txt       # Python dependencies
├── Dockerfile.api         # Docker configuration for API
├── Dockerfile.streamlit   # Docker configuration for Streamlit
├── docker-compose.yml     # Docker Compose configuration
└── README.md              # This file
```

## API Documentation

The FastAPI backend provides a comprehensive API with automatic documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details
