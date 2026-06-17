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
    os.system("touch .Terraform/proxmox/tmp.auto.tfvars")

    print("Application des variables")
    with open('.Terraform/proxmox/tmp.auto.tfvars', 'w') as f:
        f.write(f"vmname = {vm_name}")
        f.write(f"vmID = {vm_ID}")
        f.write(f"vmIP = {vm_IP}")
        f.write(f"vmGW = {vm_GW}")
    
    while True:
        print("Execution de Terraform")
        os.system("terraform init")
        con1 = input("Continue ? (Y/n) : ")
        if con1 == "y" and con1 == "Y" and con1 == "":
            break
        elif con1 == "n" and con1 == "N":
            sys.exit(1)
        else:
            print("Choix incorrect")
    
    while True:
        os.system("terraform fmt")
        con2 = input("Continue ? (Y/n) : ")
        if con2 == "y" and con2 == "Y" and con2 == "":
            break
        elif con2 == "n" and con2 == "N":
            sys.exit(2)
        else:
            print("Choix incorrect")
    
    while True:
        os.system("terraform validate")
        con3 = input("Continue ? (Y/n) : ")
        if con3 == "y" and con3 == "Y" and con3 == "":
            break
        elif con3 == "n" and con3 == "N":
            sys.exit(3)
        else:
            print("Choix incorrect")

    while True:
        os.system("terraform plan")
        con4 = input("Continue ? (Y/n) : ")
        if con4 == "y" and con4 == "Y" and con4 == "":
            break
        elif con4 == "n" and con4 == "N":
            sys.exit(4)
        else:
            print("Choix incorrect")

    while True:
        os.system("terraform apply")
        con5 = input("Continue ? (Y/n) : ")
        if con5 == "y" and con5 == "Y" and con5 == "":
            break
        elif con5 == "n" and con5 == "N":
            sys.exit(5)
        else:
            print("Choix incorrect")



if __name__ == "__main__":
    menu()