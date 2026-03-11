FROM python:3.12-slim

WORKDIR /src

RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.30.0" \
    "httpx>=0.27.0" \
    "networkx>=3.2" \
    "pyyaml>=6.0" \
    "pydantic>=2.6.0" \
    "pydantic-settings>=2.1.0" \
    "prometheus-client>=0.20.0"

COPY app/ app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
