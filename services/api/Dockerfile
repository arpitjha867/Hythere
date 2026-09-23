FROM python:3.12-slim
WORKDIR /app
COPY services/api/requirements.txt services/api/requirements.txt
COPY services/agent/requirements.txt services/agent/requirements.txt
RUN pip install --no-cache-dir -r services/api/requirements.txt -r services/agent/requirements.txt
COPY services/api/src services/api/src
COPY services/agent/src services/agent/src
ENV PYTHONPATH=/app/services/api/src:/app/services/agent/src
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "hythere_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
