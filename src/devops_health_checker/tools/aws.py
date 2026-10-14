import boto3
from botocore.exceptions import (
    ClientError,
    EndpointResolutionError,
    NoCredentialsError,
    NoRegionError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from devops_health_checker.models import (
    HealthResult,
    HealthStatus,
)

# Transient AWS errors worth retrying (throttles, endpoint blips).
_RETRYABLE_AWS = (
    ClientError,
    EndpointResolutionError,
)


def _is_throttle(exc: Exception) -> bool:
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        return code in {"RequestLimitExceeded", "Throttling", "ThrottlingException"}
    return True


@retry(
    reraise=True,
    retry=retry_if_exception_type(_RETRYABLE_AWS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
def _sts_get_caller_identity() -> dict:
    return boto3.client("sts").get_caller_identity()


@retry(
    reraise=True,
    retry=retry_if_exception_type(_RETRYABLE_AWS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
def _ec2_describe_instances() -> dict:
    return boto3.client("ec2").describe_instances()


def get_aws_identity() -> dict:
    try:
        response = _sts_get_caller_identity()
        return {
            "success": True,
            "data": {
                "account_id": response["Account"],
                "user_id": response["UserId"],
                "arn": response["Arn"],
            },
            "error": None,
        }
    except NoCredentialsError:
        return {
            "success": False,
            "data": None,
            "error": "AWS credentials not configured",
        }
    except Exception as error:
        return {
            "success": False,
            "data": None,
            "error": f"AWS identity check failed: {error}",
        }


def get_ec2_instances() -> dict:
    try:
        response = _ec2_describe_instances()
        instances = []
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                instances.append(
                    {
                        "id": instance["InstanceId"],
                        "state": instance["State"]["Name"],
                        "type": instance["InstanceType"],
                        "private_ip": instance.get("PrivateIpAddress"),
                        "launch_time": str(instance.get("LaunchTime", "")),
                        "tags": {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])},
                    }
                )
        return {"success": True, "data": instances, "error": None}

    except NoCredentialsError:
        return {
            "success": False,
            "data": None,
            "error": "AWS credentials not configured",
        }
    except NoRegionError:
        return {
            "success": False,
            "data": None,
            "error": "AWS region not configured — set AWS_REGION or aws.region in config.yaml",
        }
    except Exception as error:
        return {
            "success": False,
            "data": None,
            "error": f"EC2 health check failed: {error}",
        }


def check_ec2_health() -> HealthResult:
    result = get_ec2_instances()

    if not result["success"]:
        return HealthResult(
            name="aws",
            status=HealthStatus.CRITICAL,
            details={},
            errors=[result["error"]],
        )

    instances = result["data"]

    running = [i for i in instances if i["state"] == "running"]
    stopped = [i for i in instances if i["state"] == "stopped"]
    other = [i for i in instances if i["state"] not in {"running", "stopped"}]

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
            "total_instances": len(instances),
            "running_instances": len(running),
            "stopped_instances": len(stopped),
            "other_instances": len(other),
            "instances": instances,
        },
        errors=[],
    )
