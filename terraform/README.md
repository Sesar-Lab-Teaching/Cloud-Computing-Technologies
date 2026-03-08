# Terraform

In this demo, we are going to deploy the reference scenario using one of the most popular IaC tool: Terraform. Terraform relies on plugins called providers to interact with cloud providers, SaaS providers, and other APIs. Providers are distributed separately from Terraform itself and they can be found in the Terraform Registry. The advantage of Terraform is that a deployment can include multiple providers, mixing resources from AWS, GCP, Docker, Azure, and even custom providers, for instance. The providers we use for this demo are the Docker provider and AWS provider; in this way, we can centralize the management of our infrastructure, even if distributed across Docker and AWS. These providers map Docker and AWS resources to Terraform resources, which can be configured using HCL (Hashicorp Configuration Language).

## Initialization

Terraform must first download the plugins you have specified in the `terraform` section:

```bash
terraform init
```

This command creates a `.terraform` folder containing the binaries of necessary plugins. Additionally, the `.terraform.lock.hcl` locks the plugins versions.
To validate the files, run

```bash
# to improve formatting on assignments
terraform fmt -recursive

terraform validate
```

## Plan and Apply

You are ready to deploy your resources. To do a "dry run" and inspect what resources will eventually be created, run:

```bash
terraform plan -var-file cct.tfvars -out first-deploy.tfplan
```

The generated file is not human readable, but you can review it with:

```bash
# add -json option if you need to process it
terraform show first-deploy.tfplan
```

Then deploy the plan:

```bash
terraform apply -var-file cct.tfvars first-deploy.tfplan
```

Terraform stores its current understanding of the state of your resources locally in the `terraform.tfstate` file. Thanks to this state file, subsequent executions of `terraform apply` only apply the delta from the current state to the desired one.

---

## Cleanup

To remove the resources:

```bash
terraform plan -destroy -var-file cct.tfvars -out destroy-all.tfplan
terraform apply -var-file cct.tfvars destroy-all.tfplan
```