# Blog Platform API

A modern, scalable blog platform API built with FastAPI, featuring role-based access control, caching, and comprehensive test coverage.

## Features

- 🔐 **Authentication & Authorization**
  - JWT-based authentication
  - Role-based access control (Admin, Author, Reader)
  - Token blacklisting for secure logout

- 📝 **Blog Post Management**
  - CRUD operations for posts
  - Tag support
  - Comment support
  - Redis-based caching for improved performance

- 🔍 **Search Option**
  - Full-text search
  - Filter by author, date, tags

## Prerequisites

- Docker and Docker Compose v3.8+
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/technophyl/blog-api.git
cd blog-api
```

2. Create and configure the environment file:
```bash
cp .env.example .env
```

Update the `.env` file with your configuration:
```env
DB_HOST=db_host
DB_PORT=db_port
DB_USER=bloguser
DB_PASSWORD=your_secure_password
DB_NAME=blogdb
SECRET_KEY=your_secure_secret_key
REDIS_HOST=redis_host
REDIS_PORT=redis_port
```

3. Start the application using Docker Compose:
```bash
docker-compose up --build -d
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, you can access:
- Swagger UI documentation: `http://localhost:8000/docs`
- ReDoc documentation: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`

## Authentication

The API uses JWT tokens for authentication. To obtain a token:

1. Register a new user:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass", "full_name": "John Doe"}'
```

2. Login to get an access token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=user@example.com&password=securepass"
```

3. Use the token in subsequent requests:
```bash
curl -X GET http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer your_access_token"
```

## Development Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
.\venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run tests:
```bash
pytest
```

3. Run Project:
```bash
uvicorn app.main:app --reload
```

## Project Structure

```
blog-api/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── api.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── permissions.py
│   ├── models/
│   ├── schemas/
│   └── main.py
├── tests/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Configuration

The application can be configured using environment variables or a `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| DB_HOST | PostgreSQL host | localhost or db(for docker)|
| DB_PORT | PostgreSQL port | 5432 |
| DB_USER | Database username | bloguser |
| DB_PASSWORD | Database password | blogpass |
| DB_NAME | Database name | blogdb |
| SECRET_KEY | JWT secret key | secret-key |
| REDIS_HOST | Redis host | localhost or redis(for docker)|
| REDIS_PORT | Redis port | 6379 |

## Testing

The project includes comprehensive test coverage:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api.py
```
