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

commande a executer : 
ansible-playbook -i inventaire.ini playbook.yaml

chmod 600 /root/.ssh/tp_azure_ed25519
