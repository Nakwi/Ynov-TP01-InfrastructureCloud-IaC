#!/usr/bin/env python3
"""Assistant simple pour piloter les stacks Terraform Azure et Proxmox."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

# Dossiers Terraform disponibles dans le projet.
STACKS = {"azure": ROOT / "azure", "proxmox": ROOT / "Proxmox"}

# Valeurs utilisees par defaut si terraform.tfvars n'existe pas encore.
DEFAULT_KEY = "~/.ssh/tp_azure_ed25519"
ADMIN_USER = "admincloud"

# Fichiers Ansible deja presents dans le projet.
ANSIBLE_DIR = ROOT / "ansible"
ANSIBLE_INVENTORY = ANSIBLE_DIR / "inventaire.ini"
ANSIBLE_PLAYBOOK = ANSIBLE_DIR / "playbook.yaml"


# -----------------------------
# Petites fonctions d'affichage
# -----------------------------

def info(title: str) -> None:
    # Affiche un titre lisible dans le terminal.
    print(f"\n== {title} ==")


def ask(prompt: str, default: str | None = None) -> str:
    # Pose une question a l'utilisateur.
    # Si une valeur par defaut existe et que l'utilisateur appuie sur Entree,
    # on retourne cette valeur par defaut.
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


# -----------------------------
# Commandes locales
# -----------------------------

def require_command(name: str) -> None:
    # Verifie qu'une commande existe sur le PC.
    # Exemple: terraform, ssh, ssh-keygen.
    if shutil.which(name) is None:
        raise RuntimeError(f"Commande introuvable: {name}")


def has_command(name: str) -> bool:
    # Version simple de require_command.
    # Elle renvoie True/False au lieu de bloquer le script.
    return shutil.which(name) is not None


def command_path(name: str) -> str:
    # Sur Windows, certaines commandes sont des .CMD.
    # Avec subprocess, utiliser le chemin complet evite les erreurs.
    return shutil.which(name) or name


def run(
    args: list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
    show_output: bool = True,
) -> str:
    # Lance une commande locale.
    # - args: liste de morceaux de commande, exemple ["terraform", "plan"]
    # - cwd: dossier ou lancer la commande
    # - capture: True si on veut recuperer le texte renvoye par la commande
    print("$ " + " ".join(shlex.quote(str(arg)) for arg in args))
    working_dir = str(cwd) if cwd else None
    result = subprocess.run(args, cwd=working_dir, text=True, capture_output=capture)

    if capture and show_output:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

    if check and result.returncode != 0:
        raise RuntimeError("La commande a echoue.")

    return (result.stdout or "").strip()


def expand(path: str) -> Path:
    # Transforme "~/.ssh/..." en chemin complet Windows/Linux.
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def shell_quote(value: str) -> str:
    # Protege une valeur envoyee dans une commande shell Linux distante.
    return "'" + value.replace("'", "'\"'\"'") + "'"


# -----------------------------
# Lecture/ecriture terraform.tfvars
# -----------------------------

def read_tfvars(stack: str) -> str:
    # Lit le fichier terraform.tfvars d'une stack.
    # Si le fichier n'existe pas encore, on retourne du texte vide.
    path = STACKS[stack] / "terraform.tfvars"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def get_tfvar(stack: str, name: str, default: str = "") -> str:
    # Recupere une variable dans terraform.tfvars.
    # Exemple: get_tfvar("proxmox", "network_bridge", "vmbr0")
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", read_tfvars(stack))
    if not match:
        return default

    value = match.group(1).strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def hcl(value: str | bool | int) -> str:
    # Convertit une valeur Python en valeur compatible Terraform/HCL.
    # Exemple: True -> true, "texte" -> "texte"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def set_tfvar(stack: str, name: str, value: str | bool | int) -> None:
    # Ajoute ou remplace une variable dans terraform.tfvars.
    path = STACKS[stack] / "terraform.tfvars"
    text = read_tfvars(stack)
    line = f"{name} = {hcl(value)}"
    pattern = rf"(?m)^\s*{re.escape(name)}\s*=.*$"

    if re.search(pattern, text):
        text = re.sub(pattern, line, text)
    else:
        text = text.rstrip() + "\n" + line + "\n"

    path.write_text(text.lstrip(), encoding="utf-8")


# -----------------------------
# SSH vers Proxmox
# -----------------------------

def ssh(host: str, command: str, key: str | None = None, check: bool = True, capture: bool = False) -> str:
    # Lance une commande SSH sur le serveur Proxmox.
    args = ["ssh", "-o", "StrictHostKeyChecking=accept-new"]

    # BatchMode evite que SSH reste bloque quand on ne veut pas de saisie interactive.
    if capture or not check:
        args += ["-o", "BatchMode=yes"]

    if key and expand(key).exists():
        args += ["-i", str(expand(key))]

    return run(args + [host, command], check=check, capture=capture)


def ensure_ssh_key(private_key: str) -> None:
    # Cree une cle SSH si elle n'existe pas encore.
    # Cette cle servira a se connecter au node Proxmox et aux VM.
    require_command("ssh-keygen")
    key = expand(private_key)
    pub = Path(str(key) + ".pub")
    key.parent.mkdir(parents=True, exist_ok=True)

    if key.exists() and pub.exists():
        print(f"Cle SSH deja presente: {key}")
        return

    run(["ssh-keygen", "-t", "ed25519", "-f", str(key), "-C", "tp-proxmox", "-N", ""])


def endpoint_host() -> str:
    # Recupere l'IP du Proxmox depuis proxmox_endpoint.
    # Exemple: https://192.168.1.126:8006/ -> 192.168.1.126
    endpoint = get_tfvar("proxmox", "proxmox_endpoint", "https://192.168.1.126:8006/")
    match = re.search(r"https?://([^/:]+)", endpoint)
    if match:
        return match.group(1)
    return "192.168.1.126"


def install_root_key(host: str, private_key: str) -> None:
    # Copie la cle publique locale dans /root/.ssh/authorized_keys sur Proxmox.
    # A la premiere execution, SSH peut demander le mot de passe root.
    pub = Path(str(expand(private_key)) + ".pub").read_text(encoding="utf-8").strip()

    remote = (
        "mkdir -p /root/.ssh && chmod 700 /root/.ssh && "
        "touch /root/.ssh/authorized_keys && "
        f"(grep -qxF -- {shell_quote(pub)} /root/.ssh/authorized_keys || "
        f"echo {shell_quote(pub)} >> /root/.ssh/authorized_keys) && "
        "chmod 600 /root/.ssh/authorized_keys && systemctl enable --now ssh"
    )
    print("La premiere connexion peut demander le mot de passe root Proxmox.")
    ssh(f"root@{host}", remote, key=private_key)
    ssh(f"root@{host}", "echo ok", key=private_key, capture=True)


def prepare_node(host: str, private_key: str, datastore: str) -> str:
    # Prepare le node Proxmox pour Terraform:
    # - SSH actif
    # - datastore local compatible snippets/import
    # - dossier snippets present
    # - nmap installe pour retrouver les IP si l'agent QEMU ne repond pas
    remote = "; ".join(
        [
            "set -e",
            "systemctl enable --now ssh",
            f"pvesm set {shell_quote(datastore)} --content iso,vztmpl,backup,import,snippets",
            f"snippet_dir=$(pvesm path {shell_quote(datastore + ':snippets')} 2>/dev/null || true)",
            'if [ -z "$snippet_dir" ]; then snippet_dir=/var/lib/vz/snippets; fi',
            'mkdir -p "$snippet_dir"',
            'chmod 755 "$snippet_dir"',
            "if ! command -v nmap >/dev/null 2>&1; then apt-get update -y && apt-get install -y nmap; fi",
            "hostname",
        ]
    )

    output = ssh(f"root@{host}", remote, key=private_key, capture=True)
    lines = [line.strip() for line in output.splitlines() if line.strip()]

    if lines:
        return lines[-1]
    return "pve"


def create_api_token(host: str, private_key: str, api_user: str, token_id: str) -> tuple[str, str]:
    # Cree un utilisateur/token Proxmox pour Terraform.
    # Le token est recree a chaque preparation pour eviter les secrets perdus.
    user = shell_quote(api_user)
    token = shell_quote(token_id)

    # Creation de l'utilisateur et droits administrateur.
    ssh(
        f"root@{host}",
        "; ".join(
            [
                f"pveum user add {user} --comment 'Terraform user' 2>/dev/null || true",
                f"pveum acl modify / --users {user} --roles Administrator",
                f"pveum user token remove {user} {token} 2>/dev/null || true",
            ]
        ),
        key=private_key,
        capture=True,
    )

    # Creation du token API. Proxmox affiche le secret une seule fois.
    output = ssh(
        f"root@{host}",
        f"pveum user token add {user} {token} --privsep 0 --output-format json",
        key=private_key,
        capture=True,
    )

    # Cas normal: Proxmox renvoie du JSON.
    try:
        data = json.loads(output[output.find("{") :])
        return data.get("full-tokenid", f"{api_user}!{token_id}"), data["value"]

    # Secours: si le JSON est parasite par un message, on cherche le secret UUID.
    except Exception:
        match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", output)
        if not match:
            raise RuntimeError("Impossible de recuperer le secret du token API Proxmox.")
        return f"{api_user}!{token_id}", match.group(0)


def prepare_proxmox() -> None:
    # Parcours complet de preparation Proxmox.
    # Il remplit ensuite Proxmox/terraform.tfvars pour Terraform.
    host = ask("IP ou DNS du Proxmox", endpoint_host())
    private_key = ask("Cle SSH privee locale", get_tfvar("proxmox", "proxmox_ssh_private_key_path", DEFAULT_KEY))
    api_user = ask("User API Proxmox", "terraform@pve")
    token_id = ask("Token ID Proxmox", "provider")
    bridge = ask("Bridge reseau des VM", get_tfvar("proxmox", "network_bridge", "vmbr0"))
    snippets_store = ask("Datastore snippets/import", get_tfvar("proxmox", "snippets_datastore_id", "local"))
    image_store = ask("Datastore image Debian", get_tfvar("proxmox", "image_datastore_id", "local"))
    vm_store = ask("Datastore disques VM", get_tfvar("proxmox", "vm_datastore_id", "local-lvm"))
    cloud_init_store = ask("Datastore disque cloud-init", get_tfvar("proxmox", "cloud_init_datastore_id", "local-lvm"))

    info("SSH")
    ensure_ssh_key(private_key)
    install_root_key(host, private_key)

    info("Node Proxmox")
    node = prepare_node(host, private_key, snippets_store)
    print(f"Node detecte: {node}")

    info("Token API")
    full_token_id, token_secret = create_api_token(host, private_key, api_user, token_id)

    info("terraform.tfvars")

    # Toutes ces valeurs sont ecrites dans Proxmox/terraform.tfvars.
    values: dict[str, str | bool] = {
        "proxmox_endpoint": f"https://{host}:8006/",
        "proxmox_ssh_username": "root",
        "proxmox_ssh_agent": False,
        "proxmox_ssh_private_key_path": private_key,
        "ssh_public_key_path": f"{private_key}.pub",
        "proxmox_node_name": node,
        "network_bridge": bridge,
        "snippets_datastore_id": snippets_store,
        "image_datastore_id": image_store,
        "vm_datastore_id": vm_store,
        "cloud_init_datastore_id": cloud_init_store,
        "proxmox_api_token_id": full_token_id,
        "proxmox_api_token": token_secret,
        "qemu_guest_agent_enabled": True,
    }

    for name, value in values.items():
        set_tfvar("proxmox", name, value)

    print("Proxmox/terraform.tfvars mis a jour.")


# -----------------------------
# Preparation Azure
# -----------------------------

def yes(value: str) -> bool:
    # Accepte les reponses francaises et anglaises les plus courantes.
    return value.lower() in ("o", "oui", "y", "yes")


def public_ip_cidr() -> str:
    # Recupere l'IP publique du poste pour ouvrir SSH seulement depuis cette IP.
    try:
        with urllib.request.urlopen("https://api.ipify.org", timeout=10) as response:
            ip = response.read().decode("utf-8").strip()
            return f"{ip}/32"
    except Exception:
        return ""


def install_azure_cli(local_os: str) -> None:
    # Installe Azure CLI si possible.
    # Windows: winget.
    # Linux Debian/Ubuntu: script officiel Microsoft via curl.
    if has_command("az"):
        print("Azure CLI est deja installe.")
        run([command_path("az"), "version"], capture=True)
        return

    if not yes(ask("Azure CLI introuvable. Installer maintenant ? (o/n)", "o")):
        raise RuntimeError("Azure CLI est necessaire pour preparer Azure.")

    if local_os == "windows":
        require_command("winget")
        run(
            [
                "winget",
                "install",
                "--id",
                "Microsoft.AzureCLI",
                "--exact",
                "--accept-source-agreements",
                "--accept-package-agreements",
            ]
        )
    else:
        require_command("bash")
        require_command("curl")
        install_command = "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            install_command = "curl -sL https://aka.ms/InstallAzureCLIDeb | bash"
        run(["bash", "-lc", install_command])

    require_command("az")
    run([command_path("az"), "version"], capture=True)


def azure_subscription_id() -> str:
    # Retourne l'abonnement Azure actif si la personne est deja connectee.
    return run(
        [command_path("az"), "account", "show", "--query", "id", "-o", "tsv"],
        check=False,
        capture=True,
        show_output=False,
    ).strip()


def azure_login() -> str:
    # Connexion Azure en mode device code, pratique dans un terminal.
    # Cela evite l'ouverture automatique d'une page de login.
    run([command_path("az"), "login", "--use-device-code"])
    return azure_subscription_id()


def prepare_azure(local_os: str) -> None:
    # Parcours complet de preparation Azure.
    # Il remplit ensuite azure/terraform.tfvars pour Terraform.
    info("SSH")
    private_key = ask("Cle SSH privee locale", private_key_for_stack("azure"))
    ensure_ssh_key(private_key)

    info("Azure CLI")
    install_azure_cli(local_os)

    info("Connexion Azure")
    current_subscription = azure_subscription_id()
    if not current_subscription or yes(ask("Lancer az login --use-device-code ? (o/n)", "o")):
        current_subscription = azure_login()

    subscription_id = ask(
        "Subscription ID Azure",
        get_tfvar("azure", "subscription_id", current_subscription),
    )
    if not subscription_id:
        raise RuntimeError("subscription_id est obligatoire pour Terraform Azure.")

    run([command_path("az"), "account", "set", "--subscription", subscription_id])

    info("Parametres Terraform Azure")
    project_name = ask("Nom du projet", get_tfvar("azure", "project_name", "tp-cloud"))
    location = ask("Region Azure", get_tfvar("azure", "location", "spaincentral"))
    admin_user = ask("Utilisateur admin des VM", get_tfvar("azure", "admin_username", ADMIN_USER))
    detected_ip = public_ip_cidr()
    admin_ip = ask("IP publique autorisee en SSH", get_tfvar("azure", "admin_ip_cidr", detected_ip))

    if not admin_ip:
        raise RuntimeError("admin_ip_cidr est obligatoire. Exemple: 1.2.3.4/32")

    values: dict[str, str] = {
        "subscription_id": subscription_id,
        "project_name": project_name,
        "location": location,
        "admin_username": admin_user,
        "ssh_public_key_path": f"{private_key}.pub",
        "admin_ip_cidr": admin_ip,
    }

    for name, value in values.items():
        set_tfvar("azure", name, value)

    print("azure/terraform.tfvars mis a jour.")


def terraform_cmd(stack: str, command: str) -> None:
    # Lance une commande Terraform dans le bon dossier.
    # Exemple: stack="proxmox", command="plan" -> terraform plan dans Proxmox/
    require_command("terraform")
    cwd = STACKS[stack]
    run(["terraform", command], cwd=cwd)

    # Si apply reussit, on essaye tout de suite d'afficher les IP utiles.
    if command == "apply":
        show_ips_after_apply(stack)


def vm_ids() -> dict[str, str]:
    # IDs des VM dans Proxmox.
    # On lit terraform.tfvars si les IDs ont ete personnalises.
    return {
        "web": get_tfvar("proxmox", "web_vm_id", "201"),
        "monitoring": get_tfvar("proxmox", "monitoring_vm_id", "202"),
    }


def extract_agent_ips(data: Any) -> list[str]:
    # Analyse la reponse JSON du QEMU Guest Agent.
    # Objectif: recuperer uniquement les IPv4 utiles, pas 127.0.0.1.
    if isinstance(data, dict):
        data = data.get("result", data)
        if isinstance(data, dict):
            data = data.get("interfaces", data.get("result", []))

    if not isinstance(data, list):
        return []

    ips: list[str] = []

    for iface in data:
        if not isinstance(iface, dict):
            continue

        ip_addresses = iface.get("ip-addresses", [])
        for item in ip_addresses:
            ip = item.get("ip-address")
            ip_type = item.get("ip-address-type")

            if not ip:
                continue
            if ip.startswith("127."):
                continue
            if ip_type not in (None, "ipv4"):
                continue

            ips.append(ip)

    return ips


def ips_from_agent(host: str, private_key: str) -> dict[str, str]:
    # Premiere methode pour trouver les IP: QEMU Guest Agent.
    # C'est propre et rapide, mais il faut que l'agent soit bien demarre dans la VM.
    node = get_tfvar("proxmox", "proxmox_node_name", "pve")
    ips: dict[str, str] = {}

    for role, vmid in vm_ids().items():
        command = f"pvesh get /nodes/{node}/qemu/{vmid}/agent/network-get-interfaces --output-format json"
        output = ssh(f"root@{host}", command, key=private_key, check=False, capture=True)

        try:
            found = extract_agent_ips(json.loads(output))
        except Exception:
            found = []

        if found:
            ips[role] = found[0]

    return ips


def ips_from_nmap(host: str, private_key: str) -> dict[str, str]:
    # Deuxieme methode si l'agent QEMU ne repond pas:
    # 1. On lit les MAC des VM avec qm config.
    # 2. On scanne le reseau avec nmap.
    # 3. On associe MAC -> IP.
    macs: dict[str, str] = {}

    for role, vmid in vm_ids().items():
        config = ssh(f"root@{host}", f"qm config {vmid}", key=private_key, check=False, capture=True)
        match = re.search(r"net0:\s+\S+=([0-9A-Fa-f:]{17}),", config)
        if match:
            macs[role] = match.group(1).upper()

    # On essaye de detecter automatiquement le subnet du bridge Proxmox.
    bridge = get_tfvar("proxmox", "network_bridge", "vmbr0")
    subnet = ssh(
        f"root@{host}",
        f"ip -4 route show dev {shell_quote(bridge)} proto kernel scope link | awk '{{print $1; exit}}'",
        key=private_key,
        check=False,
        capture=True,
    ).strip()

    try:
        ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        subnet = ask("Subnet a scanner", "192.168.1.0/24")

    scan = ssh(f"root@{host}", f"nmap -sn {shell_quote(subnet)}", key=private_key, check=False, capture=True)
    current_ip = ""
    found: dict[str, str] = {}

    for line in scan.splitlines():
        report = re.search(r"Nmap scan report for .*\((\d+\.\d+\.\d+\.\d+)\)", line)
        if not report:
            report = re.search(r"Nmap scan report for (\d+\.\d+\.\d+\.\d+)", line)

        if report:
            current_ip = report.group(1)
            continue

        mac = re.search(r"MAC Address:\s+([0-9A-Fa-f:]{17})", line)
        if mac and current_ip:
            for role, expected in macs.items():
                if mac.group(1).upper() == expected:
                    found[role] = current_ip

    return found


def print_proxmox_ips(ips: dict[str, str], private_key: str) -> None:
    # Affiche les IP et les commandes SSH utiles.
    info("IP trouvees")
    for role in ("web", "monitoring"):
        ip = ips.get(role, "<non trouvee>")
        print(f"{role:10} {ip}")

        if ip != "<non trouvee>":
            print(f"  ssh -i {private_key} {ADMIN_USER}@{ip}")

    if ips.get("web"):
        print(f"  web_url: http://{ips['web']}")
    if ips.get("monitoring"):
        print(f"  uptime_kuma_url: http://{ips['monitoring']}:3001")


def find_proxmox_ips(prompt: bool = True, attempts: int = 1, wait_seconds: int = 15) -> dict[str, str]:
    # Fonction interne pour afficher les IP des VM.
    # prompt=True: on pose les questions dans le menu.
    # prompt=False: apres terraform apply, on utilise directement terraform.tfvars.
    host = endpoint_host()
    private_key = get_tfvar("proxmox", "proxmox_ssh_private_key_path", DEFAULT_KEY)

    if prompt:
        host = ask("IP ou DNS du Proxmox", host)
        private_key = ask("Cle SSH privee locale", private_key)

    ips: dict[str, str] = {}

    for attempt in range(1, attempts + 1):
        info(f"Recherche IP Proxmox ({attempt}/{attempts})")
        ips = ips_from_agent(host, private_key)

        if set(ips) != {"web", "monitoring"}:
            print("Agent incomplet, fallback nmap/MAC.")
            ips.update(ips_from_nmap(host, private_key))

        if set(ips) == {"web", "monitoring"}:
            break

        if attempt < attempts:
            print(f"IP encore incomplete, nouvelle tentative dans {wait_seconds} secondes.")
            time.sleep(wait_seconds)

    print_proxmox_ips(ips, private_key)
    return ips


# -----------------------------
# Ansible
# -----------------------------

def as_root(args: list[str]) -> list[str]:
    # Sur Linux, certaines installations demandent les droits administrateur.
    # Si on n'est pas root et que sudo existe, on ajoute sudo devant la commande.
    if hasattr(os, "geteuid") and os.geteuid() != 0 and has_command("sudo"):
        return ["sudo"] + args
    return args


def terraform_outputs(stack: str) -> dict[str, Any]:
    # Recupere les outputs Terraform en JSON.
    # On l'utilise surtout pour Azure, qui donne directement les IP publiques.
    require_command("terraform")
    output = run(["terraform", "output", "-json"], cwd=STACKS[stack], check=False, capture=True, show_output=False)
    if not output:
        return {}

    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {}


def output_value(outputs: dict[str, Any], name: str) -> str:
    # Dans le JSON Terraform, une valeur est souvent rangee dans la cle "value".
    item = outputs.get(name)
    if isinstance(item, dict):
        return str(item.get("value", "")).strip()
    return str(item or "").strip()


def private_key_for_stack(stack: str) -> str:
    # Retrouve la cle privee a utiliser pour Ansible.
    if stack == "proxmox":
        return get_tfvar("proxmox", "proxmox_ssh_private_key_path", DEFAULT_KEY)

    public_key = get_tfvar("azure", "ssh_public_key_path", f"{DEFAULT_KEY}.pub")
    if public_key.endswith(".pub"):
        return public_key[:-4]
    return public_key


def user_for_stack(stack: str) -> str:
    # Azure peut avoir un utilisateur personnalise.
    # Proxmox utilise l'utilisateur cree dans les cloud-init.
    if stack == "azure":
        return get_tfvar("azure", "admin_username", ADMIN_USER)
    return ADMIN_USER


def host_names_for_stack(stack: str) -> dict[str, str]:
    # Noms des machines tels qu'ils sont crees par Terraform.
    prefix = get_tfvar(stack, "project_name", "tp-cloud")
    if stack == "azure":
        return {"web": f"{prefix}-web-vm", "monitoring": f"{prefix}-monitoring-vm"}
    return {"web": f"{prefix}-web", "monitoring": f"{prefix}-monitoring"}


def ips_for_ansible(stack: str) -> dict[str, str]:
    # Recupere les IP a placer dans inventaire.ini.
    # Azure: outputs Terraform.
    # Proxmox: QEMU Guest Agent puis nmap si besoin.
    if stack == "proxmox":
        return find_proxmox_ips()

    outputs = terraform_outputs("azure")
    return {
        "web": output_value(outputs, "web_public_ip"),
        "monitoring": output_value(outputs, "monitoring_public_ip"),
    }


def print_azure_ips() -> None:
    # Affiche les IP Azure apres un apply.
    outputs = terraform_outputs("azure")
    ips = {
        "web": output_value(outputs, "web_public_ip"),
        "monitoring": output_value(outputs, "monitoring_public_ip"),
    }
    private_key = private_key_for_stack("azure")
    user = user_for_stack("azure")

    info("IP trouvees")
    for role in ("web", "monitoring"):
        ip = ips.get(role) or "<non trouvee>"
        print(f"{role:10} {ip}")

        if ip != "<non trouvee>":
            print(f"  ssh -i {private_key} {user}@{ip}")

    if ips.get("web"):
        print(f"  web_url: http://{ips['web']}")
    if ips.get("monitoring"):
        print(f"  uptime_kuma_url: http://{ips['monitoring']}:3001")


def show_ips_after_apply(stack: str) -> None:
    # Cette fonction est appelee automatiquement apres terraform apply.
    # On garde une sortie simple: IP, commandes SSH et URLs.
    info("Recuperation automatique des IP")

    if stack == "proxmox":
        find_proxmox_ips(prompt=False, attempts=6, wait_seconds=15)
    elif stack == "azure":
        print_azure_ips()


def write_ansible_inventory(stack: str) -> None:
    # Genere ansible/inventaire.ini avec les IP detectees.
    ips = ips_for_ansible(stack)
    names = host_names_for_stack(stack)
    user = user_for_stack(stack)
    private_key = ask("Cle SSH privee pour Ansible", private_key_for_stack(stack))

    missing = [role for role in ("web", "monitoring") if not ips.get(role)]
    if missing:
        raise RuntimeError("IP introuvable pour: " + ", ".join(missing))

    ANSIBLE_DIR.mkdir(parents=True, exist_ok=True)
    text = f"""[web]
{names['web']} ansible_host={ips['web']} ansible_user={user}

