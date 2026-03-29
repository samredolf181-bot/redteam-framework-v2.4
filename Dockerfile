FROM python:3.11-slim-bullseye
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends nmap dnsutils whois exiftool curl jq git && rm -rf /var/lib/apt/lists/*
COPY rtf/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY rtf /app
EXPOSE 5000
CMD ["python","rtf.py"]
