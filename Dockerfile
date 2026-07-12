FROM python:3.12-slim
WORKDIR /app
# src-layout: pip build needs the source present, so copy first, then install
# runtime deps only (no dev/test extras). .dockerignore keeps tests/venv out.
COPY . .
RUN pip install --no-cache-dir .
ENV PYTHONPATH=/app/src
CMD ["uvicorn", "sfplatform.app:app", "--host", "0.0.0.0", "--port", "8000"]
