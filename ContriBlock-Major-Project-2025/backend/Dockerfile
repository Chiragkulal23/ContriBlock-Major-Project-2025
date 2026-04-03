FROM python:3.11-slim
WORKDIR /app
COPY backend /app/backend
RUN pip install --no-cache-dir -r backend/requirements.txt
ENV FLASK_APP=backend/app.py
EXPOSE 5001
CMD ["python", "backend/app.py"]

