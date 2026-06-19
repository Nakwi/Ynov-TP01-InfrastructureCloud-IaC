# Ynov TP01 - Infrastructure Cloud IaC

Ce projet permet de deployer deux VM avec Terraform sur Azure ou Proxmox.

- `web` : VM Debian avec Nginx
- `monitoring` : VM Debian avec Docker, prevue pour Uptime Kuma

Le point d'entree recommande est le script Python :

```bash
terraform_assistant.py
```

Il evite de retenir toutes les commandes Terraform et prepare automatiquement une partie des prerequis.

## Arborescence

```text
.
+-- azure/                 # Stack Terraform Azure
+-- Proxmox/               # Stack Terraform Proxmox
+-- ansible/               # Inventaire et playbook Ansible
+-- terraform_assistant.py # Assistant interactif
`-- README.md
```

Les fichiers sensibles ou locaux comme `terraform.tfvars`, `.terraform/` et `terraform.tfstate` sont ignores par Git.

## Prerequis

Sur le poste local :

- Python 3
- Terraform
- OpenSSH (`ssh` et `ssh-keygen`)
- Azure CLI pour Azure
- Ansible uniquement si le poste de controle est Linux

Sur Windows, lance le script avec :

```powershell
py .\terraform_assistant.py
```

ou :

```powershell
python .\terraform_assistant.py
```

Sur Linux, lance le script avec :

```bash
python3 ./terraform_assistant.py
```

Au demarrage, le script demande :

```text
Poste local (W=Windows, L=Linux)
```

- `W` : mode Windows, Ansible est masque
- `L` : mode Linux, les actions Ansible sont disponibles

## Utilisation Rapide

Lance l'assistant :

```bash
python3 ./terraform_assistant.py
```

Puis choisis :

```text
1. Azure
2. Proxmox
0. quitter
```

Chaque stack propose ensuite :

```text
1. terraform init
2. terraform validate
3. terraform plan
4. terraform apply
```

Apres un `terraform apply` reussi, le script tente de recuperer automatiquement les IP des VM et affiche les commandes SSH utiles.

## Parcours Proxmox

Dans le menu principal, choisis `2. Proxmox`.

Le menu Proxmox propose :

```text
1. terraform init
2. terraform validate
3. terraform plan
4. terraform apply
5. preparer Proxmox
```

Commence par `preparer Proxmox`.

Cette action :

- cree ou reutilise une cle SSH locale
- copie la cle SSH sur le compte `root` du node Proxmox
- active SSH sur Proxmox
- prepare le datastore pour les snippets cloud-init
- installe `nmap` sur le node Proxmox
- cree un utilisateur/token API pour Terraform
- met a jour `Proxmox/terraform.tfvars`

Ensuite lance dans l'ordre :

```text
terraform init
terraform validate
terraform plan
terraform apply
```

Apres `terraform apply`, le script cherche les IP avec :

1. QEMU Guest Agent
2. fallback nmap/MAC si besoin

## Parcours Azure

Dans le menu principal, choisis `1. Azure`.

Le menu Azure propose :

```text
1. terraform init
2. terraform validate
3. terraform plan
4. terraform apply
5. preparer Azure
```

Commence par `preparer Azure`.

Cette action :

- cree ou reutilise une cle SSH locale
- verifie Azure CLI
- propose d'installer Azure CLI si elle manque
- lance `az login --use-device-code`
- selectionne la subscription Azure
- detecte ton IP publique en `/32`
- met a jour `azure/terraform.tfvars`

Ensuite lance dans l'ordre :

```text
terraform init
terraform validate
terraform plan
terraform apply
```

Apres `terraform apply`, le script lit les outputs Terraform Azure et affiche :

- IP publique de la VM web
- IP publique de la VM monitoring
- commandes SSH
- URL web
- URL Uptime Kuma

## Ansible

Ansible est affiche seulement si tu choisis `L` au demarrage.

Dans les menus Azure ou Proxmox, tu auras :

```text
generer inventaire Ansible
installer/verifier Ansible
lancer playbook Ansible
```

Le script genere :

```text
ansible/inventaire.ini
```

Puis lance :

```bash
ansible-playbook -i ansible/inventaire.ini ansible/playbook.yaml
```

Sur Windows, Ansible n'est pas propose directement. Utilise Linux ou WSL si tu veux lancer Ansible depuis la meme machine.

## Connexion SSH Aux VM

L'utilisateur par defaut dans les VM est :

```text
admincloud
```

Exemple :

```bash
ssh -i ~/.ssh/tp_azure_ed25519 admincloud@IP_DE_LA_VM
```

Sur la VM monitoring, Docker est installe par cloud-init.

Si `docker ps` refuse l'acces sans sudo, reconnecte-toi :

```bash
exit
ssh -i ~/.ssh/tp_azure_ed25519 admincloud@IP_DE_LA_VM
docker ps
```

Les groupes Linux sont charges au moment de la connexion.

## Erreurs Frequentes

### Python introuvable sur Windows

Utilise plutot :

```powershell
py .\terraform_assistant.py
```

Si `py` manque aussi, installe Python depuis python.org et coche l'option `Add Python to PATH`.

### Azure Resource Providers

Si Linux affiche une erreur pendant l'enregistrement de nombreux providers Azure, le projet desactive l'auto-registration dans :

```text
azure/provider.tf
```

avec :

```hcl
resource_provider_registrations = "none"
```

Si Azure demande quand meme un provider precis :

```bash
az provider register --namespace Microsoft.Resources
az provider register --namespace Microsoft.Network
az provider register --namespace Microsoft.Compute
```

### Connexion Azure coupee

Si Terraform affiche :

```text
HTTP response was nil; connection may have been reset
```

Relance simplement :

```bash
terraform plan
terraform apply
```

Azure peut avoir cree certaines ressources avant la coupure.

### Proxmox ne trouve pas les IP

Attends que les VM finissent leur premier demarrage.

Le script tente automatiquement plusieurs recherches apres `terraform apply`.

Si besoin, verifie dans la console Proxmox que cloud-init est termine :

```bash
cloud-init status --long
```

## Commandes De Secours

Azure :

```bash
cd azure
terraform init
terraform validate
terraform plan
terraform apply
```

Proxmox :

```bash
cd Proxmox
terraform init
terraform validate
terraform plan
terraform apply
```

Ansible sur Linux :

```bash
cd ansible
ansible-playbook -i inventaire.ini playbook.yaml
```

## Ordre Recommande Pour Un TP

1. Lancer `terraform_assistant.py`
2. Choisir `W` ou `L`
3. Choisir Azure ou Proxmox
4. Lancer `preparer Azure` ou `preparer Proxmox`
5. Lancer `terraform init`
6. Lancer `terraform validate`
7. Lancer `terraform plan`
8. Lancer `terraform apply`
9. Si tu es sur Linux, generer l'inventaire Ansible
10. Lancer le playbook Ansible
