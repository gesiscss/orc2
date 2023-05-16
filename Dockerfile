FROM ubuntu:22.04 as k8s
RUN apt-get update && \
apt install -y kubernetes git-crypt && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

FROM ubuntu:22.04 as ansible
RUN apt-get update && \
apt install -y ansible git-crypt && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

