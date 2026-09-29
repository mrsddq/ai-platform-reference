FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/app \
    XDG_CACHE_HOME=/home/app/.cache

WORKDIR /app
COPY . .
RUN pip install . && useradd --uid 10001 --user-group --create-home app \
    && install -d -o app -g app /home/app/.cache

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "platform_app.api:app", "--host", "0.0.0.0", "--port", "8000"]
