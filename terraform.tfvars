subscription_id = "VOTRE-subscription_id"
# Commande pour récupérer votre Sub ID : az account show --query id -o tsv


project_name = "tp-cloud"
location     = "spaincentral"

admin_username      = "admincloud"
ssh_public_key_path = "~/.ssh/tp_azure_ed25519.pub"

admin_ip_cidr = "VOTRE-IP-PUBLIQUE/32"
#Commande pour récupérer votre IP publique : Invoke-RestMethod -Uri "https://api.ipify.org"

web_vm_size        = "Standard_B2ats_v2"
monitoring_vm_size = "Standard_B2ats_v2"
