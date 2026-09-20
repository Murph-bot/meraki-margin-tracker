FROM node:20-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend ./backend
COPY --from=frontend /frontend/dist ./frontend/dist
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
