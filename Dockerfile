FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY bin/ ./bin/
COPY sounds/ ./sounds/
COPY .env .
COPY main.py .
COPY memes.ogg .

CMD ["python", "main.py"]