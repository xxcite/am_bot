FROM python:3
WORKDIR /usr/src/app

## install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD [ "python", "./watch_script.py" ]