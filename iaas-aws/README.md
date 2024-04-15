# IaaS with AWS

In this guide we are going to deploy the scenario on EC2, leveraging load balancing and scaling features. To follow the rest of the guide, you need an AWS account.

---

## Install AWS CLI

[AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) is the command line tool for AWS and can be installed with:

```
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

---

## Configuration

AWS CLI must be configured with the credentials necessary to access the AWS APIs. If you don't have an access key yet, from the AWS Console, go to *IAM* > *Users* and select your user > *Security credentials* > *Create access key*. Then, in the shell:

```
aws configure
```

and complete the configuration with the information requested (access key, secret, default region and default output).

---

## Networking

To deploy the scenario, we need 2 VMs, one for the web server and one for the mysql instance. To make these VMs communicate, we can put them in a VPC (Virtual Private Cloud) and allocate a public IP address to make the web server publically available.

First, we can create a VPC:

```
aws ec2 create-vpc \
    --cidr-block 10.0.0.0/28 \
    --tag-specifications 'ResourceType=vpc,Tags=[{Key=Environment,Value=demo-cct}]'
```

and a subnet. However, the subnet requires the vpc-id, which we can query with:

```
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=tag:Environment,Values=demo-cct" \
    --query "Vpcs[*].VpcId" \
    --output text)
```

Note: each command usually returns an output that you can query with the `--query` option and format with the `--output` option. Now that we have the vpc ID, we can create the subnet:

```
aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.0.0/28 \
    --tag-specifications 'ResourceType=subnet,Tags=[{Key=Environment,Value=demo-cct}]'
```

Resources may need to connect to the internet, and this is possible with a internet gateway:

```
aws ec2 create-internet-gateway \
    --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Environment,Value=demo-cct}]'
INTERNET_GATEWAY_ID=$(aws ec2 describe-internet-gateways \
    --filters "Name=tag:Environment,Values=demo-cct" \
    --query "InternetGateways[*].InternetGatewayId" \
    --output text)
aws ec2 attach-internet-gateway \
    --internet-gateway-id "$INTERNET_GATEWAY_ID" \
    --vpc-id "$VPC_ID"
ROUTE_TABLE_ID="$(aws ec2 describe-route-tables \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "RouteTables[*].RouteTableId" \
    --output text)"
aws ec2 create-route --route-table-id "$ROUTE_TABLE_ID" --destination-cidr-block 0.0.0.0/0 --gateway-id "$INTERNET_GATEWAY_ID"
```

Instances are by default secured, i.e. they do not allow any inbound traffic from the internet, but only outbound traffic. We can modify this behaviour using security groups, by softening the default rules:

```
SG_ID="$(aws ec2 describe-security-groups \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[*].GroupId" \
    --output text)"
aws ec2 create-tags --resources "$SG_ID" \
    --tags 'Key=Environment,Value=demo-cct'
# create rule for SSH connections
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 22 \
    --cidr 0.0.0.0/0 \
    --tag-specifications 'ResourceType=security-group-rule,Tags=[{Key=Environment,Value=demo-cct}]'
```

---

## Computing

Before creating the instance, we need a key pair, which can be used to access the instances through SSH:

```
aws ec2 create-key-pair \
    --key-name demo-keypair \
    --query 'KeyMaterial' \
    --output text \
    --tag-specifications 'ResourceType=key-pair,Tags=[{Key=Environment,Value=demo-cct}]' > demo_keypair.pem
chmod 400 "demo_keypair.pem"
```

Now we can create the instances. First we define a launch template, which contains all the parameters to create an instance. Starting from the mysql server:

```
SUBNET_ID="$(aws ec2 describe-subnets \
    --filters "Name=tag:Environment,Values=demo-cct" \
    --query "Subnets[*].SubnetId" \
    --output text)"
# user-data must be written using base64 format
PING_CHECK="while ! ping -c 1 -W 5 8.8.8.8; do echo \"Internet unreachable\"; done ;"
curl https://raw.githubusercontent.com/Sesar-Lab-Teaching/Cloud-Computing-Technologies/4a3e704817243249c8da509c9ddc38fefc629b50/iaas-openstack/provision-db.sh | sed -e "2 i $PING_CHECK" | base64 -w 0 > provision-db.txt

# build the template for the mysql instance
cat <<EOF > mysql_launch_template.json
{
    "NetworkInterfaces": [{
        "AssociatePublicIpAddress": true,
        "DeviceIndex": 0,
        "SubnetId": "$SUBNET_ID",
        "Groups": ["$SG_ID"]
    }],
    "ImageId": "ami-023adaba598e661ac",
    "InstanceType": "t2.small",
    "KeyName": "demo-keypair",
    "TagSpecifications": [{
        "ResourceType": "instance",
        "Tags": [{
            "Key":"Environment",
            "Value":"demo-cct"
        },
        {
            "Key":"Name",
            "Value":"mysql-instance"
        }]
    }],
    "Monitoring": {
        "Enabled": true
    },
    "UserData": "$(cat provision-db.txt)"
}
EOF

# delete the launch template if exists, then (re)create it
if [[ $(aws ec2 describe-launch-templates --filters "Name=tag:Environment,Values=demo-cct" --query "length(LaunchTemplates[?LaunchTemplateName==\`mysql-template\`])") -eq 1 ]]
then
    aws ec2 delete-launch-template --launch-template-name mysql-template
fi
aws ec2 create-launch-template \
    --launch-template-name mysql-template \
    --tag-specifications 'ResourceType=launch-template,Tags=[{Key=Environment,Value=demo-cct}]' \
    --launch-template-data file://mysql_launch_template.json

