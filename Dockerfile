FROM python:3
WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
ENTRYPOINT  ["python","/app/emqx-exporter.py"]
CMD [""]