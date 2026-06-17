# Lancement du Terraform

# Choix pour azure ou Proxmox

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



def azure():
    print("TG")

def proxmox():
    print("Lancement du module Proxmox")
    print("Insérez vos variables pour la VM créée : ")

    vm_name = input("Nom de la VM : ")
    vm_ID = int(input("ID de la VM : "))
    vm_IP = input("IP de la VM : ")
    vm_GW = input("Passerellle de la VM : ")

    print("Création du fichier tmp.auto.tfvars")
    os.system("touch ./Terraform/proxmox/tmp.auto.tfvars")

    print("Application des variables")
    with open('./Terraform/proxmox/tmp.auto.tfvars', 'w') as f:
        f.write(f"""vmname = {vm_name}
vmID = {vm_ID}
vmIP = {vm_IP}
vmGW = {vm_GW}""")
    
    while True:
        print("Execution de Terraform")
        os.system("terraform -chdir=./Terraform/proxmox init")
        con1 = input("Continue ? (Y/n) : ")
        if con1 == "y" or con1 == "Y" or con1 == "":
            break
        elif con1 == "n" or con1 == "N":
            sys.exit(1)
        else:
            print("Choix incorrect")
    
    while True:
        os.system("terraform -chdir=./Terraform/proxmox fmt")
        con2 = input("Continue ? (Y/n) : ")
        if con2 == "y" or con2 == "Y" or con2 == "":
            break
        elif con2 == "n" or con2 == "N":
            sys.exit(2)
        else:
            print("Choix incorrect")
    
    while True:
        os.system("terraform -chdir=./Terraform/proxmox validate")
        con3 = input("Continue ? (Y/n) : ")
        if con3 == "y" or con3 == "Y" or con3 == "":
            break
        elif con3 == "n" or con3 == "N":
            sys.exit(3)
        else:
            print("Choix incorrect")

    while True:
        os.system("terraform -chdir=./Terraform/proxmox plan")
        con4 = input("Continue ? (Y/n) : ")
        if con4 == "y" or con4 == "Y" or con4 == "":
            break
        elif con4 == "n" or con4 == "N":
            sys.exit(4)
        else:
            print("Choix incorrect")

    while True:
        os.system("terraform -chdir=./Terraform/proxmox apply")
        con5 = input("Continue ? (Y/n) : ")
        if con5 == "y" or con5 == "Y" or con5 == "":
            break
        elif con5 == "n" or con5 == "N":
            sys.exit(5)
        else:
            print("Choix incorrect")



if __name__ == "__main__":
    menu()