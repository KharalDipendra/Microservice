FROM python:3.11-slim
WORKDIR /app
# Install dependencies first so this layer is cached when only code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5003
CMD ["python", "app.py"]
