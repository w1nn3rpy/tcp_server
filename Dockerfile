FROM python:3.12-slim
WORKDIR /usr/src/app

COPY . .

CMD ["python", "main.py"]