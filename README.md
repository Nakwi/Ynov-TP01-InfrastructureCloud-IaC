# Déploiement automatisé d'une infrastructure web — TP fil rouge

Projet de mise en œuvre d'une infrastructure *as code* dans le cadre du cours Infrastructure Cloud.
L'objectif est d'industrialiser le déploiement d'une
infrastructure web : on passe d'une création manuelle de ressources à un déploiement
entièrement automatisé, reproductible et versionné.

## Objectifs

- Provisionner des machines virtuelles prêtes à l'emploi dès le démarrage avec **cloud-init**.
- Décrire l'infrastructure sous forme de code avec **Terraform**.
- Configurer automatiquement les services avec **Ansible**.
- Rendre le déploiement reproductible, modulaire et indépendant du fournisseur (Proxmox / Azure).
- Assurer le suivi des évolutions et la séparation des responsabilités grâce à **Git**.

## Architecture cible

L'infrastructure repose sur deux machines virtuelles distinctes, chacune avec un rôle clair :

| Machine      | Rôle                          | Composants                          | Exposition |
| ------------ | ----------------------------- | ----------------------------------- | ---------- |
| `web`        | Service public                | Nginx (page web statique)           | Public     |
| `monitoring` | Supervision de l'infrastructure | Uptime Kuma (Docker)              | Interne    |

Le service public (une page web servie par Nginx) est supervisé par Uptime Kuma, ce qui donne
une infrastructure cohérente : un service exposé et un outil qui en surveille la disponibilité.

## Stack technique

- **cloud-init** — amorçage des VM au premier démarrage (utilisateur, clé SSH, paquets de base).
- **Terraform** — provisionnement déclaratif des ressources.
- **Ansible** — configuration idempotente des services.
- **Nginx** — serveur web hébergeant la page publique (VM web).
- **Docker** — exécution d'Uptime Kuma (VM monitoring).
- **Git / GitHub** — versioning et séparation des couches.

## Mise en place du dépôt Git

La première étape du projet a consisté à créer le dépôt GitHub et à l'organiser pour garantir
une séparation nette entre les différentes couches de l'infrastructure as code.

### Stratégie de branches

Le dépôt est structuré autour de quatre branches, afin d'isoler chaque couche du projet et de
conserver un historique lisible :

- `main` — branche stable et intégrée. Elle ne reçoit que du code validé et fonctionnel ;
  c'est la référence du projet.
- `cloud-init` — développement et tests des fichiers de configuration cloud-init.
- `terraform` — description de l'infrastructure (provisionnement des VM, réseau, sorties).
- `ansible` — playbooks et rôles de configuration des services.

Chaque branche de couche est développée de façon isolée, puis fusionnée dans `main` une fois la
couche validée. Cette organisation permet de travailler couche par couche sans déstabiliser la
branche principale, et de matérialiser dans l'historique les trois grandes étapes du projet
(cloud-init, Terraform, Ansible).

### Fichier `.gitignore`

Le fichier `.gitignore` a été créé en tout premier, avant tout déploiement, afin de ne jamais
versionner d'état Terraform, de variables sensibles ou de clés privées :

```gitignore
*.tfstate
*.tfstate.*
*.tfvars
.terraform/
.terraform.lock.hcl
*.pem
*.key
id_rsa
id_rsa.pub
```

## Démarche de déploiement
