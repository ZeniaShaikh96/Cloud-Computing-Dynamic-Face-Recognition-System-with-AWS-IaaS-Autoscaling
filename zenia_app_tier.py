import boto3
import os
import logging
from face_recognition_1 import face_match

# AWS configuration and clients
aws_region = 'us-east-1'
s3 = boto3.client('s3', region_name=aws_region)  # S3 client
sqs = boto3.client('sqs', region_name=aws_region)  # SQS client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# AWS SQS queue and S3 bucket details
request_queue_url = 'https://sqs.us-east-1.amazonaws.com/710271919140/1229028439-req-queue'
response_queue_url = 'https://sqs.us-east-1.amazonaws.com/710271919140/1229028439-resp-queue'
input_bucket_name = '1229028439-in-bucket'
output_bucket_name = '1229028439-out-bucket'
model_path = "/home/ubuntu/CSE-546-CC/CSE546-Cloud-Computing/model/data.pt"

def process_images():
    while True:
        # Poll SQS for messages (image filenames)
        response = sqs.receive_message(QueueUrl=request_queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=20)
        
        if 'Messages' in response:
            for message in response['Messages']:
                image_filename = message['Body'].strip()
                local_image_path = f"/tmp/{os.path.basename(image_filename)}"
                
                logging.info(f"Received image filename from SQS: {image_filename}")
                
                try:
                    # Download image from S3 input bucket
                    logging.info(f"Downloading image from S3: {input_bucket_name}/{image_filename}")
                    s3.download_file(Bucket=input_bucket_name, Key=image_filename, Filename=local_image_path)
                    
                    # Perform face recognition (classification)
                    logging.info(f"Performing face recognition on: {local_image_path}")
                    classification_result = face_match(local_image_path, model_path)  # This returns the classification result, e.g., 'Paul'
                    
                    # Remove the file extension from the image filename
                    image_filename_without_ext = os.path.splitext(image_filename)[0]
                    
                    # Format result for SQS as <image_filename_without_ext:classification result>
                    result_message = f"{image_filename_without_ext}:{classification_result}"
                    
                    # Use the classification result as the key and content in the S3 bucket
                    result_key = f"{classification_result}"  # The key will now be the result itself, e.g., 'Paul'
                    
                    # Upload the classification result (name of the person) as the content to S3
                    logging.info(f"Uploading classification result to S3: {output_bucket_name}/{result_key}")
                    s3.put_object(Bucket=output_bucket_name, Key=result_key, Body=classification_result)
                    
                    # Send result to the SQS response queue
                    logging.info(f"Sending classification result to SQS: {result_message}")
                    sqs.send_message(QueueUrl=response_queue_url, MessageBody=result_message)

                except Exception as e:
                    logging.error(f"Error processing {image_filename}: {e}")

                finally:
                    # Clean up local image and delete message from request queue
                    if os.path.exists(local_image_path):
                        os.remove(local_image_path)
                    sqs.delete_message(QueueUrl=request_queue_url, ReceiptHandle=message['ReceiptHandle'])
                    logging.info(f"Deleted processed SQS message: {message['ReceiptHandle']}")
        
        else:
            logging.info("No new messages in queue. Waiting for new images...")

if __name__ == '__main__':
    logging.info("Starting image processing...")
    process_images()
