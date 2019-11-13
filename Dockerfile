FROM python:3
WORKDIR /app
ADD . /app
RUN pip install -r requirements.txt
ENV PARAMS=""
ENTRYPOINT ["sh","-c","python /app/emqx-exporter.py $PARAMS"]