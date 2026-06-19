# Ynov TP01 - Infrastructure Cloud IaC

Projet d'Infrastructure as Code (Master 1 Cloud, Sécurité & Infrastructure — Ynov). Il déploie
une infrastructure web complète, de bout en bout et sans intervention manuelle, indifféremment
sur **Proxmox** ou sur **Azure**, à partir du même socle.

Deux machines virtuelles sont créées :

- `web` : VM Debian avec **Nginx** (service public)
- `monitoring` : VM Debian avec **Docker** + **Uptime Kuma** (supervision)

Le point d'entrée recommandé est le script Python, qui orchestre toute la chaîne :

```bash
python3 ./terraform_assistant.py
```

Quatre briques se passent le relais : **cloud-init** (amorçage), **Terraform** (provisionnement),
**Ansible** (configuration), le tout piloté par le **script Python**.

## Démonstrations
 
Deux vidéos montrent un déploiement complet de bout en bout :
 
- **Démo Azure** : https://youtu.be/wgGb3_AWmtE
- **Démo Proxmox** : https://youtu.be/dpfslmvEur4


## Vue d'ensemble : comment tout fonctionne ensemble

| Machine | Rôle | Service | Exposition |
| ------- | ---- | ------- | ---------- |
| `web` | Service public | Nginx (page statique) | Publique (port 80) |
| `monitoring` | Supervision | Uptime Kuma via Docker | Restreinte (port 3001) |

Le cycle complet d'un déploiement :

```
   Script Python  (terraform_assistant.py)
        │
        ▼
   Terraform ───────────────► crée les VM (Proxmox OU Azure) + réseau + disques
        │                      et attache la configuration cloud-init
        ▼
   cloud-init (au 1er boot) ─► crée l'utilisateur admincloud, injecte la clé SSH,
        │                      installe les paquets de base (et Docker sur monitoring)
        ▼
   Script Python ───────────► récupère les IP des VM et génère l'inventaire Ansible
        │
        ▼
   Ansible (SSH) ───────────► configure Nginx (web) et déploie Uptime Kuma (monitoring)
```

La clé SSH sert de fil conducteur : sa partie publique est injectée par Terraform dans
cloud-init, sa partie privée est utilisée par Ansible pour se connecter.

## Arborescence

```text
.
├── azure/                    # Stack Terraform Azure
├── Proxmox/                  # Stack Terraform Proxmox
├── ansible/                  # Inventaire et playbook Ansible
├── terraform_assistant.py    # Assistant interactif (point d'entrée)
└── README.md
```

Les fichiers sensibles ou locaux (`terraform.tfvars`, `.terraform/`, `terraform.tfstate`, clés
privées) sont ignorés par Git.

## Prérequis

Sur le poste local :

- Python 3
- Terraform
- OpenSSH (`ssh` et `ssh-keygen`)
- Azure CLI pour Azure
- Ansible uniquement si le poste de contrôle est Linux (Ansible ne fonctionne pas comme control
  node depuis Windows natif)

Sur Windows, lance le script avec :

```powershell
py .\terraform_assistant.py
```

Sur Linux :

```bash
python3 ./terraform_assistant.py
```

Au démarrage, le script demande :

```text
Poste local (W=Windows, L=Linux)
```

- `W` : mode Windows, les actions Ansible sont masquées
- `L` : mode Linux, les actions Ansible sont disponibles

## Utilisation rapide

Lance l'assistant, puis choisis le fournisseur :

```text
1. Azure
2. Proxmox
0. quitter
```

Chaque stack propose ensuite `terraform init / validate / plan / apply`, la préparation
(Azure ou Proxmox), et — en mode Linux — la génération de l'inventaire et le lancement d'Ansible.
Après un `apply` réussi, le script récupère automatiquement les IP des VM et affiche les
commandes SSH utiles.

---

## Fonctionnement détaillé

### 1. Le script Python - `terraform_assistant.py`

C'est l'orchestrateur du projet. Il n'utilise que la bibliothèque standard de Python et pilote
les commandes externes déjà nécessaires (`terraform`, `ssh`, `ssh-keygen`, `ansible-playbook`).
Il évite de retenir toutes les commandes Terraform et prépare automatiquement une partie des
prérequis.

#### Menus

