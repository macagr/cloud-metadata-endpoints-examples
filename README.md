# Fun with Metadata Endpoints

This repository contains the deployments in three different cloud providers: AWS, Azure, and Google Cloud. The folders for Azure and AWS deploy a vulnerable YouTrack container in:
- ECS and Fargate.
- Azure and Azure Container Instances.
The infrastructure is deployed using Pulumi. Each Service also deploys a single resource that can be reached only by using the container IAM role/Managed Identity.

The folder for gcp contains an application deployed in Cloud Run and a shell obtained by using the code in [https://github.com/matti/google-cloud-run-shell](https://github.com/matti/google-cloud-run-shell). All the credits go to the corresponding authors. 



