"""Basic HTTP tests to make sure things are running"""
import pprint

import requests

TIMEOUT = 30


def test_binder_up(binder_url):
    """
    Binder Hub URL is up & returning sensible text
    """
    resp = requests.get(binder_url, timeout=TIMEOUT)
    assert resp.status_code == 200
    assert "GitHub" in resp.text


def test_hub_health(hub_url):
    """check JupyterHubHub health endpoint"""
    resp = requests.get(hub_url + "/hub/api/health", timeout=TIMEOUT)
    print(resp.text)
    assert resp.status_code == 200


def test_binder_health(binder_url):
    """check BinderHub health endpoint"""
    resp = requests.get(binder_url + "/health", timeout=TIMEOUT)
    pprint.pprint(resp.json())
    assert resp.status_code == 200
