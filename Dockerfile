FROM ubuntu:22.04 as k8s
RUN apt-get update && \
apt install -y kubernetes git-crypt && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

FROM ubuntu:22.04 as ansible

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && \
apt install -y ansible ansible-lint rsync git-crypt && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

