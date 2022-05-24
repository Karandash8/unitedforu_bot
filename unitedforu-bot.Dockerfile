FROM ubuntu:18.04

# set timezone
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        debconf-utils \
        apt-utils \
        gcc \
        g++ \
    && echo 'tzdata tzdata/Areas select Europe' | debconf-set-selections \
    && echo 'tzdata tzdata/Zones/Europe select Paris' | debconf-set-selections \
    && DEBIAN_FRONTEND="noninteractive" apt-get install --no-install-recommends -y \
        tzdata

# install python 3.8 and set as default python
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        python3.8 \
        python3.8-dev \
        python3-pip \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.8 1

# install additional packages
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        ssh \
        vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# install ansible
RUN pip3 install --upgrade pip \
    && pip3 install setuptools \
    && pip3 install python-telegram-bot \
    && pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib

COPY ./bot-unitedforu /bot-unitedforu

ENTRYPOINT ["python", "/bot-unitedforu/main.py"]