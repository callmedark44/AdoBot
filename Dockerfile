FROM python:3.12-slim

WORKDIR /app

# Install ca-certificates for HTTPS out of the box (needed by yande/danbooru/etc.)
RUN apt-get update -qq && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*

# Install deps first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# runtime.txt pins python-3.12; we already use the 3.12 image above.
EXPOSE 8080

# bot.py reads PORT from env (Railway sets it)
CMD ["python", "bot.py"]
