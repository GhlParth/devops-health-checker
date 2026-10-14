from unittest.mock import Mock, patch

from devops_health_checker.tools.aws import (
    get_aws_identity,
    get_ec2_instances,
)


@patch(
    "devops_health_checker.tools.aws.boto3.client"
)
def test_get_aws_identity(mock_client):
    mock_sts = Mock()

    mock_sts.get_caller_identity.return_value = {
        "Account": "123456789012",
        "UserId": "test-user",
        "Arn": (
            "arn:aws:iam::123456789012:"
            "user/test"
        ),
    }

    mock_client.return_value = mock_sts

    result = get_aws_identity()

    assert result["success"] is True

    assert (
        result["data"]["account_id"]
        == "123456789012"
    )

    assert (
        result["data"]["user_id"]
        == "test-user"
    )


@patch(
    "devops_health_checker.tools.aws.boto3.client"
)
def test_get_ec2_instances(mock_client):
    mock_ec2 = Mock()

    mock_ec2.describe_instances.return_value = {
        "Reservations": [
            {
                "Instances": [
                    {
                        "InstanceId": (
                            "i-123456789"
                        ),
                        "InstanceType": "t3.micro",
                        "PrivateIpAddress": (
                            "10.0.1.10"
                        ),
                        "State": {
                            "Name": "running",
                        },
                    }
                ]
            }
        ]
    }

    mock_client.return_value = mock_ec2

    result = get_ec2_instances()

    assert result["success"] is True
    assert len(result["data"]) == 1

    assert (
        result["data"][0]["id"]
        == "i-123456789"
    )

    assert (
        result["data"][0]["state"]
        == "running"
    )


@patch(
    "devops_health_checker.tools.aws.boto3.client"
)
def test_get_ec2_instances_failure(
    mock_client,
):
    mock_ec2 = Mock()

    mock_ec2.describe_instances.side_effect = (
        Exception("AWS API failure")
    )

    mock_client.return_value = mock_ec2

    result = get_ec2_instances()

    assert result["success"] is False
    assert result["data"] is None

    assert (
        "AWS API failure"
        in result["error"]
    )