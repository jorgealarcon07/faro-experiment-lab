FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY . .
RUN pip install --no-build-isolation --no-deps . && useradd -m faro && mkdir -p local && chown -R faro:faro local
USER faro
ENTRYPOINT ["faro-exp"]
CMD ["demo"]
