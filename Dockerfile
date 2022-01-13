FROM python:3.7-slim

# specific options to compiler for annoy build
# useful for eg. disabling avx512 instruction set
ARG ANNOY_COMPILER_ARGS=

WORKDIR /opt/ann

RUN apt-get update && \
    apt-get install --no-install-suggests --no-install-recommends -y build-essential && \
    apt-get autoremove --purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY *.py /opt/ann/
COPY requirements.txt /opt/ann/
ENV ANNOY_COMPILER_ARGS=${ANNOY_COMPILER_ARGS}
RUN pip3 install --no-cache-dir -r /opt/ann/requirements.txt

WORKDIR /opt/ann
CMD ["/usr/local/bin/gunicorn", "--config", "/opt/ann/gunicorn_conf.py", "api:api"]
