FROM python:3.12.7-slim
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY . .
RUN mkdir -p /app/data
EXPOSE 8000
# Tables are created on startup in app/__init__.py (Base.metadata.create_all).
# DATABASE_URL and other config come from compose/env — not baked into the image.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
