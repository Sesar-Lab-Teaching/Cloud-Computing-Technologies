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
        --parameter-overrides DbCloudInitConfig="$(cat cloud-init/db.yaml)" WebServerCloudInitConfig="$(cat cloud-init/webserver.yaml)"
    
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
    --filters Name=key-name,Values=demo-cct-iaas-key-pair \
    --query KeyPairs[*].KeyPairId \
    --output text)"

sudo rm -f demo-key-pair.pem
aws ssm get-parameter \
    --name /ec2/keypair/$KEY_PAIR_ID --with-decryption --query Parameter.Value --output text > demo-key-pair.pem
chmod 400 demo-key-pair.pem
```

After creating the stack, the webserver instance can be accessed with SSH using the assigned IP address. The db instance can only be accessed using an EC2 instance Connect Endpoint, already provisioned through the networking stack.

Find the public IP associated to the first web-server instance:

```bash
WEBSERVER_IP="$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=demo-cct-iaas-webserver-instance" \
    --query "Reservations[0].Instances[0].NetworkInterfaces[0].Association.PublicIp" \
    --output text)"
ssh -i "demo-key-pair.pem" -o IdentitiesOnly=yes ubuntu@${WEBSERVER_IP}
```

---

## Access the Webserver

We can access the webserver directly from the public IP address, but the optimal access point is the Load balancer, so that it takes care of distributing the load among the registered instances. To retrieve the Load balancer endpoint:

```bash
LOAD_BALANCER_ENDPOINT="$(aws cloudformation describe-stacks \
    --stack-name demo-cct-iaas \
    --output text \
    --query "Stacks[0].Outputs[?OutputKey == 'LoadBalancerDNSName'].OutputValue")"
echo "$LOAD_BALANCER_ENDPOINT"
```

Send an HTTP request to `LOAD_BALANCER_ENDPOINT` to see the response from the webserver

---

## Trigger a Scale out

The auto scaling group is configured to allow up to 3 instances of the webserver. The instances scales out automatically thanks to the dynamic scaling policy (Target-Tracking scaling). The target value for the scaling policy is 10 requests per target (per instance) in a 1 minute period. If the load balancer receives too many requests and the average number of requests received by each instance is more than 10, one ore more new instances are deployed. This behaviour works in the opposite direction as well: if the number of instances is too high, i.e. they are underloaded considering the low number of requests, some instances might be destroyed.

To trigger a scale out, we can continuously send requests to the load balancer:

```bash
for ((i=0; ;i++))
do
    echo "$i ... Sending HTTP request to load balancer"
    curl --output /dev/null -s "$LOAD_BALANCER_ENDPOINT"
    echo "$i ... request received"
    sleep 1
done
```

After a while (aws is quite conservative on spawning new instance, it first needs to make sure that is not just a network peak), three instances will be deployed in the target group and the load balancer will distribute requests across all the available instances, in both AZ zones (`PublicSubnet2` and `PublicSubnet2`). If you stop the script, the target group scales in after some time.