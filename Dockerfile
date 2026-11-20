FROM python:3.10-slim

WORKDIR /app

# Install system dependencies if any are needed for numpy/scipy/etc
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8509

CMD ["streamlit", "run", "dashboard/kpi_dashboard.py", "--server.port=8509", "--server.address=0.0.0.0"]
