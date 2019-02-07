import os

import boto3
import json

from botocore.exceptions import ClientError

from base.utils import get_model_object

from .models import Challenge, ChallengePhase, Leaderboard, DatasetSplit, ChallengePhaseSplit


get_challenge_model = get_model_object(Challenge)

get_challenge_phase_model = get_model_object(ChallengePhase)

get_leaderboard_model = get_model_object(Leaderboard)

get_dataset_split_model = get_model_object(DatasetSplit)

get_challenge_phase_split_model = get_model_object(ChallengePhaseSplit)


def get_file_content(file_path, mode):
    if os.path.isfile(file_path):
        with open(file_path, mode) as file_content:
            return file_content.read()


def convert_to_aws_ecr_compatible_format(string):
    return string.replace(" ", "-").lower()


def get_or_create_ecr_repository(name, region_name='us-east-1'):
    '''Get or create AWS ECR Repository
    
    Arguments:
        name {string} -- name of ECR repository
        tag {dict} -- Dictionary to store some tags for repository identification 
    
    Keyword Arguments:
        region_name {str} -- AWS region name (default: {'us-east-1'})
    
    Returns:
        tuple -- Contains repository dict and boolean field to represent whether ECR repository was created
        Eg: (
                {
                    'repositoryArn': 'arn:aws:ecr:us-east-1:1234567890:repository/some-repository-name',
                    'registryId': '1234567890',
                    'repositoryName': 'some-repository-name',
                    'repositoryUri': '1234567890.dkr.ecr.us-east-1.amazonaws.com/some-repository-name',
                    'createdAt': datetime.datetime(2019, 2, 6, 9, 12, 5, tzinfo=tzlocal())
                },
                False
            )

    '''
    AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')
    repository, created = None, False
    client = boto3.client('ecr', region_name=region_name)
    try:
        response = client.describe_repositories(
            registryId=AWS_ACCOUNT_ID,
            repositoryNames=[
                name,
            ]
        )
        repository = response['repositories'][0]
    except ClientError as e:
        if e.response['Error']['Code'] == 'RepositoryNotFoundException':
            response = client.create_repository(repositoryName=name)
            repository = response['repository']
            created = True
    return (repository, created)


def create_federated_user(name, repository):
    '''Create AWS federated user
    
    Arguments:
        name {string} -- Name of participant team for which federated user is to be created
        repository {string} -- Name of the AWS ECR repository to which user should be granted permission
    
    Returns:
        dict -- Dict containing user related credentials such as access_key_id, access_secret etc.
        Eg: 
        {
            'Credentials': {
                'AccessKeyId': 'ABCDEFGHIJKLMNOPQRTUVWXYZ',
                'SecretAccessKey': 'NMgBB75gfVBCDEFGHIJK8g00qVyyzQW+4XjJGQALMNOPQRSTUV',
                'SessionToken': 'FQoGZX.....',
                'Expiration': datetime.datetime(2019, 2, 7, 5, 43, 58, tzinfo=tzutc())
            },
            'FederatedUser': {
                'FederatedUserId': '1234567890:test-user',
                'Arn': 'arn:aws:sts::1234567890:federated-user/test-user'
            },
            'PackedPolicySize': 28,
            'ResponseMetadata': {
                'RequestId': 'fb47f78b-2a92-11e9-84b9-33527429b818',
                'HTTPStatusCode': 200,
                'HTTPHeaders': {
                'x-amzn-requestid': 'fb47f78b-2a92-11e9-84b9-33527429b818',
                'content-type': 'text/xml',
                'content-length': '1245',
                'date': 'Thu, 07 Feb 2019 04:43:57 GMT'
                },
                'RetryAttempts': 0
            }
        }
    '''
    AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')
    policy = {
      "Version":"2019-02-07",
      "Statement":[
          {
            "Effect":"Allow",
            "Action": "ecr:*",
            "Resource": "arn:aws:ecr:us-east-1:{}:repository/{}".format(AWS_ACCOUNT_ID, repository),
           },
            {
              "Effect": "Allow",
              "Action": [
                "ecr:GetAuthorizationToken"
              ],
              "Resource": "*"
            }
      ]
    }
    client = boto3.client('sts')
    response = client.get_federation_token(
        Name=name,
        Policy=json.dumps(policy),
        DurationSeconds=3600
    )
    return response
