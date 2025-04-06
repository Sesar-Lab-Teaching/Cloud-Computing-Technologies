# CloudFormation

AWS CFN (Cloudformation) is the IaC tool provided by AWS. Instead of provisioning resources by hand or using complex scripts, we can define our resources in a declarative file and leverage the flexibility of YAML + CFN template features to organize and easily deploy entire groups of resources.

Let's replicate the scenario with a webserver and the db using CFN templates. We can group resources into different templates and then use [nested stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-nested-stacks.html) to call them from a single stack.

AWS CFN currently has a quite annoying limitation: nested template files must be saved on S3 in order to be used. 

First we need to create a new S3 bucket that will contain the nested templates. 

```bash
BUCKET_NAME=demo-cct1
aws s3 mb s3://$BUCKET_NAME
```

Then we copy our templates (previously validated) in the S3 bucket:

```bash
function upload_templates {
    for child_template in stack/modules/*
    do
        aws cloudformation validate-template --template-body file://$child_template && \
        aws s3 cp $child_template "s3://$BUCKET_NAME/iaas/cfn-templates/$(basename "$child_template")"
    done
}
upload_templates
```

Finally, we can deploy the root stack, which includes the child templates, with:

```bash
aws cloudformation validate-template --template-body file://stack/root.yaml && \
aws cloudformation create-stack \
    --stack-name demo-cct-iaas \
    --template-body file://stack/root.yaml
```

To update the stack:

```bash
upload_templates
aws cloudformation validate-template --template-body file://stack/root.yaml && \
aws cloudformation update-stack \
    --stack-name demo-cct-iaas \
    --template-body file://stack/root.yaml
```

To delete your stack:

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

After creating the stack, the instances can be accessed with SSH:

```bash
ELASTIC_IP="$(aws ec2 describe-addresses \
    --filters "Name=tag:Environment,Values=demo-cct" \
    --query "Addresses[0].PublicIp" \
    --output text)"
ssh -i "demo-key-pair.pem" admin@${ELASTIC_IP}
```