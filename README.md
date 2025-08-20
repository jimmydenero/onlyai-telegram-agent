# OnlyAI Telegram Agent

An AI-powered Telegram bot for OnlyAi course Q&A with knowledge base retrieval, group monitoring, and daily digest generation.

## Features

- **Q&A System**: Answer questions about OnlyAi course and AI-OFM strategies using retrieved context
- **Knowledge Base**: Upload and process documents (PDF, DOCX, TXT, MD) with automatic chunking and embedding
- **Hybrid Search**: Combine BM25 full-text search with vector similarity search for better results
- **Smart Chat Monitoring**: AI-powered message classification (Information, Question, Answer, Joke, Useless)
- **Group Monitoring**: Monitor group messages and generate daily digests
- **Chat History Integration**: Use previous Q&A from group chats to answer similar questions
- **Whitelist System**: Control access with user whitelisting
- **Admin Dashboard**: Web interface for document management and system administration
- **Scheduled Tasks**: Automatic nightly digest generation and message cleanup

## Tech Stack

- **Language**: Python 3.11
- **Bot Framework**: aiogram (Telegram webhook)
- **API**: FastAPI
- **Database**: PostgreSQL + pgvector
- **Storage**: Local filesystem (dev) / Railway volume (prod)
- **AI/LLM**: OpenAI GPT-4o + text-embedding-3-large
- **Scheduler**: APScheduler for nightly tasks

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database with pgvector extension
- OpenAI API key
- Telegram bot token

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd onlyai-telegram-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_MODEL=gpt-4o
   EMBED_MODEL=text-embedding-3-large
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_WEBHOOK_BASE=https://your-domain.com
   OWNER_TELEGRAM_ID=5822224802
   ADMIN_TOKEN=your_long_random_admin_token
   DATABASE_URL=postgresql://user:password@localhost:5432/onlyai_agent
   PGVECTOR_ENABLED=true
   FILE_STORAGE_DIR=./data
   LOG_LEVEL=info
   ```

4. **Set up database**
   ```sql
   -- Enable pgvector extension
   CREATE EXTENSION IF NOT EXISTS vector;
   
   -- Run the schema from app/db/models.sql
   ```

5. **Run the application**
   ```bash
   python -m app.main
   ```

6. **Set webhook** (after starting the app)
   ```bash
   curl -X POST "http://localhost:8000/webhook/set" \
     -H "Authorization: Bearer your_admin_token"
   ```

## Bot Commands

### Monitoring Commands
- `/monitor` - Start/stop chat monitoring in the current group
- `/groups` - Show which groups are currently being monitored
- `/stats` - Display monitoring statistics and message classifications

### General Commands
- `/test` - Test bot connectivity and permissions
- `/help` - Show available commands

### Admin Commands
- `/knowledge` - Show knowledge base status (admin only)

## Chat Monitoring Features

The bot includes intelligent message classification:

- **Information**: Useful facts, tips, strategies, educational content
- **Question**: Asks for help, advice, clarification, or information  
- **Answer**: Responds to someone else's question or provides help
- **Joke**: Humor, memes, funny comments, entertainment
- **Useless**: Spam, random characters, or content with no value

Only Information, Question, and Answer messages are stored for future reference. When answering questions, the bot will reference previous group discussions and add a warning if the answer wasn't from Jimmy.

### Railway Deployment

1. **Create Railway account and project**

2. **Add PostgreSQL service**
   - Create a new PostgreSQL service
   - Enable pgvector extension in the database

3. **Deploy the application**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login and deploy
   railway login
   railway link
   railway up
   ```

4. **Set environment variables in Railway dashboard**
   - Add all required environment variables
   - Set `TELEGRAM_WEBHOOK_BASE` to your Railway app URL

5. **Set webhook**
   ```bash
   curl -X POST "https://your-railway-app.railway.app/webhook/set" \
     -H "Authorization: Bearer your_admin_token"
   ```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `OPENAI_MODEL` | OpenAI model for chat | No | `gpt-5.0-thinking` |
