FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["streamlit", "run", "src/app/streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
