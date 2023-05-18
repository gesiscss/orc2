FROM ubuntu:22.04 as k8s
RUN apt update && \
apt install -y curl && \
curl https://baltocdn.com/helm/signing.asc --output /etc/apt/trusted.gpg.d/helm.asc && \
echo "deb [arch=amd64 signed-by=/etc/apt/trusted.gpg.d/helm.asc] https://baltocdn.com/helm/stable/debian/ all main" > /etc/apt/sources.list.d/helm-stable-debian.list && \
curl https://dl.k8s.io/apt/doc/apt-key.gpg --output /etc/apt/trusted.gpg.d/kubernetes.gpg && \
echo "deb [signed-by=/etc/apt/trusted.gpg.d/kubernetes.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" > /etc/apt/sources.list.d/kubernetes.list && \ 
apt update && \
apt install -y kubelet=1.27.* kubeadm=1.27.* kubectl=1.27.* helm git-crypt && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

FROM ubuntu:22.04 as ansible

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && \
apt install -y ansible ansible-lint python3-passlib rsync git-crypt && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
ansible-galaxy collection install kubernetes.core
