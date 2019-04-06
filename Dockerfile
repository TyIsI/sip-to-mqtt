FROM python:2

WORKDIR /app
CMD [ "python", "sip-to-mqtt.py" ]

COPY . /app

RUN cd /app \
    && pip install --no-cache-dir -r requirements.txt -U

RUN cd /tmp \
    && wget -O rtclite.zip https://github.com/TyIsI/rtclite/archive/master.zip \
    && pip install -U rtclite.zip \
    && rm rtclite.zip
