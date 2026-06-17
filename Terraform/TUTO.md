# Introduction

1. Structure du dossier Terraform

Terraform/
├───azure/
|   └───azure.tf
└───proxmox/
    ├───main.tf
    ├───provider.tf
    ├───terraform.tfvars
    └───variables.tf

2. Que fait Terraform?

Terraform va créer une VM a partir d'une template pré-existante. Terraform n'est pas capable de créer une VM de rien il faut donc une template avant obligatoirement.

3. Commandes

```bash
# Initialisation du Terraform
cd ./Terraform
terraform init
```

```bash
terraform plan
```

```bash
terraform apply
```

```bash
terraform destroy
```

```bash

```