
import boto3
import time

# Constants
MAX_INSTANCES = 20
MIN_INSTANCES = 0
INSTANCE_TYPE = 't2.micro'  # Change as per your instance type
AMI_ID = 'ami-0693aaf279d97623f'  # Replace with your App Tier AMI ID
REQUEST_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/710271919140/1229028439-req-queue'  # Replace with your request queue URL
REGION = 'us-east-1'  # Set to your region
IAM_ROLE_NAME = 'access_aws_resources'  # Replace with your IAM role name

# AWS Clients
ec2_client = boto3.client('ec2', region_name=REGION)
sqs_client = boto3.client('sqs', region_name=REGION)

def get_queue_size():
    """Get the approximate number of messages in the SQS request queue."""
    response = sqs_client.get_queue_attributes(
        QueueUrl=REQUEST_QUEUE_URL,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(response['Attributes'].get('ApproximateNumberOfMessages', 0))

def get_current_instance_count():
    """Get the number of running instances in the App Tier."""
    response = ec2_client.describe_instances(
        Filters=[
            {'Name': 'tag:Name', 'Values': ['app-tier-instance-*']},  # Adjust tag name as needed
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    return len([instance for reservation in response['Reservations'] for instance in reservation['Instances']])

def scale_out(current_instance_count, target_instance_count):
    """Scale out by launching additional instances."""
    instances_to_launch = target_instance_count - current_instance_count
    if instances_to_launch > 0:
        print(f"Scaling out: Launching {instances_to_launch} new instances")
        
        # Launch each instance with its unique tag
        for i in range(instances_to_launch):
            instance_number = current_instance_count + i + 1  # Increment instance number for each new instance
            instance_name = f'app-tier-instance-{instance_number}'
            print(f"Launching instance {instance_name}")
            ec2_client.run_instances(
                ImageId=AMI_ID,
                InstanceType=INSTANCE_TYPE,
                MinCount=1,
                MaxCount=1,
                IamInstanceProfile={'Name': IAM_ROLE_NAME},
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': instance_name}]
                }]
            )

def scale_in(current_instance_count, target_instance_count):
    """Scale in by terminating excess instances."""
    instances_to_terminate = current_instance_count - target_instance_count
    if instances_to_terminate > 0:
        print(f"Scaling in: Terminating {instances_to_terminate} instances")
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': ['app-tier-instance-*']},
                {'Name': 'instance-state-name', 'Values': ['running']}
            ]
        )
        instance_ids = [instance['InstanceId'] for reservation in response['Reservations'] for instance in reservation['Instances']]
        instances_to_terminate = instance_ids[:instances_to_terminate]
        ec2_client.terminate_instances(InstanceIds=instances_to_terminate)

def autoscale():
    while True:
        queue_size = get_queue_size()
        current_instance_count = get_current_instance_count()

        # Determine target number of instances based on the queue size
        if queue_size == 0:
            target_instance_count = 0
        else:
            target_instance_count = min(MAX_INSTANCES, max(MIN_INSTANCES, queue_size))

        print(f"Queue size: {queue_size}, Current instances: {current_instance_count}, Target instances: {target_instance_count}")

        if current_instance_count < target_instance_count:
            scale_out(current_instance_count, target_instance_count)
        elif current_instance_count > target_instance_count:
            scale_in(current_instance_count, target_instance_count)

        # Wait before checking again
        time.sleep(30)

if __name__ == '__main__':
    autoscale()
