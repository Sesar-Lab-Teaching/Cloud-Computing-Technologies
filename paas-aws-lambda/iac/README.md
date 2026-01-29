# PaaS with Cloud Formation

Similarly to what we have done with IaaS, we can provision the PaaS infrastructure for the demo scenario using CloudFormation. The services we are going to use are:

- **RDS** - The database containing user data
- **Lambda** - 2 Lamdba functions:
    - `demo-cct-lambda-seed-db`: seeds the database with initial data
    - `demo-cct-lambda-get-data`: query the database to get accounts data
- **API Gateway** - Make Lambda Functions callable using HTTP requests

---

## Images for Lambda

To create a Lambda Function, we first need to specify a deployment package, which can be either a `.zip` file or a container image. In this demo, we will explore the second approach, therefore we first need to create an `ECR` repository for each Lambda function involved. 

```bash
aws cloudformation validate-template --template-body file://stack/ecr-repositories.yaml
aws cloudformation deploy \
    --stack-name demo-cct-paas-ecr-repositories \
    --template-file stack/ecr-repositories.yaml
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
docker build --platform linux/amd64 --provenance=false -t "$SEED_DB_LAMBDA_REPO_URI" -f ../src/Dockerfile.lambda_seed_db ../src
docker build --platform linux/amd64 --provenance=false -t "$GET_DATA_LAMBDA_REPO_URI" -f ../src/Dockerfile.lambda_get_data ../src
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

## Deploy the Scenario

We can now deploy the stack with all the PaaS components. First, create the S3 bucket (you can reuse the same one created for the demo `iaas-aws`:

```bash
BUCKET_NAME=cct-demo
aws s3 mb s3://$BUCKET_NAME
```

First we validate the template:

```bash
function validate_templates {
    for nested_template in stack/modules/*
    do
        aws cloudformation validate-template --template-body file://$nested_template
    done
    aws cloudformation validate-template --template-body file://stack/root.yaml
}

validate_templates
```

Then, similarly to what we have done in the iaas demo with aws, we use the `package` and `deploy` commands to deploy the root stack with the nested ones:

```bash
function deploy_stack {
    aws cloudformation package \
        --s3-bucket "$BUCKET_NAME" \
        --s3-prefix 'paas' \
        --template-file ./stack/root.yaml \
        --output-template-file packaged-root.yaml

    aws cloudformation deploy \
        --template-file packaged-root.yaml \
        --stack-name demo-cct-paas \
        --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM \
        --parameter-overrides ECRSeedDbLambdaRepository="$SEED_DB_LAMBDA_REPO_URI" ECRGetDataLambdaRepository="$GET_DATA_LAMBDA_REPO_URI"
    
    rm packaged-root.yaml
}

deploy_stack
```

To delete the stack:

```bash
aws cloudformation delete-stack --stack-name demo-cct-paas
aws cloudformation delete-stack --stack-name demo-cct-paas-ecr-repositories
```

---

## DB Initialization

We need to create the accounts table in the database and fill it with sample records. We can do it by running the lambda function, whose ARN is one of the CFN stack's output:

```bash
SEED_DB_LAMBDA_ARN="$(aws cloudformation describe-stacks \
    --stack-name demo-cct-paas \
    --output text \
    --query "Stacks[0].Outputs[?OutputKey == 'SeedDbLambdaArn'].OutputValue")"
```

Run the Lambda with:

```bash
aws lambda invoke --function-name "$SEED_DB_LAMBDA_ARN" response.json
cat response.json && rm response.json
```

---

## Api Gateway

After deploying the stack, we can reach the API Gateway by retrieving its endpoint from the stack output.

```bash
APIGW_ENDPOINT="$(aws cloudformation describe-stacks \
    --stack-name demo-cct-paas \
    --output text \
    --query "Stacks[0].Outputs[?OutputKey == 'ApiGatewayEndpoint'].OutputValue")"
echo "$APIGW_ENDPOINT"
```

Now you can query the API Gateway endpoint at `$APIGW_ENDPOINT/accounts.html`.