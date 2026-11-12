FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY app/requirements.txt /srv/requirements.txt
RUN pip install -r /srv/requirements.txt
COPY app /srv/app
COPY docs /srv/docs
ENV ZOCALO_DATA_DIR=/data ZOCALO_DATASETS_DIR=/datasets ZOCALO_DOCS_DIR=/srv/docs ZOCALO_IN_DOCKER=1 PYTHONPATH=/srv/app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "zocalo.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
