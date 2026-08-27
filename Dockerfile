FROM python:3.11-slim

# ============================================================
# SYSTEM DEPENDENCIES
# ============================================================
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    xvfb \
    wget \
    curl \
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
    libglib2.0-0 \
    libxrender1 \
    libxcb1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# ENVIRONMENT
# ============================================================
ENV DISPLAY=:99
ENV NODE_ENV=production
ENV NODE_OPTIONS=--max-old-space-size=1024
ENV NODE_OPTIONS="--max-old-space-size=3072"

WORKDIR /app

# ============================================================
# PYTHON DEPENDENCIES
# ============================================================
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# REMOTION PROJECT
# ============================================================
COPY remotion-project/package*.json ./remotion-project/

WORKDIR /app/remotion-project

RUN npm install

# Make sure Remotion has its own compatible browser
RUN npx remotion browser ensure

# Install Playwright package if required by the project
RUN npm install playwright

WORKDIR /app

# ============================================================
# COPY BACKEND
# ============================================================
COPY . .

# ============================================================
# CREATE REMOTION BROWSER LINK
# ============================================================
RUN BROWSER_PATH=$(find /app/remotion-project/node_modules/.remotion \
    -type f \
    -name "chrome-headless-shell" \
    | head -n 1) \
    && echo "Remotion browser: $BROWSER_PATH" \
    && test -n "$BROWSER_PATH" \
    && chmod +x "$BROWSER_PATH" \
    && ln -sf "$BROWSER_PATH" /usr/local/bin/remotion-chromium

# ============================================================
# PORT
# ============================================================
EXPOSE 8080

# ============================================================
# START SERVER
# ============================================================
CMD sh -c '\
    Xvfb :99 -screen 0 1920x1080x24 -ac >/tmp/xvfb.log 2>&1 & \
    sleep 3 && \
    echo "DISPLAY=$DISPLAY" && \
    echo "Remotion browser:" && \
    readlink -f /usr/local/bin/remotion-chromium && \
    /usr/local/bin/remotion-chromium \
        --version >/tmp/chromium-version.txt 2>&1 || true && \
    cat /tmp/chromium-version.txt 2>/dev/null || true && \
    uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} \
'