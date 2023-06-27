"""Script to identify when Docker-in-Docker stop working."""

import argparse
import datetime
import logging

from kubernetes import client, config, watch

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("orc2-fix-dind-bot")
logger.setLevel(logging.WARNING)

NAMESPACE = "gesis"


def monitor_cluster():
    """Monitor pod"""
    logger.info("Start monitoring ...")

    w = watch.Watch()
    for event in w.stream(v1.list_namespaced_event, namespace=NAMESPACE):
        if event["object"].metadata.name.startswith("binderhub-dind-"):
            if event["object"].type == "Warning":
                logger.info("Found Warning event in %s", event["object"].metadata.name)
                if event["object"].reason == "BackOff":
                    time_since_last_timestamp = (
                        datetime.datetime.now(datetime.timezone.utc)
                        - event["object"].last_timestamp
                    )

                    if time_since_last_timestamp.seconds > 5:
                        logger.info(
                            "Skipping because event old (%d > 5 seconds).",
                            time_since_last_timestamp.seconds,
                        )
                    else:
                        logger.info(
                            "Removing Docker-in-Docker socket and containers ..."
                        )
            elif event["object"].type == "Normal":
                logger.debug(
                    "Found Normal event in %s ... skipping!",
                    event["object"].metadata.name,
                )
            else:
                logger.debug(
                    "Found %s event in %s ... ignoring!",
                    event["object"].type,
                    ["object"].metadata.name,
                )

    logger.info("Stop monitoring!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Open Research Computing v2 Fix JupyterHub Bot",
        description="Monitoring Kubernetes cluster to restart JupyterHub",
    )
    parser.add_argument(
        "-c",
        "--kube-config",
        type=str,
        default="~/.kube/config",
        help="Location of Kubernetes configuration file",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Display log information"
    )
    parser.add_argument(
        "-vv", "--debug", action="store_true", help="Display debug information"
    )
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.INFO)
    if args.debug:
        logger.setLevel(logging.DEBUG)

    config.load_kube_config(config_file=args.kube_config)

    v1 = client.CoreV1Api()

    monitor_cluster()
