FROM alpine/k8s:1.26.3 AS kubernetes
RUN apk add --update --no-cache git-crypt

FROM mambaorg/micromamba AS test
COPY --chown=$MAMBA_USER:$MAMBA_USER test/env.yaml /tmp/env.yaml
RUN micromamba install -y -n base -f /tmp/env.yaml && \
    micromamba clean --all --yes
