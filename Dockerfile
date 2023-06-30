FROM python:3
WORKDIR /usr/src/app
LABEL org.opencontainers.image.source=https://github.com/xxcite/am_bot

## install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD [ "python", "./watch_script.py" ]