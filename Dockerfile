FROM ubuntu:22.04 as k8s
RUN apt update && \
apt install -y curl && \
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.32/deb/Release.key --output /etc/apt/trusted.gpg.d/kubernetes.asc && \
echo "deb [signed-by=/etc/apt/trusted.gpg.d/kubernetes.asc] https://pkgs.k8s.io/core:/stable:/v1.32/deb/ /" > /etc/apt/sources.list.d/kubernetes.list && \ 
curl -fsSL https://baltocdn.com/helm/signing.asc --output /etc/apt/trusted.gpg.d/helm.asc && \
echo "deb [arch=amd64 signed-by=/etc/apt/trusted.gpg.d/helm.asc] https://baltocdn.com/helm/stable/debian/ all main" > /etc/apt/sources.list.d/helm-stable-debian.list && \
apt update && \
apt install -y kubelet=1.27.* kubeadm=1.27.* kubectl=1.27.* helm=3.11.* git-crypt && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

FROM ubuntu:22.04 as ansible

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && \
apt install -y python3 python3-pip python3-passlib rsync git-crypt && \
apt-get clean && \
rm -rf /var/lib/apt/lists/* && \
python3 -m pip install --no-cache-dir ansible ansible-lint && \
ansible-galaxy collection install kubernetes.core && \
python3 -m pip install --no-cache-dir staticjinja
