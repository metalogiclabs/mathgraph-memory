FROM python:3.12-slim
WORKDIR /service
COPY *.py ./
ENV PORT=8080 MEMORY_DB=/data/memory.sqlite3 MEMORY_RANKER=indexed
VOLUME /data
EXPOSE 8080
CMD ["python", "app.py"]
