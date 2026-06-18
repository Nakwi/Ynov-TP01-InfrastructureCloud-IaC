# Ansible

Cette partie du projet permet de configurer automatiquement les services sur les machines virtuelles créées par Terraform et préparées par Cloud-init.

## Arborescence

```text
ansible/
├── inventaire.ini
├── playbook.yml
└── roles/
    ├── web/
    │   └── tasks/
    │       └── role_web.yml
    └── monitoring/
        └── tasks/
            └── role_monitoring.yml
```

## Description des fichiers

| Fichier | Description |
|----------|-------------|
| `inventaire.ini` | Liste des machines cibles et paramètres de connexion SSH. |
| `playbook.yml` | Point d'entrée Ansible permettant d'exécuter les rôles sur les différentes machines. |
| `role_web.yml` | Configuration du serveur web Nginx. |
| `role_monitoring.yml` | Configuration du serveur de monitoring Docker et Uptime Kuma. |

## Configuration SSH

Appliquer les permissions sur la clé privée :

```bash
chmod 600 ~/.ssh/tp_azure_ed25519
```

Résultat attendu :

```text
web01 | SUCCESS
monitoring01 | SUCCESS
```

## Exécution du playbook

Lancer le déploiement :

```bash
ansible-playbook -i inventaire.ini playbook.yaml
```

## Fonctionnement

Le playbook exécute les rôles suivants :

### Rôle Web

- Déploiement de la page d'accueil Nginx
- Vérification du service Nginx
- Démarrage automatique du service si nécessaire

### Rôle Monitoring

- Vérification du service Docker
- Création du volume persistant Uptime Kuma
- Déploiement du conteneur Uptime Kuma
- Vérification du bon fonctionnement du service

## Vérification

### Site Web

```text
http://IP_DE_LA_VM_WEB
```

### Uptime Kuma

```text
http://IP_DE_LA_VM_MONITORING:3001
```

## Objectif

Automatiser la configuration des services afin d'obtenir un déploiement reproductible, fiable et idempotent sur l'ensemble des environnements.
