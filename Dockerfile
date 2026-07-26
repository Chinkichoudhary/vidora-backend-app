FROM python:3.11-slim

# Install Node.js, Chromium and required libraries
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
    xdg-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Tell Remotion where Chromium is installed
ENV CHROME_BIN=/usr/bin/chromium
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV REMOTION_BROWSER_EXECUTABLE=/usr/bin/chromium

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY remotion-project/package*.json ./remotion-project/
RUN cd remotion-project && npm install

COPY . .

EXPOSE 8000

CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]