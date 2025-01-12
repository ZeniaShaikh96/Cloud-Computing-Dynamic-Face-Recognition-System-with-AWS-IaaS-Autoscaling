# Cloud-Computing-Dynamic-Face-Recognition-System-with-AWS-IaaS-Autoscaling
Complete an elastic face recognition application using AWS IaaS. Implement App and Data Tiers with S3 storage, scalable EC2-based App Tier for ML inference, and a Web Tier to manage requests. Incorporate custom autoscaling, concurrent processing, and testing with a workload generator to ensure performance.
Project Title: "Elastic Multi-Tier Face Recognition Application with AWS IaaS"
Project Description:
This project completes the development of an elastic face recognition application leveraging AWS IaaS. It involves building and integrating three tiers: Web Tier, App Tier, and Data Tier, with features such as machine learning inference, autoscaling, and persistent storage.

Web Tier
Functionality:

Receives user-uploaded images (.jpg) via HTTP POST requests to the root endpoint (/).
Forwards images to the App Tier for processing and returns the recognition results.
Handles concurrent requests efficiently.
Architecture:

Utilizes the EC2 instance from Part 1, named web-instance.
Implements communication with the App Tier using two SQS queues:
Request Queue (<ASU ID>-req-queue)
Response Queue (<ASU ID>-resp-queue)
Runs a custom autoscaling controller for the App Tier (AWS-managed autoscaling is not allowed).
App Tier
Functionality:

Processes image recognition requests using a provided deep learning model.
Dynamically scales based on request volume:
Scales out during high demand (up to 20 instances).
Scales in when demand decreases (0 instances when idle).
Processes requests using instances created from a custom AMI.
Setup:

Launch a base EC2 instance with required dependencies (torch, torchvision, torchaudio).
Configure the instance with the model code and weights.
Save the configured instance as an AMI, used to launch App Tier instances (app-tier-instance-<instance#>).
Data Tier
Functionality:

Stores input images and their recognition results in S3 buckets for persistence.
Input Bucket: Stores images (<ASU ID>-in-bucket).
Output Bucket: Stores recognition results as key-value pairs (<ASU ID>-out-bucket).
Bucket Structure:

Input:
Key: Image filename (e.g., test_00.jpg).
Value: Image file.
Output:
Key: Image filename without extension (e.g., test_00).
Value: Classification result (e.g., Paul).
