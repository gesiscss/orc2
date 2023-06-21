---
name: Unhealth server
about: Report a unhealth status from notebooks.gesis.org
title: 'https://notebooks.gesis.org/binder/ is unhealth'
labels: ''
assignees: '@rgaiacs'
---

https://notebooks.gesis.org/binder/health return <!-- failed system information -->.

## What is the current bug behavior?

<!-- Paste the json report -->

## What is the expected correct behavior?

```json
{
    "ok": true,
    "checks": [
        {
            "service": "Docker registry",
            "ok": true
        },
        {
            "service": "JupyterHub API",
            "ok": true
        },
        {
            "service": "Pod quota",
            "total_pods": 4,
            "build_pods": 1,
            "user_pods": 3,
            "quota": 100,
            "ok": true,
            "_ignore_failure": true
        }
    ]
}
```

## Steps to reproduce

1. Go to https://notebooks.gesis.org/binder/health using your web browser

or, alternatively,

1. run `wget https://notebooks.gesis.org/binder/health`
