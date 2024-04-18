# PaaS with AWS Lambda Functions and RDS

---

AWS offers a quite extensive list of PaaS, two of the most well-known services are Lambda Functions and RDS (Relational Database Service).

Sources:
- [Lambda Functions - Building with Python](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)

## RDS

As opposed to the IaaS deployment, where the database is deployed on an EC2 instance, we can use RDS, a DBaaS service (DataBase-as-a-Service):

<!-- aws ec2 create-vpc \
    --cidr-block 10.0.0.16/28 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=vpc-demo-cct-paas},{Key=Environment,Value=demo-cct-paas}]'
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=tag:Name,Values=vpc-demo-cct-paas" \
    --query "Vpcs[0].VpcId" \
    --output text)
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.0.16/28 \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Environment,Value=demo-cct-paas}]'

# the default security group already allow all traffic generated within the same security group (i.e. by all hosts placed in the same VPC)
SG_ID="$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[*].GroupId" \
    --output text)"
aws ec2 create-tags --resources "$SG_ID" \
    --tags 'Key=Environment,Value=demo-cct-paas'

# but we need a subnet group to place the db instance in the correct subnet
SUBNET_ID="$(aws ec2 describe-subnets \
    --filter "Name=vpc-id,Values=$VPC_ID" \
    --query "Subnets[0].SubnetId" \
    --output text)"
aws rds create-db-subnet-group \
    --db-subnet-group-name subnet-group-demo-cct-paas \
    --db-subnet-group-description "Subnet group for the PaaS demo" \
    --tags 'Key=Environment,Value=demo-cct-paas' \
    --subnet-ids "$SUBNET_ID" -->

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

<!-- aws lambda update-function-configuration \
    --function-name "$LAMBDA_NAME" \
    --vpc-config "$(cat <<-EOF
        {
            "SubnetIds": $SUBNET_IDS,
            "SecurityGroupIds": $SEC_GROUP_IDS
        }
EOF
    )"-->

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
                "MYSQL_DB": "$MYSQL_DATABASE",
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
SUBNET_ID="$()"
docker tag "$LAMBDA_NAME:1.0.0" "$REPOSITORY_ID:latest"
docker push "$REPOSITORY_ID:latest"
aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --package-type Image \
    --environment "$(cat <<-EOF
        {
            "Variables": {
                "MYSQL_HOST": "$DB_ENDPOINT",
                "MYSQL_USER": "$MYSQL_MASTER_USERNAME",
                "MYSQL_PASSWORD": "$MYSQL_MASTER_PASSWORD",
                "MYSQL_DB": "$MYSQL_DATABASE",
                "MYSQL_PORT": "$MYSQL_PORT"
            }
        }
EOF
    )" \
    --timeout 30 \
    --tags "Key=Environment,Value=demo-cct-paas" \
    --code "ImageUri=$REPOSITORY_ID:latest" \
    --role "$ROLE_ARN"
```