# Quotebot AI Proxy

Production-ready FastAPI backend for seamless Dify integration with Quotebot.

## 🚀 Quick Start

### 1. Setup
```bash
cd quotebot-ai-proxy
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env with your Dify API key
```

### 3. Start Redis
```bash
redis-server
```

### 4. Run
```bash
python main.py
```

### 5. Access
- API Docs: http://localhost:8000/api/v1/docs
- Health: http://localhost:8000/api/v1/health

## 📚 API Endpoints

### POST /api/v1/chat
Send a chat message

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "Hello!",
    "user": "user-123"
  }'
```

### GET /api/v1/history/{conversation_id}
Get conversation history

```bash
curl http://localhost:8000/api/v1/history/conv-123?user=user-123 \
  -H "X-API-Key: your-api-key"
```

### DELETE /api/v1/conversation/{conversation_id}
Delete conversation

```bash
curl -X DELETE http://localhost:8000/api/v1/conversation/conv-123?user=user-123 \
  -H "X-API-Key: your-api-key"
```

## 🔒 Security

- API key authentication
- Rate limiting (60/min, 1000/hour)
- CORS protection
- Input validation

## 📊 Monitoring

Health check: `curl http://localhost:8000/api/v1/health`

## 🐛 Troubleshooting

### Redis connection error
```bash
redis-cli ping  # Should return PONG
```

### Port in use
```bash
lsof -i :8000  # Find process
kill -9 <PID>  # Kill process
```