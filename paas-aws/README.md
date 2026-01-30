# PaaS with AWS Lambda Functions, RDS and API Gateway

---

AWS offers a quite extensive list of PaaS, two of the most well-known services are Lambda Functions and RDS (Relational Database Service).

Sources:
- [Lambda Functions - Building with Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)

## RDS

As opposed to the IaaS deployment, where the database is deployed on an EC2 instance, we can use RDS, a DBaaS service (DataBase-as-a-Service):

A DB instance can be built with:

```
MYSQL_PORT=3306
MYSQL_DATABASE=accounts
MYSQL_MASTER_USERNAME=democct
MYSQL_MASTER_PASSWORD=demo-cct-password
aws rds create-db-instance \
    --db-name "$MYSQL_DATABASE" \
    --db-instance-identifier demo-cct-db \
    --db-instance-class db.t3.small \
    --port "$MYSQL_PORT" \
    --engine mysql \
    --no-publicly-accessible \
    --master-username "$MYSQL_MASTER_USERNAME" \
    --tags "Key=Environment,Value=demo-cct-paas" \
    --master-user-password "$MYSQL_MASTER_PASSWORD" \
    --allocated-storage 20
DB_ENDPOINT="$(aws rds describe-db-instances \
    --db-instance-identifier "demo-cct-db" \
    --query "DBInstances[0].Endpoint.Address" \
    --output text)"
```

