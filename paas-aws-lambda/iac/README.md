# PaaS with Cloud Formation

Similarly to what we have done with IaaS, we can provision the PaaS infrastructure for the demo scenario using CloudFormation. The services we are going to use are:

- `RDS` - The database containing user data
- `Lambda` - 2 Lamdba functions:
    - `demo-cct-lambda-seed-db`: seeds the database with initial data
    - `demo-cct-lambda-get-data`: query the database to get accounts data
- `API Gateway` - Make Lambda Functions callable using HTTP requests

---

## Images for Lambda

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

And push them on the ECR registry:

```bash
ACCOUNT_ID="$(aws sts get-caller-identity \
    --query Account \
    --output text)"
REGION="$(aws configure get region)"
aws ecr get-login-password | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
docker push "$SEED_DB_LAMBDA_REPO_URI"
docker push "$GET_DATA_LAMBDA_REPO_URI"
```

---

## The Complete stack

We can now deploy the entire stack. First, create the S3 bucket (you can reuse the same one created for the demo `iaas-aws`:

```bash
BUCKET_NAME=demo-cct1
aws s3 mb s3://$BUCKET_NAME
```

Upload on S3 the nested stacks:

```bash
function upload_templates {
    for child_template in stack/modules/*
    do
        echo "Uploading $child_template"
        aws cloudformation validate-template --template-body file://$child_template > /dev/null && \
        aws s3 cp $child_template "s3://$BUCKET_NAME/paas/cfn-templates/$(basename "$child_template")"
    done
}
upload_templates
```

Then, we can create the stack:

```bash
aws cloudformation validate-template --template-body file://stack/root.yaml && \
aws cloudformation create-stack \
    --stack-name demo-cct-paas \
    --parameters "[
        {
            \"ParameterKey\": \"ECRSeedDbLambdaRepository\",
            \"ParameterValue\": \"$SEED_DB_LAMBDA_REPO_URI\"
        },
        {
            \"ParameterKey\": \"ECRGetDataLambdaRepository\",
            \"ParameterValue\": \"$GET_DATA_LAMBDA_REPO_URI\"
        }
    ]" \
    --capabilities CAPABILITY_NAMED_IAM \
    --template-body file://stack/root.yaml
```