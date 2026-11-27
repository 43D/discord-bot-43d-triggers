FROM python:3.12-slim

WORKDIR /app

RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app

RUN test -x /app/bin/bin/ffmpeg && test -e /app/bin/lib/libavdevice.so.62
ENV LD_LIBRARY_PATH=/app/bin/lib:${LD_LIBRARY_PATH}


CMD ["python", "main.py"]