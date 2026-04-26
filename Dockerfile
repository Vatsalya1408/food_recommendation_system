FROM python:3.10-slim

# Install tesseract
RUN apt-get update && apt-get install -y tesseract-ocr

# Set working dir
WORKDIR /app

# Copy files
COPY . .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run app
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080"]
