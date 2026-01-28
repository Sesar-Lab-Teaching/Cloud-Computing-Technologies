# CloudFormation

AWS CFN (Cloudformation) is the IaC tool provided by AWS. Instead of provisioning resources by hand or using complex scripts, we can define our resources in a declarative file and leverage the flexibility of YAML + CFN template features to organize and easily deploy entire groups of resources.

Let's replicate the scenario with a webserver and the db using CFN templates. We can group resources into different templates and then use [nested stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html) to call them from a single stack.

AWS CFN currently has a quite annoying limitation: nested template files must be saved on S3 in order to be used. 

First we need to create a new S3 bucket that will contain the nested templates. 

```bash
BUCKET_NAME=cct-demo
aws s3 mb s3://$BUCKET_NAME || echo "Bucket already exists"
```

We first need to validate the templates:

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

Then we use the `package` command to upload the nested templates to the S3 bucket, and `deploy` to deploy the root stack together with the nested ones. Each deploy creates a change set only if the resources have changed.

```bash
function deploy_stack {
    aws cloudformation package \
        --s3-bucket "$BUCKET_NAME" \
        --s3-prefix 'iaas' \
        --template-file ./stack/root.yaml \
        --output-template-file packaged-root.yaml

    aws cloudformation deploy \
        --template-file packaged-root.yaml \
        --stack-name demo-cct-iaas \
        --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_NAMED_IAM \
        --parameter-overrides DbCloudInitConfig="$(cat cloud-init/db.yaml)"
    
    rm packaged-root.yaml
}

deploy_stack
```

To delete the stack:

```bash
aws cloudformation delete-stack --stack-name demo-cct-iaas
```

---

## Networking

In the networking template, we also create a key pair that allows us to SSH into the instances. That private key is stored in the AWS Systems Manager Parameter Store at `/ec2/keypair/key_pair_id`. To retrieve it:

```bash
KEY_PAIR_ID="$(aws ec2 describe-key-pairs \
    --filters Name=key-name,Values=demo-cct-key-pair \
    --query KeyPairs[*].KeyPairId \
    --output text)"

sudo rm -f demo-key-pair.pem
aws ssm get-parameter \
    --name /ec2/keypair/$KEY_PAIR_ID --with-decryption --query Parameter.Value --output text > demo-key-pair.pem
chmod 400 demo-key-pair.pem
```

After creating the stack, the instances can be accessed with SSH using an Elastic IP address (which needs to be created and associated to the instance you want to connect to).

```bash
ELASTIC_IP="$(aws ec2 describe-addresses \
    --filters "Name=tag:Environment,Values=demo-cct" \
    --query "Addresses[0].PublicIp" \
    --output text)"
ssh -i "demo-key-pair.pem" -o IdentitiesOnly=yes admin@${ELASTIC_IP}
```

### NAT Gateway

Instances in a private subnet can access internet only if they are created with a public IP address associated. Without a public IP, we need to deploy an additional [NAT Gateway](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html). 

---

## Load Balancer

The CloudFormation script also includes a load balancer that balance traffic among the registered instances. These instances are added to an autoscaling group: instances associated to this group can scale manually, or using a [dynamic policy](https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html). The listener of the Load balancer is then configured to forward traffic coming from port 80 to one of the registered instances (port 5000) in the autoscaling group.