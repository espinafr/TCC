FROM node:18-alpine AS assets
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --silent
COPY app/public ./app/public
RUN npm run build:css

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt --no-cache-dir

# Copy compiled CSS from build stage
COPY --from=assets /app/app/public/tailwindoutput.css ./app/public/tailwindoutput.css
COPY . .

EXPOSE 5000

USER nobody
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:create_app()"]