[monitoring]
{names['monitoring']} ansible_host={ips['monitoring']} ansible_user={user}

[all:vars]
ansible_ssh_private_key_file={private_key}
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
"""

    ANSIBLE_INVENTORY.write_text(text, encoding="utf-8")
    print(f"Inventaire Ansible mis a jour: {ANSIBLE_INVENTORY}")


def install_ansible_linux() -> None:
    # Installe Ansible sur un poste Linux si la commande manque.
    # Le script reste volontairement simple: apt, dnf, yum ou pacman.
    if os.name == "nt":
        raise RuntimeError("Ansible doit etre lance depuis Linux ou WSL. Relance le script dans Linux, ou choisis W.")

    if has_command("ansible-playbook"):
        print("Ansible est deja installe.")
    elif has_command("apt-get"):
        run(as_root(["apt-get", "update", "-y"]))
        run(as_root(["apt-get", "install", "-y", "ansible"]))
    elif has_command("dnf"):
        run(as_root(["dnf", "install", "-y", "ansible"]))
    elif has_command("yum"):
        run(as_root(["yum", "install", "-y", "ansible"]))
    elif has_command("pacman"):
        run(as_root(["pacman", "-Sy", "--noconfirm", "ansible"]))
    else:
        raise RuntimeError("Gestionnaire de paquets non reconnu. Installe Ansible manuellement.")

    require_command("ansible-playbook")
    run(["ansible-playbook", "--version"], capture=True)

    # Le role monitoring utilise community.docker pour gerer Uptime Kuma.
    if has_command("ansible-galaxy"):
        run(["ansible-galaxy", "collection", "install", "community.docker"], check=False)


def run_ansible_playbook(stack: str) -> None:
    # Prepare Ansible puis lance le playbook existant.
    install_ansible_linux()
    write_ansible_inventory(stack)

    if not ANSIBLE_PLAYBOOK.exists():
        raise RuntimeError(f"Playbook introuvable: {ANSIBLE_PLAYBOOK}")

    run(["ansible-playbook", "-i", str(ANSIBLE_INVENTORY), str(ANSIBLE_PLAYBOOK)], cwd=ANSIBLE_DIR)


# -----------------------------
# Menus
# -----------------------------

def choose_local_os() -> str:
    # Au demarrage, on demande le systeme du poste qui lance le script.
    # W = Windows: Terraform/Proxmox/Azure seulement.
    # L = Linux: on ajoute Ansible dans les menus.
    default = "W" if os.name == "nt" else "L"

    while True:
        choice = ask("Poste local (W=Windows, L=Linux)", default).lower()
        if choice in ("w", "windows"):
            print("Mode Windows: les actions Ansible sont masquees.")
            return "windows"
        if choice in ("l", "linux"):
            print("Mode Linux: les actions Ansible sont disponibles.")
            return "linux"
        print("Choix invalide. Tape W ou L.")


def add_action(actions: dict[str, tuple[str, Any]], label: str, action: Any) -> None:
    # Ajoute une entree au menu avec le prochain numero disponible.
    number = str(len(actions) + 1)
    actions[number] = (label, action)


def stack_menu(stack: str, local_os: str) -> None:
    # Menu d'une stack Terraform.
    # Ansible apparait seulement si le poste choisi au demarrage est Linux.
    actions = {
        "1": ("terraform init", lambda: terraform_cmd(stack, "init")),
        "2": ("terraform validate", lambda: terraform_cmd(stack, "validate")),
        "3": ("terraform plan", lambda: terraform_cmd(stack, "plan")),
        "4": ("terraform apply", lambda: terraform_cmd(stack, "apply")),
    }

    if stack == "azure":
        add_action(actions, "preparer Azure", lambda: prepare_azure(local_os))

    if stack == "proxmox":
        add_action(actions, "preparer Proxmox", prepare_proxmox)

    if local_os == "linux":
        add_action(actions, "generer inventaire Ansible", lambda: write_ansible_inventory(stack))
        add_action(actions, "installer/verifier Ansible", install_ansible_linux)
        add_action(actions, "lancer playbook Ansible", lambda: run_ansible_playbook(stack))

    while True:
        info(f"Stack {stack}")

        # Affichage automatique du menu depuis le dictionnaire actions.
        for key, (label, _) in actions.items():
            print(f"{key}. {label}")
        print("0. retour")

        choice = ask("Choix")
        if choice == "0":
            return

        action = actions.get(choice)
        if action:
            action[1]()
        else:
            print("Choix invalide.")


def main() -> None:
    # Point d'entree du script.
    if os.name == "nt":
        os.environ.setdefault("PYTHONUTF8", "1")

    local_os = choose_local_os()

    while True:
        info("Assistant Terraform")
        print("1. Azure")
        print("2. Proxmox")
        print("0. quitter")
        choice = ask("Choix")
        if choice == "1":
            stack_menu("azure", local_os)
        elif choice == "2":
            stack_menu("proxmox", local_os)
        elif choice == "0":
            return
        else:
            print("Choix invalide.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompu.")
    except Exception as exc:
        print(f"\nErreur: {exc}", file=sys.stderr)
        sys.exit(1)
