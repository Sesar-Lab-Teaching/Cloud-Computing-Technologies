# PaaS with Cloud Formation

Similarly to what we have done with IaaS, we can provision the PaaS infrastructure for the demo scenario using CloudFormation. The services we are going to use are:

- `RDS` - The database containing user data
- `Lambda` - 2 Lamdba functions:
    - `demo-cct-lambda-seed-db`: seeds the database with initial data
    - `demo-cct-lambda-get-data`: query the database to get accounts data
- `API Gateway` - Make Lambda Functions callable using HTTP requests

---

## Setup and Lambda creation

To create a Lambda Function, we first need to specify a deployment package. We can use a `.zip` file or a Docker image. In this demo, we will explore the second approach, therefore we first need to create an `ECR` repository for each Lambda function involved. 

```bash
aws cloudformation validate-template --template-body file://stack/ecr-repositories.yaml && \
aws cloudformation create-stack \
    --stack-name demo-cct-paas-ecr-repositories \
    --template-body file://stack/ecr-repositories.yaml
```

Then we save the repository URI for later:

```bash
SEED_DB_LAMBDA_REPO_URI="$(aws cloudformation describe-stacks \
    --stack-name demo-cct-paas-ecr-repositories \
    --output text \
    --query "Stacks[0].Outputs[?OutputKey == 'SeedDbLambdaRepoUri'].OutputValue")"
GET_DATA_LAMBDA_REPO_URI="$(aws cloudformation describe-stacks \
    --stack-name demo-cct-paas-ecr-repositories \
    --output text \
    --query "Stacks[0].Outputs[?OutputKey == 'GetDataLambdaRepoUri'].OutputValue")"
```

Now we can create the Docker images:

```bash
(
    cd ../src
    docker build -t "$SEED_DB_LAMBDA_REPO_URI" -f Dockerfile.lambda_seed_db .
    docker build -t "$GET_DATA_LAMBDA_REPO_URI" -f Dockerfile.lambda_get_data .
)
```