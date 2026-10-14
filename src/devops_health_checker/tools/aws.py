import boto3

from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)


def get_aws_identity():
    sts = boto3.client("sts")

    try:
        response = sts.get_caller_identity()

        return {
            "success": True,
            "data": {
                "account_id": response["Account"],
                "user_id": response["UserId"],
                "arn": response["Arn"],
            },
            "error": None,
        }

    except Exception as error:
        return {
            "success": False,
            "data": None,
            "error": (
                f"AWS identity check failed: "
                f"{error}"
            ),
        }


def get_ec2_instances():
    ec2 = boto3.client("ec2")

    try:
        response = ec2.describe_instances()

        instances = []

        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                instances.append(
                    {
                        "id": instance[
                            "InstanceId"
                        ],
                        "state": instance[
                            "State"
                        ]["Name"],
                        "type": instance[
                            "InstanceType"
                        ],
                        "private_ip": instance.get(
                            "PrivateIpAddress"
                        ),
                    }
                )

        return {
            "success": True,
            "data": instances,
            "error": None,
        }

    except Exception as error:
        return {
            "success": False,
            "data": None,
            "error": (
                f"EC2 health check failed: "
                f"{error}"
            ),
        }


def check_ec2_health():
    result = get_ec2_instances()

    if not result["success"]:
        return HealthResult(
            name="aws",
            status=HealthStatus.CRITICAL,
            details={},
            errors=[
                result["error"]
            ],
        )

    instances = result["data"]

    running = [
        instance
        for instance in instances
        if instance["state"] == "running"
    ]

    stopped = [
        instance
        for instance in instances
        if instance["state"] == "stopped"
    ]

    other = [
        instance
        for instance in instances
        if instance["state"]
        not in [
            "running",
            "stopped",
        ]
    ]

    if other:
        status = HealthStatus.WARNING

    elif stopped:
        status = HealthStatus.WARNING

    else:
        status = HealthStatus.HEALTHY

    return HealthResult(
        name="aws",
        status=status,
        details={
            "total_instances": len(
                instances
            ),
            "running_instances": len(
                running
            ),
            "stopped_instances": len(
                stopped
            ),
            "other_instances": len(
                other
            ),
            "instances": instances,
        },
        errors=[],
    )