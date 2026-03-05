FROM python:3.7.0-slim-stretch

RUN apt-get update \
    && apt-get -y install curl build-essential \
    && apt-get clean \
    && pip install --upgrade pip

# Prepare environment
RUN mkdir /hfbot
WORKDIR /hfbot

# Install TA-lib
COPY build_helpers/* /tmp/
RUN cd /tmp && /tmp/install_ta-lib.sh && rm -r /tmp/*ta-lib*

ENV LD_LIBRARY_PATH /usr/local/lib

# Install dependencies
COPY requirements.txt /hfbot/
RUN pip3 install numpy --no-cache-dir \
  && pip3 install -r requirements.txt --no-cache-dir

# Install and execute
COPY . /hfbot/
RUN pip3 install -e . --no-cache-dir
ENTRYPOINT ["hfbot"]