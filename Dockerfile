# © COPYRIGHT TO https://github.com/GouthamSER
# Base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot code
COPY . .

# Set environment variables (optional defaults)
# You can override them on Koyeb deployment
ENV API_ID=0
ENV API_HASH=your_api_hash
ENV BOT_TOKEN=your_bot_token

# Start the bot
CMD ["python", "main.py"]