# run the instance
aws ec2 run-instances \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Environment,Value=demo-cct}]' \
    --launch-template LaunchTemplateName=mysql-template \
    --count 1
```

The only allowed connection is through ssh:

```
MYSQL_IP_ADDRESS="$(aws ec2 describe-instances \
    --filters "Name=tag:Environment,Values=demo-cct" "Name=tag:Name,Values=mysql-instance" \
    --query "Reservations[*].Instances[?State.Name==\`running\`].NetworkInterfaces[0].Association.PublicIp" \
    --output text)"
ssh -i demo_keypair.pem ubuntu@$MYSQL_IP_ADDRESS
```
We can do the same for the webserver, but we also need to create a rule in the security group to make sure the webserver is reachable (on port 5000) from the internet. For simplicity, we add the rule to the default security group, which is shared with the mysql instance as well, but the right approach would be craeting a separate security group with this rule and associate it exclusively to the webserver instance:

```
aws ec2 authorize-security-group-ingress \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 5000 \
    --cidr 0.0.0.0/0 \
    --tag-specifications 'ResourceType=security-group-rule,Tags=[{Key=Environment,Value=demo-cct}]'
```

Now we can create the webserver:

```
MYSQL_PRIVATE_IP_ADDRESS="$(aws ec2 describe-instances \
    --filters "Name=tag:Environment,Values=demo-cct" "Name=tag:Name,Values=mysql-instance" \
    --query "Reservations[*].Instances[?State.Name==\`running\`].NetworkInterfaces[0].PrivateIpAddress" \
    --output text)"
curl https://raw.githubusercontent.com/Sesar-Lab-Teaching/Cloud-Computing-Technologies/4a3e704817243249c8da509c9ddc38fefc629b50/iaas-openstack/provision-webserver.sh | sed \
    -e "2 i $PING_CHECK" \
    -e 's/curl -O http:\/\/169.254.169.254\/openstack\/latest\/meta_data.json//g' \
    -e "s/DB_IP_ADDRESS=.*$/DB_IP_ADDRESS=$MYSQL_PRIVATE_IP_ADDRESS/g" \
     | base64 -w 0 > provision-webserver.txt

# build the template for the webserver
cat <<EOF > webserver_launch_template.json
{
    "NetworkInterfaces": [{
        "AssociatePublicIpAddress": true,
        "DeviceIndex": 0,
        "SubnetId": "$SUBNET_ID",
        "Groups": ["$SG_ID"]
    }],
    "ImageId": "ami-023adaba598e661ac",
    "InstanceType": "t2.small",
    "KeyName": "demo-keypair",
    "TagSpecifications": [{
        "ResourceType": "instance",
        "Tags": [{
            "Key":"Environment",
            "Value":"demo-cct"
        },
        {
            "Key":"Name",
            "Value":"webserver-instance"
        }]
    }],
    "Monitoring": {
        "Enabled": true
    },
    "UserData": "$(cat provision-webserver.txt)"
}
EOF

# delete the launch template if exists, then (re)create it
if [[ $(aws ec2 describe-launch-templates --filters "Name=tag:Environment,Values=demo-cct" --query "length(LaunchTemplates[?LaunchTemplateName==\`webserver-template\`])") -eq 1 ]]
then
    aws ec2 delete-launch-template --launch-template-name webserver-template
fi
aws ec2 create-launch-template \
    --launch-template-name webserver-template \
    --tag-specifications 'ResourceType=launch-template,Tags=[{Key=Environment,Value=demo-cct}]' \
    --launch-template-data file://webserver_launch_template.json

# run the instance
aws ec2 run-instances \
    --tag-specifications 'ResourceType=instance,Tags=[{Key=Environment,Value=demo-cct}]' \
    --launch-template LaunchTemplateName=webserver-template \
    --count 1
```

And can be accessed with SSH:

```
WEBSERVER_IP_ADDRESS="$(aws ec2 describe-instances \
    --filters "Name=tag:Environment,Values=demo-cct" "Name=tag:Name,Values=webserver-instance" \
    --query "Reservations[*].Instances[?State.Name==\`running\`].NetworkInterfaces[0].Association.PublicIp" \
    --output text)"
ssh -i demo_keypair.pem ubuntu@$WEBSERVER_IP_ADDRESS
```

---

## Elastic IP

Instead of using a generic public IP address, we can create an Elastic IP address, which is fixed and can be associated or dissociated to a running instance. In this way the final user can reference a fixed IP address even if the instance is shut down and recreated (with a different IP):

```
aws ec2 allocate-address \
    --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Environment,Value=demo-cct}]'
```

In the output, the `PublicIp` field specifies the public IP address. To see all the available Elastic IPs, run `aws ec2 describe-addresses`.

Then we can associate it to a running instance:

```
# associate the elastic ip created before
EIP_ALLOCATION_ID="$(aws ec2 describe-addresses \
    --filters "Name=tag:Environment,Values=demo-cct" \
    --query "Addresses[0].AllocationId" \
    --output text)"
INSTANCE_ID="$(aws ec2 describe-instances \
    --filters "Name=tag:Environment,Values=demo-cct" "Name=tag:Name,Values=my-instance" \
    --query "Reservations[0].Instances[0].InstanceId" \
    --output text)"
aws ec2 associate-address \
    --allocation-id "$EIP_ALLOCATION_ID" \
    --instance-id "$INSTANCE_ID"
```

---










