FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DB_PATH=/data/jira.db
ENV UPLOAD_DIR=/data/uploads

EXPOSE 5050

CMD ["python", "app.py"]
