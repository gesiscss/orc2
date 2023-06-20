"""Script to identify when JupyterHub stop working."""

import argparse
import datetime
import logging

from kubernetes import client, config, watch

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("orc2-fix-jupyterhub-bot")
logger.setLevel(logging.WARNING)

NAMESPACE = "gesis"
RESTART_WAITING_TIME = 120  # seconds


def get_binder_pod():
    """Get name of pod running Binder."""
    api_response = v1.list_namespaced_pod(NAMESPACE)
    for pod in api_response.items:
        logger.debug("Pod %s", pod.metadata.name)
        if pod.metadata.name.startswith("binder-"):
            binder_pod_name = pod.metadata.name
            break

    return binder_pod_name


def kill_jupyterhub_pod():
    """Kill all JupyterHub pods"""
    api_response = v1.list_namespaced_pod(NAMESPACE)
    for pod in api_response.items:
        logger.debug("Pod %s", pod.metadata.name)
        if pod.metadata.name.startswith("hub-"):
            v1.delete_namespaced_pod(pod.metadata.name, NAMESPACE)


def monitor_pod():
    """Monitor pod"""
    while True:
        pod_name = get_binder_pod()
        logger.info("Monitoring %s", pod_name)

        last_jupyterhub_restart = datetime.datetime.now()

        w = watch.Watch()
        for line in w.stream(
            v1.read_namespaced_pod_log, name=pod_name, namespace=NAMESPACE, tail_lines=0
        ):
            if line.find("Error accessing Hub API") > -1:
                logger.debug(line)

                now = datetime.datetime.now()
                time_difference = now - last_jupyterhub_restart
                if time_difference.seconds > RESTART_WAITING_TIME:
                    logger.debug("Restarting JupyterHub ...")
                    kill_jupyterhub_pod()
                    last_jupyterhub_restart = now
                else:
                    logger.debug(
                        "Waiting %s seconds for JupyterHub to restart.",
                        RESTART_WAITING_TIME,
                    )

        logger.info("Stop monitoring %s", pod_name)

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

    monitor_pod()
