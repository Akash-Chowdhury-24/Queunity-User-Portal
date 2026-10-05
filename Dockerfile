FROM python:3.11-slim AS build
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN prisma generate

FROM python:3.11-slim
WORKDIR /app

# libatomic1 is also needed at RUNTIME — the query engine binary depends on it too
RUN apt-get update && apt-get install -y --no-install-recommends libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /root/.cache/prisma-python /root/.cache/prisma-python
COPY . .
EXPOSE 8002
CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8002"]