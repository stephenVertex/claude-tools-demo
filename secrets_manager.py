import base64
import json

import boto3
import botocore


def get_secret(secret_name=None, region_name="us-east-1"):

    if secret_name is None:
        secret_name = "prod/sjbClickUp"
        print(
            "DEPRECATION_WARNING: Calling get_secret with no secret_name currently defaults to prod/sjbClickUp.  Will eventually default to None and raise error"
        )

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    # In this sample we only handle the specific exceptions for the 'GetSecretValue' API.
    # See https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
    # We rethrow the exception by default.

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except botocore.exceptions.ClientError as e:
        print(e)
        if e.response["Error"]["Code"] == "DecryptionFailureException":
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            raise e
        elif e.response["Error"]["Code"] == "InternalServiceErrorException":
            # An error occurred on the server side.
            raise e
        elif e.response["Error"]["Code"] == "InvalidParameterException":
            # You provided an invalid value for a parameter.
            raise e
        elif e.response["Error"]["Code"] == "InvalidRequestException":
            # You provided a parameter value that is not valid for the current state of the resource.
            raise e
        elif e.response["Error"]["Code"] == "ResourceNotFoundException":
            # We can't find the resource that you asked for.
            raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        # print("Secrets in the else block")
        if "SecretString" in get_secret_value_response:
            secret = get_secret_value_response["SecretString"]
        else:
            # This codepath may be unused, and/or untested.
            secret = base64.b64decode(get_secret_value_response["SecretBinary"])

        return json.loads(secret)  # returns the secret as dictionary
