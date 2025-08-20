# Railway Deployment Setup Guide

## Required Environment Variables

You need to set these environment variables in your Railway project dashboard:

### 1. OpenAI Configuration
```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
EMBED_MODEL=text-embedding-3-large
```

### 2. Telegram Configuration
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_WEBHOOK_BASE=https://your-railway-app-url.railway.app
```

### 3. Database Configuration
```
DATABASE_URL=postgresql://username:password@host:port/database
```

### 4. Admin Configuration
```
ADMIN_TOKEN=your_secure_admin_token_here
OWNER_TELEGRAM_ID=your_telegram_user_id
```

## How to Set Environment Variables

1. Go to your Railway project dashboard
2. Click on your service
3. Go to the "Variables" tab
4. Add each environment variable above
5. Click "Deploy" to apply changes

## Getting Your Values

### OpenAI API Key
- Go to https://platform.openai.com/api-keys
- Create a new API key
- Copy the key (starts with `sk-`)

### Telegram Bot Token
- Message @BotFather on Telegram
- Create a new bot with `/newbot`
- Copy the token (starts with `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Database URL
- In Railway, add a PostgreSQL database service
- Copy the connection URL from the database service variables

### Admin Token
- Generate a secure random token (you can use a password generator)
- This will be used to access admin endpoints

### Railway App URL
- After deploying, Railway will give you a URL like `https://your-app-name.railway.app`
- Use this as your `TELEGRAM_WEBHOOK_BASE`

## After Setting Variables

1. Deploy your app in Railway
2. Set up the webhook by calling:
   ```bash
   curl -X POST "https://your-app-url.railway.app/webhook/set" \
     -H "Authorization: Bearer your_admin_token"
   ```
3. Test your bot by sending `/test` in Telegram

## Troubleshooting

If you see "Missing required environment variables" error:
1. Check that all variables are set in Railway dashboard
2. Make sure there are no extra spaces in the values
3. Redeploy the app after setting variables

If the bot doesn't respond:
1. Check the webhook is set correctly
2. Verify the bot token is correct
3. Check Railway logs for errors
