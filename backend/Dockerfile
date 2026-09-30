FROM python:3.13-slim
RUN adduser --disabled-password --no-create-home appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY data/ data/
RUN chown -R appuser:appuser /app
EXPOSE 8000
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
