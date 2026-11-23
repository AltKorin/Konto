FROM node:22-slim AS front
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_DEBUG=0
WORKDIR /app
COPY requirements.txt ./
COPY vendor/ ./vendor/
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=front /app/frontend/dist ./frontend/dist
RUN DJANGO_DEBUG=1 DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput \
    && useradd -u 1000 -m app && mkdir -p /data && chown app /data
USER app
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py createcachetable && python manage.py wczytaj_produkty && gunicorn config.wsgi -b 0.0.0.0:8000 -w 2 --access-logfile -"]
