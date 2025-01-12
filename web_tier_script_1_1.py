
from flask import Flask, request, jsonify
import boto3
import logging
from PIL import Image
import os
import botocore
import csv

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)

config = botocore.config.Config(
    region_name='us-east-1',
    max_pool_connections=250  # Increase connection pool size for higher loads
)

# AWS SQS and S3 client setup with the new config
sqs = boto3.client('sqs', config=config)
s3 = boto3.client('s3', config=config)

request_queue_url = 'https://sqs.us-east-1.amazonaws.com/710271919140/1229028439-req-queue'
response_queue_url = 'https://sqs.us-east-1.amazonaws.com/710271919140/1229028439-resp-queue'

# S3 bucket name
bucket_name = '1229028439-in-bucket'

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB file size limit
csv_filename = 'classification_results.csv'

# Ensure the CSV file exists and has the correct headers
def initialize_csv_file():
    if not os.path.exists(csv_filename):
        with open(csv_filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['filename', 'classification_result'])  # Write the header row

# Check if a file is an image
def is_image(file):
    try:
        img = Image.open(file)
        img.verify()  # Verify if the file is a valid image
        return True
    except (IOError, SyntaxError):
        return False

# Store the SQS messages in a CSV file, preventing duplicates
def store_messages_in_csv(messages):
    existing_filenames = set()  # Store existing filenames
    
    # Load existing filenames from the CSV
    with open(csv_filename, 'r', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            existing_filenames.add(row[0])

    # Write new messages to the CSV if they don't already exist
    with open(csv_filename, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for message in messages:
            message_body = message['Body']
            filename, classification_result = message_body.split(':')
            if filename not in existing_filenames:  # Only store if not already present
                writer.writerow([filename, message_body])  # Write to CSV
                logging.info(f"Stored {message_body} in CSV.")

            # Delete the message from SQS after processing
            sqs.delete_message(
                QueueUrl=response_queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )

# Poll the SQS queue for responses and store in CSV
def poll_response_queue_batch():
    response = sqs.receive_message(
        QueueUrl=response_queue_url,
        MaxNumberOfMessages=10,  # Poll up to 10 messages at a time
        WaitTimeSeconds=2  # Long polling
    )
    messages = response.get('Messages', [])
    if messages:
        store_messages_in_csv(messages)

# Search for the requested image result in the CSV file, using filename without extension
def lookup_in_csv(image_filename):
    filename_without_ext = os.path.splitext(image_filename)[0]  # Remove extension
    logging.info(f"Looking up {filename_without_ext} in the CSV file.")
    
    with open(csv_filename, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            logging.info(f"Checking row: {row}")
            if row[0] == filename_without_ext:  # Compare without extension
                logging.info(f"Found result for {filename_without_ext}: {row[1]}")
                return row[1]  # Return the <filename:classification_result>
    logging.info(f"{filename_without_ext} not found in CSV.")
    return None  # Return None if not found

# Main logic to continuously poll until the result for a specific image is found
def get_classification_result(image_filename):
    while True:
        # Check the CSV for the requested image's result
        result = lookup_in_csv(image_filename)
        if result:
            return result  # If found, return the result

        # If not found, poll the SQS queue for more messages
        poll_response_queue_batch()

@app.route('/', methods=['POST'])
def upload_image():
    try:
        if 'inputFile' not in request.files:
            return jsonify({"error": "No inputFile part in the request"}), 400

        input_file = request.files['inputFile']

        # Check file size
        if len(input_file.read()) > MAX_FILE_SIZE:
            return jsonify({"error": "File size exceeds limit"}), 400
        input_file.seek(0)  # Reset the file pointer after reading

        # Check if the file is a valid image
        if not is_image(input_file):
            return jsonify({"error": "Invalid image file"}), 400

        input_file.seek(0)  # Reset the file pointer again for upload

        original_filename = input_file.filename

        # Upload the image directly from memory to S3
        try:
            s3.upload_fileobj(
                input_file,
                bucket_name,
                original_filename  # Use the original filename as the object key
            )
            logging.info(f"Uploaded image to S3: {bucket_name}/{original_filename}")

            # Send a message to the request queue with the image filename
            sqs.send_message(
                QueueUrl=request_queue_url,
                MessageBody=original_filename
            )
            logging.info(f"Sent SQS message for image: {original_filename}")

            # Poll the response queue and retrieve classification result
            logging.info(f"Waiting for classification result for image: {original_filename}")
            result = get_classification_result(original_filename)

            return f"{result}", 200

        except Exception as e:
            logging.error(f"Error uploading image or sending SQS message: {e}")
            return jsonify({"error": "Error processing image"}), 500

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    initialize_csv_file()  # Ensure the CSV is initialized
    app.run(host='0.0.0.0', port=80, debug=True)
