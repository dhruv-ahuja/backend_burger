# [wip]backend_burger

## Tech Stack

- FastAPI webapp running on Python3.11
- Beanie ODM on top of MongoDB
- Pydantic v2 for all schemas, models and validation needs
- Ruff for formatting and linting code
- AWS Services: Cloudwatch to gather logs, S3 Bucket to store logs for long durations, SQS to handle background tasks
- New Relic integration for application monitoring

## Tech Setup

An initial production setup could be:
An AWS ECS cluster setup running the MongoDB database service in an EC2 machine with mounted storage EBS storage, initially (will experiment with a more advanced setup soon). Another service to run several instances of the backend app on Fargate. The backend is configured to auto-scale.
Backend and DB share the same VPC and have service discovery enabled for communication using the namespace DNS. The namespace DNS ensures that the communication happens dynamically without worrying about IP addresses for the services.
All services are private and a public Application Load Balancer routes incoming traffic to one of the upstream backend servers.

## Extending the project

I have now extended this project to serve as the backend for my [full-stack application](https://winter-orb.vercel.app/), [frontend repository](https://github.com/dhruv-ahuja/winter-orb).
