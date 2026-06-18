# Ynov-TP01-InfrastructureCloud-IaC
TP fil rouge M1 — Déploiement automatisé d'une infrastructure web reproductible (cloud-init + Terraform + Ansible), portable Proxmox/Azure.

Ansible - arboresence a réaliser

```
/home
├── inventory.ini
├── playbook.yml
└── roles/
    ├── web/
    │   └── tasks/
    │       └── main.yml
    └── monitoring/
        └── tasks/
            └── main.yml
```

Description des fichiers
Fichier	Description
inventaire.ini	Liste des machines cibles et paramètres de connexion SSH.
playbook.yml	Point d'entrée Ansible permettant d'exécuter les rôles sur les différentes machines.
role_web.yml	Configuration du serveur web Nginx.
role_monitoring.yml	Configuration du serveur de monitoring Docker et Uptime Kuma.
Configuration SSH

Appliquer les permissions sur la clé privée :

chmod 600 ~/.ssh/tp_azure_ed25519

Résultat attendu :

web01 | SUCCESS
monitoring01 | SUCCESS
Exécution du playbook

Lancer le déploiement :

ansible-playbook -i inventaire.ini playbook.yml
Fonctionnement

Le playbook exécute les rôles suivants :

Rôle Web
Déploiement de la page d'accueil Nginx
Vérification du service Nginx
Démarrage automatique du service si nécessaire
Rôle Monitoring
Vérification du service Docker
Création du volume persistant Uptime Kuma
Déploiement du conteneur Uptime Kuma
Vérification du bon fonctionnement du service
Vérification
Site Web
http://IP_DE_LA_VM_WEB
Uptime Kuma
http://IP_DE_LA_VM_MONITORING:3001
Objectif

Automatiser la configuration des services afin d'obtenir un déploiement reproductible, fiable et idempotent sur l'ensemble des environnements.
