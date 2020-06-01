FROM python:3-alpine

WORKDIR /f2b-exporter

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./fail2ban-exporter.py"]
