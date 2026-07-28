FROM python:3.11-slim

# -----------------------------
# Install Node.js, Chromium and dependencies
# -----------------------------
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    chromium \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    libxkbcommon0 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    wget \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Verify Chromium installation
# -----------------------------
RUN which chromium || which chromium-browser

# Give execute permission
RUN chmod +x /usr/bin/chromium || true
RUN chmod +x /usr/bin/chromium-browser || true

# -----------------------------
# Tell Remotion to use system Chromium
# -----------------------------
ENV CHROME_BIN=/usr/bin/chromium
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV REMOTION_BROWSER_EXECUTABLE=/usr/bin/chromium

# Prevent Puppeteer from downloading Chrome
ENV PUPPETEER_SKIP_DOWNLOAD=true

# Helpful in Docker
ENV DISPLAY=:99

# -----------------------------
# App
# -----------------------------
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Install Remotion dependencies
# -----------------------------
COPY remotion-project/package*.json ./remotion-project/
RUN cd remotion-project && npm install

# -----------------------------
# Copy project
# -----------------------------
COPY . .

EXPOSE 8000

CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]