| `EMBED_MODEL` | OpenAI model for embeddings | No | `text-embedding-3-large` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes | - |
| `TELEGRAM_WEBHOOK_BASE` | Base URL for webhook | Yes | - |
| `OWNER_TELEGRAM_ID` | Owner's Telegram user ID | No | `5822224802` |
| `ADMIN_TOKEN` | Admin authentication token | Yes | - |
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `PGVECTOR_ENABLED` | Enable pgvector extension | No | `true` |
| `FILE_STORAGE_DIR` | File storage directory | No | `./data` |
| `LOG_LEVEL` | Logging level | No | `info` |

## API Endpoints

### Public Endpoints
- `GET /` - Root endpoint
- `GET /health` - Health check

### Admin Endpoints (require Bearer token)
- `GET /admin/` - Admin dashboard
- `POST /admin/upload` - Upload document
- `GET /admin/documents` - List documents
- `POST /admin/whitelist` - Add user to whitelist
- `DELETE /admin/whitelist/{user_id}` - Remove user from whitelist
- `GET /admin/whitelist` - Get whitelist
- `POST /admin/digest/generate` - Generate daily digest
- `POST /admin/reindex` - Reindex all documents
- `POST /admin/cleanup` - Cleanup old messages
- `GET /admin/stats` - System statistics
- `POST /admin/test-answer` - Test answer generation

### Webhook Endpoints
- `POST /webhook/set` - Set Telegram webhook
- `POST /webhook/remove` - Remove Telegram webhook
- `GET /webhook/info` - Get webhook information
- `GET /bot/info` - Get bot information

## Telegram Bot Commands

- `/test` - Test bot connectivity and permissions

## Database Schema

The application uses the following main tables:

- `users` - User information and roles
- `whitelist` - Whitelisted users
- `messages` - Group messages for digest generation
- `docs` - Document metadata
- `doc_chunks` - Document chunks with embeddings
- `chat_digests` - Daily digests with embeddings
- `qa_logs` - Q&A interaction logs

## Development

### Project Structure
```
app/
├── main.py              # FastAPI application
├── bot.py               # Telegram bot handlers
├── config.py            # Configuration settings
├── security.py          # Authentication and permissions
├── db/
│   ├── models.sql       # Database schema
│   └── repo.py          # Database operations
├── handlers/
│   ├── qa.py            # Q&A processing
│   └── admin.py         # Admin endpoints
├── retrieval/
│   ├── chunker.py       # Text chunking
│   ├── embed.py         # Embedding management
│   └── retrieve.py      # Search and retrieval
├── ingest/
│   ├── uploader.py      # Document upload processing
│   └── group_digest.py  # Daily digest generation
├── llm/
│   └── client.py        # OpenAI client wrapper
├── utils/
│   └── text.py          # Text processing utilities
└── prompts/
    ├── system.txt       # System prompt
    └── answer_template.txt # Answer template
```

### Running Tests
```bash
# Run health check
curl http://localhost:8000/health

# Test admin endpoints
curl -X POST "http://localhost:8000/admin/test-answer" \
  -H "Authorization: Bearer your_admin_token" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AI-OFM?"}'
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure PostgreSQL is running
   - Check `DATABASE_URL` format
   - Verify pgvector extension is installed

2. **OpenAI API Error**
   - Verify `OPENAI_API_KEY` is correct
   - Check API quota and billing

3. **Webhook Issues**
   - Ensure `TELEGRAM_WEBHOOK_BASE` is accessible
   - Check bot token validity
   - Verify webhook URL is HTTPS

4. **File Upload Errors**
   - Check file permissions in `FILE_STORAGE_DIR`
   - Ensure supported file formats (PDF, DOCX, TXT, MD)

### Logs
- Application logs are available in Railway dashboard
- Set `LOG_LEVEL=debug` for detailed logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
