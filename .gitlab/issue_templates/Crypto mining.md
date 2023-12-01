## What is the current bug behavior?

GESIS Notebooks is being used for crypto mining.

## What is the expected correct behavior?

GESIS Notebooks has **zero** crypto mining pods.

## Crypto mining indicator

Screenshot of https://grafana.mybinder.org/d/nDQPwi7mk/node-activity?orgId=1&var-cluster=000000002&viewPanel=38&from=now-12h&to=now

## Crypto mining suspect

Repository: <crypto-mining-git-repository>

From `spko-css-app03`, `ps aux --sort=-pcpu | head -n 10` returns

```
output goes here
```

From `spko-css-app03`, `pstree -s -p MINER_PID` (where `MINER_PID` is the process ID crypto mining) returns

```
output goes here
```

From `spko-css-app03`, `sudo nsenter -t CONTAINERD_SHIM_PID -u hostname` (where `CONTAINERD_SHIM_PID` is the process ID of the containerd-shim that is the parent of the crypto mining) returns

```
output goes here
```
