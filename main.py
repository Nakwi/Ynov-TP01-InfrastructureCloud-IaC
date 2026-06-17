# Lancement du Terraform

# Choix pour Azure ou Proxmox

import sys
import os

def menu():
    while True:
        print("""Type de déploiement :

    1. Azure
    2. Proxmox
            
    0. Exit
            """)
        
        azprox = int(input(" Choisissiez le type de déploiement : "))

        if azprox == 1:
            azure()
            break
        elif azprox == 2:
            proxmox()
            break
        elif azprox == 0:
            sys.exit(0)
        else:
            print("Choix incorrect")

vm_name = input("Quel nom pour la VM?")
vm_ID = int(input("Quel ID pour la VM?"))

def azure():
    print("")

def proxmox():
    print("")

menu()