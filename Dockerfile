FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 libatk1.0-0 \
    libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 libnspr4 libnss3 \
    libx11-xcb1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libxshmfence1 xdg-utils wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY remotion-project/package*.json ./remotion-project/
RUN cd remotion-project && npm install

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]