Note: the database has been created in the default VPC, but a user-defined VPC is the best practice. For a more complete guide, read [here](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_SettingUp.html#CHAP_SettingUp.Requirements)

---

## Lambda Functions

Lambda Functions is a compute service that allows you to run code without provisioning or managing servers. You upload your code, and the Cloud provider takes care of running and scaling it for you. However, the adoption of a Lambda Function requires small changes on the webserver source code, which must always include a [handler](https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html).

### Lambda for DB seeding

The Lambda [`lambda_seed_db.py`](src/lambda_seed_db.py) can be deployed as a Docker image:

```
cd src
LAMBDA_NAME=demo-cct-lambda-seed-db
docker build --platform linux/amd64 -t "$LAMBDA_NAME:1.0.0" -f Dockerfile.lambda_seed_db .
```

Next we need to authenticate our Docker client with ECR and create a new repository:

```
ACCOUNT_ID="$(aws sts get-caller-identity \
    --query Account \
    --output text)"
REGION="$(aws configure get region)"
aws ecr get-login-password | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
aws ecr create-repository \
    --repository-name "$LAMBDA_NAME" \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability MUTABLE \
    --tags "Key=Environment,Value=demo-cct-paas"
REPOSITORY_ID="$(aws ecr describe-repositories \
    --repository-names "$LAMBDA_NAME" \
    --query "repositories[0].repositoryUri" \
    --output text)"
```

And deploy the image on the repository:

```
docker tag "$LAMBDA_NAME:1.0.0" "$REPOSITORY_ID:latest"
docker push "$REPOSITORY_ID:latest"
```

Now that the image has been pushed on AWS, we need to authorize the Lambda Function that we will create to perform the basic operations (like writing on Cloudwatch):

```
aws iam create-role \
    --role-name role-demo-cct \
    --tags "Key=Environment,Value=demo-cct-paas" \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [
            { 
                "Effect": "Allow", 
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                }, 
                "Action": "sts:AssumeRole"
            }
        ]
    }'
aws iam attach-role-policy \
    --role-name role-demo-cct \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
# necessary because the lambda is connected to a VPC
aws iam attach-role-policy \
    --role-name role-demo-cct \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole
ROLE_ARN="$(aws iam list-roles \
    --query "Roles[?RoleName==\`role-demo-cct\`].Arn" \
    --output text)"
```

Then create the Lambda Function and associate it to the role just defined:

```
SUBNET_IDS="$(aws rds describe-db-instances \
    --db-instance-identifier demo-cct-db \
    --query "DBInstances[0].DBSubnetGroup.Subnets[*].SubnetIdentifier" \
    --output json
)"
SEC_GROUP_IDS="$(aws rds describe-db-instances \
    --db-instance-identifier demo-cct-db \
    --query "DBInstances[0].VpcSecurityGroups[*].VpcSecurityGroupId" \
    --output json
)"
aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --package-type Image \
    --environment "$(cat <<-EOF
        {
            "Variables": {
                "MYSQL_HOST": "$DB_ENDPOINT",
                "MYSQL_USER": "$MYSQL_MASTER_USERNAME",
                "MYSQL_PASSWORD": "$MYSQL_MASTER_PASSWORD",
                "MYSQL_DATABASE": "$MYSQL_DATABASE",
                "MYSQL_PORT": "$MYSQL_PORT"
            }
        }
EOF
    )" \
    --vpc-config "$(cat <<-EOF
        {
            "SubnetIds": $SUBNET_IDS,
            "SecurityGroupIds": $SEC_GROUP_IDS
        }
EOF
    )" \
    --timeout 30 \
    --tags "Key=Environment,Value=demo-cct-paas" \
    --code "ImageUri=$REPOSITORY_ID:latest" \
    --role "$ROLE_ARN"
```

To verify that the Lambda Function is working, we can call it with:

```
aws lambda wait function-active --function-name "$LAMBDA_NAME"
aws lambda invoke --function-name "$LAMBDA_NAME" response.json
```

---


### Lambda for Accounts retrieval

The procedure for the Lambda [`lambda_retrieve_accounts.py`](src/lambda_retrieve_accounts.py) is very similar, but we skip the role creation (as the role can be shared between the two lambdas):

```
cd src
LAMBDA_NAME=demo-cct-lambda-retrieve-accounts
docker build --platform linux/amd64 -t "$LAMBDA_NAME:1.0.0" -f Dockerfile.lambda_retrieve_accounts .
```

Next we need to authenticate our Docker client with ECR and create a new repository:

```
ACCOUNT_ID="$(aws sts get-caller-identity \
    --query Account \
    --output text)"
REGION="$(aws configure get region)"
aws ecr get-login-password | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
aws ecr create-repository \
    --repository-name "$LAMBDA_NAME" \
    --image-scanning-configuration scanOnPush=true \
    --image-tag-mutability MUTABLE \
    --tags "Key=Environment,Value=demo-cct-paas"
REPOSITORY_ID="$(aws ecr describe-repositories \
    --repository-names "$LAMBDA_NAME" \
    --query "repositories[0].repositoryUri" \
    --output text)"
```

And deploy the image on the repository:

```
docker tag "$LAMBDA_NAME:1.0.0" "$REPOSITORY_ID:latest"
docker push "$REPOSITORY_ID:latest"
SUBNET_IDS="$(aws rds describe-db-instances \
    --db-instance-identifier demo-cct-db \
    --query "DBInstances[0].DBSubnetGroup.Subnets[*].SubnetIdentifier" \
    --output json
)"
SEC_GROUP_IDS="$(aws rds describe-db-instances \
    --db-instance-identifier demo-cct-db \
    --query "DBInstances[0].VpcSecurityGroups[*].VpcSecurityGroupId" \
    --output json
)"
aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --package-type Image \
    --environment "$(cat <<-EOF
        {
            "Variables": {
                "MYSQL_HOST": "$DB_ENDPOINT",
                "MYSQL_USER": "$MYSQL_MASTER_USERNAME",
                "MYSQL_PASSWORD": "$MYSQL_MASTER_PASSWORD",
                "MYSQL_DATABASE": "$MYSQL_DATABASE",
                "MYSQL_PORT": "$MYSQL_PORT"
            }
        }
EOF
    )" \
    --vpc-config "$(cat <<-EOF
        {
            "SubnetIds": $SUBNET_IDS,
            "SecurityGroupIds": $SEC_GROUP_IDS
        }
EOF
    )" \
    --timeout 30 \
    --tags "Key=Environment,Value=demo-cct-paas" \
    --code "ImageUri=$REPOSITORY_ID:latest" \
    --role "$ROLE_ARN"

# authorize the api gateway to call the lambda function
aws lambda add-permission \
    --function-name "$LAMBDA_NAME" \
    --statement-id authorize-apigateway \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com

```

---

## API Gateway

Up to now, the Lambda Functions are callable only by the authorized IAM users. To expose them through HTTP APIs, we can create an API Gateway and integrate it with the Lambda Functions.

```
LAMBDA_NAME=demo-cct-lambda-retrieve-accounts
REGION="$(aws configure get region)"
LAMBDA_ARN="$(aws lambda get-function \
    --function-name "$LAMBDA_NAME" \
    --query 'Configuration.FunctionArn' \
    --output text
)"

aws apigateway create-rest-api \
    --name apigw-demo-cct \
    --tags "Key=Environment,Value=demo-cct-paas"
REST_API_ID="$(aws apigateway get-rest-apis \
    --query "items[?name==\`apigw-demo-cct\`].id" \
    --output text
)"
RESOURCE_ID="$(aws apigateway get-resources \
    --rest-api-id "$REST_API_ID" \
    --query "items[0].id" \
    --output text
)"
aws apigateway put-method \
    --rest-api-id "$REST_API_ID" \
    --resource-id "$RESOURCE_ID" \
    --http-method GET \
    --authorization-type "NONE"
aws apigateway put-method-response \
    --rest-api-id "$REST_API_ID" \
    --resource-id "$RESOURCE_ID" \
    --http-method GET \
    --response-parameters '{"method.response.header.Content-Type": false}' \
    --status-code 200
aws apigateway put-integration \
    --rest-api-id "$REST_API_ID" \
    --resource-id "$RESOURCE_ID" \
    --http-method GET \
    --type AWS \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${LAMBDA_ARN}/invocations"
aws apigateway put-integration-response \
    --rest-api-id "$REST_API_ID" \
    --resource-id "$RESOURCE_ID" \
    --http-method GET \
    --status-code 200 \
    --selection-pattern "" \
    --response-parameters "{\"method.response.header.Content-Type\": \"'text/html'\"}" \
    --response-templates '{"text/html": "$input.path(\"$\")"}'
aws apigateway create-deployment --rest-api-id "$REST_API_ID" --stage-name demo-cct
```

---

## Orchestration with Cloudformation

Scripting all the AWS commands is a first form of IaC (Infrastructure as Code), but AWS provides a more efficient way to do that: Cloudformation. It is an orchestration service that allows us to manage an entire infrastructure (or just a part of it) using template files. These files should be versioned and contain the description of how the resources should be created and initialized. The main benefits offered by AWS Cloudformation are:

- Scripting < Cloudformation because Cloudformation is a declarative language, far easier to understand and more efficient
- Automate the creation/disposal of entire stacks of resources
- Resource management is versioned
- Template cost estimation (`aws cloudformation estimate-template-cost`)

For example, we can create a Cloudformation file for the API Gateway configuration, which includes several API calls.

First, we should validate it with:

```
aws cloudformation validate-template \
    --template-body file://api_gw_template.yml
```

Then we can create it:

```
LAMBDA_NAME=demo-cct-lambda-retrieve-accounts
LAMBDA_ARN="$(aws lambda get-function \
    --function-name "$LAMBDA_NAME" \
    --query 'Configuration.FunctionArn' \
    --output text
)"
aws cloudformation create-stack \
    --template-body file://api_gw_template.yml \
    --stack-name stack-api-gw-demo-cct \
    --parameters "ParameterKey=RetrieveAccountLambdaArn,ParameterValue=$LAMBDA_ARN"
```

And delete it with:

```
aws cloudformation delete-stack \
    --stack-name stack-api-gw-demo-cct
```

---

## Monitoring

The output of the Stack deployment specifies the API Gateway endpoint that the customer should use to access the implemented REST APIs. To verify that the Lambda Function is eventually called, we can test an API request from the AWS console or using the CLI command `aws apigateway test-invoke-method`. The alternative is monitoring the logs and metrics from Cloudwatch. By default, the available metrics are:

- Invocations
- Duration
- Errors
- Throttles