Menu principal :

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
5. préparer (Azure ou Proxmox)
...
```

En mode Linux, des actions Ansible s'ajoutent : générer l'inventaire, installer/vérifier Ansible,
lancer le playbook. Après un `terraform apply` réussi, le script tente de récupérer
automatiquement les IP des VM et affiche les commandes SSH utiles.

#### Parcours Proxmox

Choisis `2. Proxmox`, puis commence par **préparer Proxmox**. Cette action :

- crée ou réutilise une clé SSH locale ;
- copie la clé SSH sur le compte `root` du node Proxmox et active SSH ;
- prépare le datastore pour les snippets cloud-init ;
- installe `nmap` sur le node (pour le fallback de détection d'IP) ;
- crée un utilisateur/token API pour Terraform ;
- met à jour `Proxmox/terraform.tfvars`.

Ensuite : `init` → `validate` → `plan` → `apply`. Après l'apply, le script cherche les IP via le
**QEMU Guest Agent**, avec un **fallback nmap/MAC** si l'agent n'est pas encore prêt.

#### Parcours Azure

Choisis `1. Azure`, puis commence par **préparer Azure**. Cette action :

- crée ou réutilise une clé SSH locale ;
- vérifie l'Azure CLI (propose de l'installer si absente) ;
- lance `az login --use-device-code` et sélectionne la subscription ;
- détecte ton IP publique en `/32` ;
- met à jour `azure/terraform.tfvars`.

Ensuite : `init` → `validate` → `plan` → `apply`. Après l'apply, le script lit les **outputs
Terraform** (IP publiques connues car allouées en `Static`) et affiche les IP, les commandes SSH
et les URLs (web et Uptime Kuma).

#### Sous le capot

L'intérêt du script est de transformer une suite d'étapes manuelles (préparer le node, appliquer
Terraform, retrouver les IP, écrire l'inventaire, lancer Ansible) en un workflow guidé et
reproductible, identique pour les deux fournisseurs. La découverte d'IP est ce qui permet
l'**inventaire Ansible dynamique** (le bonus du sujet) : guest-agent/scan pour Proxmox, outputs
Terraform pour Azure.

### 2. Terraform - Proxmox

Stack basée sur le provider **`bpg/proxmox`** (`~> 0.110`). L'authentification se fait par
**token API** (jamais le compte root), et un bloc `ssh` permet au provider de déposer les
snippets cloud-init sur le nœud (opération qui passe par SSH et non par l'API).

Le `main.tf` déroule trois étapes :

1. **Téléchargement de l'image** (`proxmox_download_file`) : récupère l'image cloud Debian 13
   (`debian-13-genericcloud`) dans le datastore.
2. **Upload des snippets cloud-init** (`proxmox_virtual_environment_file`) : chaque fichier
   cloud-init est rendu par `templatefile()` (qui remplace `${ssh_public_key}` par la vraie clé)
   puis déposé en snippet.
3. **Création des VM** (`proxmox_virtual_environment_vm`) : une seule ressource gère les deux VM
   via un `for_each` sur la map `vm_definitions` (web, monitoring). Chaque VM importe son disque
   depuis l'image, active le QEMU Guest Agent, branche sa carte réseau sur le bridge, et reçoit
   sa cloud-init via `user_data_file_id` qui **référence le snippet** (ce qui garantit aussi le
   bon ordre de création).

L'IP est envoyée à cloud-init via `ip_config` (DHCP par défaut, statique possible avec une
`precondition` exigeant alors une gateway). Les `outputs` exposent les IDs, les IP, les commandes
SSH et les URLs.

### 3. Terraform - Azure

Stack basée sur le provider **`azurerm`** ; l'authentification repose sur l'Azure CLI
(`az login`, géré par « préparer Azure »).

Le `main.tf` crée :

- un **groupe de ressources**, un **réseau virtuel**, un **sous-réseau** ;
- deux **NSG** : la VM web autorise le SSH depuis `admin_ip_cidr` et le HTTP (80) publiquement ;
  la VM monitoring autorise le SSH et le port Uptime Kuma (3001) depuis `admin_ip_cidr` ;
- deux **IP publiques** en `Static`, associées à deux **cartes réseau** ;
- deux **VM Debian 13** (`gen2`), authentification par clé uniquement
  (`disable_password_authentication = true`). cloud-init est injecté via
  `custom_data = base64encode(templatefile(...))`, la clé publique via `admin_ssh_key`.

Deux variables sont **obligatoires** dans `azure/terraform.tfvars` : `subscription_id` et
`admin_ip_cidr` (renseignées automatiquement par « préparer Azure »).

### 4. cloud-init

cloud-init amorce chaque VM **au premier démarrage**, pour la rendre joignable et administrable.
C'est un amorçage minimal ; la configuration applicative est laissée à Ansible.

Socle commun :

- utilisateur **`admincloud`** (sudo sans mot de passe) ;
- **clé SSH publique** injectée via `${ssh_public_key}`, valeur remplie par Terraform au moment
  du `apply` (jamais en clair dans le dépôt) ;
- fuseau horaire, mise à jour des paquets, fichier témoin de fin d'exécution.

Spécificités :

- **web** : installe `python3-apt` (pour Ansible), `qemu-guest-agent` (IP côté Proxmox) et
  `nginx` (configuré ensuite par Ansible).
- **monitoring** : installe Docker depuis le dépôt officiel, pour héberger Uptime Kuma.

Côté Proxmox le fichier rendu est déposé en snippet (`user_data_file_id`) ; côté Azure il est
passé en `custom_data`. Dans les deux cas, `templatefile()` remplit `${ssh_public_key}` avant que
cloud-init ne reçoive le fichier.

### 5. Ansible

Ansible est **agentless** : il n'est installé que sur le control node (Linux ou WSL) et se
connecte aux VM en SSH (port 22, utilisateur `admincloud`). Les VM n'ont besoin que de SSH et de
Python, fournis par cloud-init. L'inventaire (`ansible/inventaire.ini`) est généré dynamiquement
par le script Python à partir des IP découvertes, puis :

```bash
ansible-playbook -i ansible/inventaire.ini ansible/playbook.yaml
```

Le `playbook.yaml` contient deux plays, tous deux en `become: true` :

- **web** (`role_web`) : dépose la page `index.html` dans `/var/www/html`, puis s'assure que
  Nginx est démarré et activé.
- **monitoring** (`role_monitoring`) : vérifie que Docker tourne, crée un volume `uptime-kuma`,
  puis lance le conteneur **Uptime Kuma** (`louislam/uptime-kuma`) sur le port 3001, avec
  redémarrage automatique (collection `community.docker`).

Les playbooks sont **idempotents** : on peut les rejouer, ils convergent vers le même état.

Sur Windows, Ansible n'est pas proposé directement : utilise Linux ou WSL pour lancer le playbook
depuis la même machine.

---

## Connexion SSH aux VM

L'utilisateur par défaut dans les VM est `admincloud` :

```bash
ssh -i ~/.ssh/tp_azure_ed25519 admincloud@IP_DE_LA_VM
```

Sur la VM monitoring, Docker est installé par cloud-init. Si `docker ps` refuse l'accès sans
sudo, reconnecte-toi (les groupes Linux sont chargés à la connexion) :

```bash
exit
ssh -i ~/.ssh/tp_azure_ed25519 admincloud@IP_DE_LA_VM
docker ps
```

## Erreurs fréquentes

### Python introuvable sur Windows

```powershell
py .\terraform_assistant.py
```

Si `py` manque, installe Python depuis python.org en cochant « Add Python to PATH ».

### Azure : enregistrement des resource providers

Si l'enregistrement automatique de nombreux providers Azure échoue, le projet le désactive dans
`azure/provider.tf` :

```hcl
resource_provider_registrations = "none"
```

Si Azure réclame quand même un provider précis :

```bash
az provider register --namespace Microsoft.Resources
az provider register --namespace Microsoft.Network
az provider register --namespace Microsoft.Compute
```

### Connexion Azure coupée

Si Terraform affiche `HTTP response was nil; connection may have been reset`, relance simplement
`terraform plan` puis `terraform apply` : Azure a pu créer certaines ressources avant la coupure.

### Proxmox ne trouve pas les IP

Attends la fin du premier démarrage des VM. Le script retente plusieurs recherches après l'apply.
Au besoin, vérifie dans la console Proxmox :

```bash
cloud-init status --long
```

## Commandes de secours

Pour court-circuiter le script et lancer Terraform/Ansible à la main :

Azure :

```bash
cd azure
terraform init && terraform validate && terraform plan && terraform apply
```

Proxmox :

```bash
cd Proxmox
terraform init && terraform validate && terraform plan && terraform apply
```

Ansible (Linux) :

```bash
cd ansible
ansible-playbook -i inventaire.ini playbook.yaml
```

## Ordre recommandé

1. Lancer `terraform_assistant.py`
2. Choisir `W` ou `L`
3. Choisir Azure ou Proxmox
4. Lancer « préparer Azure » ou « préparer Proxmox »
5. `terraform init`
6. `terraform validate`
7. `terraform plan`
8. `terraform apply`
9. Si Linux : générer l'inventaire Ansible
10. Lancer le playbook Ansible

## Sécurité

- Aucun secret versionné : le `.gitignore` exclut `*.tfstate`, `*.tfvars` et les clés privées.
- Proxmox piloté par un **utilisateur API dédié + token**, jamais par root.
- VM accessibles **uniquement par clé SSH** ; management Azure restreint à `admin_ip_cidr`.
- La clé privée SSH ne quitte jamais la machine de contrôle.

## Auteurs

OSOH Tech : Ryan Corsyn, Norman Skovgaard, Angelo Vazquez, Matteo Panariello
