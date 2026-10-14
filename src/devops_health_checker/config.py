from pathlib import Path

import yaml


CONFIG_FILE = Path("config.yaml")


def load_config():
    if not CONFIG_FILE.exists():
        return {}

    with CONFIG_FILE.open("r") as file:
        return yaml.safe_load(file) or {}


def get_aws_region(config):
    return config.get(
        "aws",
        {},
    ).get(
        "region",
        "ap-south-1",
    )


def get_github_config(config):
    return config.get(
        "github",
        {},
    )


def get_kubernetes_config(config):
    return config.get(
        "kubernetes",
        {},
    )