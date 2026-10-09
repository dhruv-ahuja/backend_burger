# [wip]backend_burger

## Tech Stack

- FastAPI webapp running on Python3.11
- Beanie ODM on top of MongoDB
- Pydantic v2 for all schemas, models and validation needs
- Ruff for formatting and linting code
- AWS Services: Cloudwatch to gather logs, S3 Bucket to store logs for long durations, SQS to handle background tasks
- New Relic integration for application monitoring

## Initial setup

Create a `.env` file in the project root before running the application. The environment file is used by Docker Compose and should not be committed.

```env
AWS_ACCESS_KEY_ID=<your-aws-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-aws-secret-access-key>
AWS_REGION_NAME=<your-aws-region>
SQS_QUEUE_NAME=<your-sqs-queue-name>
S3_BUCKET_URL=<your-s3-bucket-url>
S3_BUCKET_NAME=<your-s3-bucket-name>
S3_LOGS_FOLDER=<your-s3-logs-folder>
DB_USER=dhruv
DB_PASSWORD=<your-database-password>
DB_URL=<your-database-url>
JWT_SECRET_KEY=<your-jwt-secret-key>
LOGFIRE_PYDANTIC_PLUGIN_RECORD=<true-or-false>
NEW_RELIC_LICENSE_KEY=<your-new-relic-license-key>
NEW_RELIC_APP_NAME=<your-new-relic-app-name>
REDIS_HOST=<your-redis-host>
REDIS_PASSWORD=<your-redis-password>
APP_ENVIRONMENT=dev
```

For a local setup, set `APP_ENVIRONMENT=dev`. By default, the Docker Compose service sets `APP_ENVIRONMENT=prod` for containerized runs.

## Running the app

Install the dependencies and run the FastAPI application locally:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The application is available at `http://localhost:8000`.

## Build and run with Docker

Build image:

```bash
export VERSION=latest
docker build -t backend_burger:${VERSION} .
```

Run container:

```bash
export VERSION=latest
docker run --rm -p 8000:8000 --env-file .env backend_burger:${VERSION}
```

## Run with Docker Compose

Build and start the application with Redis:

```bash
export VERSION=latest
docker compose up --build -d
```

Follow the application logs:

```bash
docker compose logs -f backend_burger
```

Stop the application:

```bash
docker compose down
```

## Publish the Docker image

The CD workflow builds and publishes the image to Docker Hub when a `v*` tag is pushed. To publish a new version:

```bash
git tag v1.0.0
git push origin v1.0.0
```

## Tech Setup

An initial production setup could be:
An AWS ECS cluster setup running the MongoDB database service in an EC2 machine with mounted storage EBS storage, initially (will experiment with a more advanced setup soon). Another service to run several instances of the backend app on Fargate. The backend is configured to auto-scale.
Backend and DB share the same VPC and have service discovery enabled for communication using the namespace DNS. The namespace DNS ensures that the communication happens dynamically without worrying about IP addresses for the services.
All services are private and a public Application Load Balancer routes incoming traffic to one of the upstream backend servers.

## Extending the project

I have now extended this project to serve as the backend for my [full-stack application](https://winter-orb.vercel.app/), [frontend repository](https://github.com/dhruv-ahuja/winter-orb).
