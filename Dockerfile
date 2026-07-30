FROM python:3.11-slim

# Install Chromium + dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-common \
    chromium-sandbox \
    xvfb \
    nodejs \
    npm \
    wget \
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

# Browser environment
ENV DISPLAY=:99
ENV CHROME_BIN=/usr/bin/chromium
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV REMOTION_BROWSER_EXECUTABLE=/usr/bin/chromium

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY remotion-project/package*.json ./remotion-project/

WORKDIR /app/remotion-project

# Install Remotion dependencies
RUN npm install

WORKDIR /app

COPY . .

EXPOSE 8000

CMD sh -c "Xvfb :99 -screen 0 1920x1080x24 & uvicorn main:app --host 0.0.0.0 --port 8000"