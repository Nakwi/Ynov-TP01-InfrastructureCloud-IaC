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
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

# Dossiers Terraform disponibles dans le projet.
STACKS = {"azure": ROOT / "azure", "proxmox": ROOT / "Proxmox"}

# Valeurs utilisees par defaut si terraform.tfvars n'existe pas encore.
DEFAULT_KEY = "~/.ssh/tp_azure_ed25519"
ADMIN_USER = "admincloud"


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


def run(args: list[str], cwd: Path | None = None, check: bool = True, capture: bool = False) -> str:
    # Lance une commande locale.
    # - args: liste de morceaux de commande, exemple ["terraform", "plan"]
    # - cwd: dossier ou lancer la commande
    # - capture: True si on veut recuperer le texte renvoye par la commande
    print("$ " + " ".join(shlex.quote(str(arg)) for arg in args))
    working_dir = str(cwd) if cwd else None
    result = subprocess.run(args, cwd=working_dir, text=True, capture_output=capture)

    if capture:
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


def terraform_cmd(stack: str, command: str) -> None:
    # Lance une commande Terraform dans le bon dossier.
    # Exemple: stack="proxmox", command="plan" -> terraform plan dans Proxmox/
    require_command("terraform")
    cwd = STACKS[stack]
    run(["terraform", command], cwd=cwd)


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


def find_proxmox_ips() -> dict[str, str]:
    # Fonction appelee par le menu pour afficher les IP des VM.
    host = ask("IP ou DNS du Proxmox", endpoint_host())
    private_key = ask("Cle SSH privee locale", get_tfvar("proxmox", "proxmox_ssh_private_key_path", DEFAULT_KEY))

    info("Recherche IP via QEMU Guest Agent")
    ips = ips_from_agent(host, private_key)
    if set(ips) != {"web", "monitoring"}:
        print("Agent incomplet, fallback nmap/MAC.")
        ips.update(ips_from_nmap(host, private_key))

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
    return ips


def stack_menu(stack: str) -> None:
    # Menu d'une stack Terraform.
    # Azure a seulement les commandes Terraform.
    # Proxmox a aussi "preparer Proxmox" et "retrouver les IP".
    actions = {
        "1": ("terraform init", lambda: terraform_cmd(stack, "init")),
        "2": ("terraform validate", lambda: terraform_cmd(stack, "validate")),
        "3": ("terraform plan", lambda: terraform_cmd(stack, "plan")),
        "4": ("terraform apply", lambda: terraform_cmd(stack, "apply")),
    }
    if stack == "proxmox":
        actions["5"] = ("preparer Proxmox", prepare_proxmox)
        actions["6"] = ("retrouver les IP des VM", find_proxmox_ips)

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
    # On garde volontairement seulement deux choix: Azure ou Proxmox.
    if os.name == "nt":
        os.environ.setdefault("PYTHONUTF8", "1")

    while True:
        info("Assistant Terraform")
        print("1. Azure")
        print("2. Proxmox")
        print("0. quitter")
        choice = ask("Choix")
        if choice == "1":
            stack_menu("azure")
        elif choice == "2":
            stack_menu("proxmox")
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
