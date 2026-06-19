#!/usr/bin/env python3
"""Interactive helper for the Azure and Proxmox Terraform stacks.

The script intentionally uses only the Python standard library plus external
commands already needed by the project: terraform, ssh, ssh-keygen, and
optionally ansible-playbook on Linux.
"""

from __future__ import annotations

import ipaddress
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
STACKS = {
    "azure": ROOT / "azure",
    "proxmox": ROOT / "Proxmox",
}
ANSIBLE_DIR = ROOT / "ansible"
ANSIBLE_INVENTORY = ANSIBLE_DIR / "inventaire.ini"
ANSIBLE_PLAYBOOK = ANSIBLE_DIR / "playbook.yaml"


def info(message: str) -> None:
    print(f"\n== {message} ==")


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or (default or "")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    value = input(f"{prompt} {suffix}: ").strip().lower()
    if not value:
        return default
    return value.startswith("y") or value.startswith("o")


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Commande introuvable: {name}")


def has_command(name: str) -> bool:
    return shutil.which(name) is not None


def run(
    args: list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = False,
    input_text: str | None = None,
    echo_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    display = " ".join(shlex.quote(str(arg)) for arg in args)
    print(f"$ {display}")
    result = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        input=input_text,
        capture_output=capture,
    )

    if capture and echo_output:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

    if check and result.returncode != 0:
        raise RuntimeError(f"La commande a echoue: {display}")

    return result


def run_capture(args: list[str], cwd: Path | None = None, check: bool = True, echo_output: bool = True) -> str:
    result = run(args, cwd=cwd, check=check, capture=True, echo_output=echo_output)
    return (result.stdout or "").strip()


def expand_user(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def ssh_args(host: str, private_key: str | None = None, batch: bool = False) -> list[str]:
    args = ["ssh", "-o", "StrictHostKeyChecking=accept-new"]
    if batch:
        args += ["-o", "BatchMode=yes"]
    if private_key:
        key = expand_user(private_key)
        if key.exists():
            args += ["-i", str(key)]
    args.append(host)
    return args


def ssh(
    host: str,
    command: str,
    private_key: str | None = None,
    batch: bool = False,
    capture: bool = False,
    check: bool = True,
    echo_output: bool = True,
) -> str:
    args = ssh_args(host, private_key=private_key, batch=batch) + [command]
    result = run(args, check=check, capture=capture, echo_output=echo_output)
    return (result.stdout or "").strip()


def read_tfvars(stack: Path) -> str:
    path = stack / "terraform.tfvars"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def get_tfvar(stack: Path, name: str, default: str = "") -> str:
    text = read_tfvars(stack)
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*(.+?)\s*$", text)
    if not match:
        return default
    value = match.group(1).strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def hcl_value(value: str | bool | int) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def set_tfvar(stack: Path, name: str, value: str | bool | int) -> None:
    path = stack / "terraform.tfvars"
    text = read_tfvars(stack)
    line = f"{name} = {hcl_value(value)}"
    pattern = rf"(?m)^\s*{re.escape(name)}\s*=.*$"

    if re.search(pattern, text):
        text = re.sub(pattern, line, text)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += line + "\n"

    path.write_text(text, encoding="utf-8")


def terraform(stack_name: str, command: str) -> None:
    stack = STACKS[stack_name]
    require_command("terraform")

    if command == "apply-auto":
        run(["terraform", "apply", "-auto-approve"], cwd=stack)
        return

    run(["terraform", command], cwd=stack)


def terraform_outputs(stack_name: str) -> dict[str, Any]:
    stack = STACKS[stack_name]
    require_command("terraform")
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=str(stack),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def choose_control_os() -> str:
    detected = "windows" if platform.system().lower().startswith("win") else "linux"
    while True:
        value = ask("Systeme de ce PC pour les commandes locales (windows/linux)", detected).lower()
        if value in ("windows", "linux"):
            if value == "windows":
                print("Ansible n'est pas compatible comme control node Windows natif. Terraform/SSH restent OK.")
            return value
        print("Choisis windows ou linux.")


def ensure_ssh_key(private_key: str) -> None:
    require_command("ssh-keygen")
    key = expand_user(private_key)
    public_key = Path(str(key) + ".pub")
    key.parent.mkdir(parents=True, exist_ok=True)

    if key.exists() and public_key.exists():
        print(f"Cle SSH deja presente: {key}")
        return

    run(["ssh-keygen", "-t", "ed25519", "-f", str(key), "-C", "tp-proxmox", "-N", ""])


def install_root_key(host: str, private_key: str) -> None:
    public_key_path = Path(str(expand_user(private_key)) + ".pub")
    public_key = public_key_path.read_text(encoding="utf-8").strip()
    quoted_key = shell_quote(public_key)
    remote = (
        "mkdir -p /root/.ssh && chmod 700 /root/.ssh && "
        "touch /root/.ssh/authorized_keys && "
        f"(grep -qxF -- {quoted_key} /root/.ssh/authorized_keys || "
        f"echo {quoted_key} >> /root/.ssh/authorized_keys) && "
        "chmod 600 /root/.ssh/authorized_keys && systemctl enable --now ssh"
    )

    print("Si la cle n'est pas encore autorisee, SSH peut demander le mot de passe root Proxmox.")
    ssh(f"root@{host}", remote, private_key=private_key)
    ssh(f"root@{host}", "echo ok", private_key=private_key, batch=True)


def prepare_proxmox_node(host: str, private_key: str, datastore: str) -> str:
    store = shell_quote(datastore)
    snippet_ref = shell_quote(f"{datastore}:snippets")
    remote = "; ".join(
        [
            "set -e",
            "systemctl enable --now ssh",
            f"pvesm set {store} --content iso,vztmpl,backup,import,snippets",
            f"snippet_dir=$(pvesm path {snippet_ref} 2>/dev/null || true)",
            'if [ -z "$snippet_dir" ]; then snippet_dir=/var/lib/vz/snippets; fi',
            'mkdir -p "$snippet_dir"',
            'chmod 755 "$snippet_dir"',
            "if ! command -v nmap >/dev/null 2>&1; then apt-get update -y && apt-get install -y nmap; fi",
            "hostname",
        ]
    )
    output = ssh(f"root@{host}", remote, private_key=private_key, batch=True, capture=True)
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else "pve"


def ensure_api_user(
    host: str,
    private_key: str,
    api_user: str,
    token_id: str,
    recreate_token: bool,
) -> tuple[str, str | None]:
    user = shell_quote(api_user)
    token = shell_quote(token_id)
    remote = "; ".join(
        [
            f"pveum user add {user} --comment 'Terraform user' 2>/dev/null || true",
            f"pveum acl modify / --users {user} --roles Administrator",
            f"pveum user token list {user} || true",
        ]
    )
    ssh(f"root@{host}", remote, private_key=private_key, batch=True)

    if not recreate_token:
        return f"{api_user}!{token_id}", None

    remote_token = "; ".join(
        [
            f"pveum user token remove {user} {token} 2>/dev/null || true",
            f"pveum user token add {user} {token} --privsep 0 --output-format json",
        ]
    )
    output = ssh(
        f"root@{host}",
        remote_token,
        private_key=private_key,
        batch=True,
        capture=True,
        echo_output=False,
    )

    json_start = output.find("{")
    if json_start >= 0:
        data = json.loads(output[json_start:])
        return data["full-tokenid"], data["value"]

    match = re.search(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        output,
    )
    if not match:
        raise RuntimeError("Impossible de recuperer le secret du token API.")
    return f"{api_user}!{token_id}", match.group(0)


def prepare_proxmox() -> None:
    stack = STACKS["proxmox"]
    host = ask("IP ou DNS du Proxmox", endpoint_host(stack))
    private_key = ask("Chemin de la cle SSH privee locale", get_tfvar(stack, "proxmox_ssh_private_key_path", "~/.ssh/tp_azure_ed25519"))
    api_user = ask("User API Proxmox", "terraform@pve")
    token_id = ask("Token ID Proxmox", "provider")
    bridge = ask("Bridge reseau des VM", get_tfvar(stack, "network_bridge", "vmbr0"))
    snippets_datastore = ask("Datastore snippets/import", get_tfvar(stack, "snippets_datastore_id", "local"))
    image_datastore = ask("Datastore image Debian", get_tfvar(stack, "image_datastore_id", "local"))
    vm_datastore = ask("Datastore disques VM", get_tfvar(stack, "vm_datastore_id", "local-lvm"))
    cloud_init_datastore = ask("Datastore disque cloud-init", get_tfvar(stack, "cloud_init_datastore_id", "local-lvm"))
    recreate_token = ask_yes_no("Creer/recreer le token API ?", False)

    info("SSH")
    ensure_ssh_key(private_key)
    install_root_key(host, private_key)

    info("Preparation du node")
    node_name = prepare_proxmox_node(host, private_key, snippets_datastore)
    print(f"Node detecte: {node_name}")

    info("API Proxmox")
    api_token_id, token_secret = ensure_api_user(host, private_key, api_user, token_id, recreate_token)

    info("Mise a jour terraform.tfvars")
    set_tfvar(stack, "proxmox_endpoint", f"https://{host}:8006/")
    set_tfvar(stack, "proxmox_ssh_username", "root")
    set_tfvar(stack, "proxmox_ssh_agent", False)
    set_tfvar(stack, "proxmox_ssh_private_key_path", private_key)
    set_tfvar(stack, "ssh_public_key_path", f"{private_key}.pub")
    set_tfvar(stack, "proxmox_node_name", node_name)
    set_tfvar(stack, "network_bridge", bridge)
    set_tfvar(stack, "snippets_datastore_id", snippets_datastore)
    set_tfvar(stack, "image_datastore_id", image_datastore)
    set_tfvar(stack, "vm_datastore_id", vm_datastore)
    set_tfvar(stack, "cloud_init_datastore_id", cloud_init_datastore)
    set_tfvar(stack, "proxmox_api_token_id", api_token_id)
    if token_secret:
        set_tfvar(stack, "proxmox_api_token", token_secret)
    set_tfvar(stack, "qemu_guest_agent_enabled", True)
    print("terraform.tfvars mis a jour.")


def endpoint_host(stack: Path) -> str:
    endpoint = get_tfvar(stack, "proxmox_endpoint", "https://192.168.1.126:8006/")
    match = re.search(r"https?://([^/:]+)", endpoint)
    return match.group(1) if match else "192.168.1.126"


def vm_ids(stack: Path) -> dict[str, str]:
    return {
        "web": get_tfvar(stack, "web_vm_id", "201"),
        "monitoring": get_tfvar(stack, "monitoring_vm_id", "202"),
    }


def configured_private_key(stack: Path) -> str:
    return get_tfvar(stack, "proxmox_ssh_private_key_path", "~/.ssh/tp_azure_ed25519")


def ips_from_guest_agent(host: str, private_key: str, ids: dict[str, str]) -> dict[str, str]:
    ips: dict[str, str] = {}
    node = get_tfvar(STACKS["proxmox"], "proxmox_node_name", "pve")

    for role, vmid in ids.items():
        commands = [
            f"pvesh get /nodes/{node}/qemu/{vmid}/agent/network-get-interfaces --output-format json",
            f"qm guest cmd {vmid} network-get-interfaces",
        ]
        output = ""
        for command in commands:
            output = ssh(
                f"root@{host}",
                command,
                private_key=private_key,
                batch=True,
                capture=True,
                check=False,
            )
            if output and "error" not in output.lower() and "not running" not in output.lower():
                break

        try:
            data = json.loads(output)
        except Exception:
            data = None

        candidates = extract_ips_from_agent_json(data) if data else []
        if candidates:
            ips[role] = candidates[0]

    return ips


def extract_ips_from_agent_json(data: Any) -> list[str]:
    found: list[str] = []

    if isinstance(data, dict):
        iterable = data.get("result", data)
        if isinstance(iterable, dict):
            iterable = iterable.get("result", iterable.get("interfaces", []))
    else:
        iterable = data

    if not isinstance(iterable, list):
        return found

    for iface in iterable:
        if not isinstance(iface, dict):
            continue
        for item in iface.get("ip-addresses", []) or []:
            ip = item.get("ip-address")
            ip_type = item.get("ip-address-type")
            if not ip or ip_type not in (None, "ipv4"):
                continue
            if ip.startswith("127."):
                continue
            found.append(ip)

    return found


def mac_from_config(config: str) -> str | None:
    match = re.search(r"net0:\s+\S+=([0-9A-Fa-f:]{17}),", config)
    return match.group(1).upper() if match else None


def scan_ips_by_mac(host: str, private_key: str, ids: dict[str, str]) -> dict[str, str]:
    macs: dict[str, str] = {}

    for role, vmid in ids.items():
        config = ssh(f"root@{host}", f"qm config {vmid}", private_key=private_key, batch=True, capture=True)
        mac = mac_from_config(config)
        if mac:
            macs[role] = mac

    subnet_output = ssh(
        f"root@{host}",
        "ip -4 route show dev vmbr0 proto kernel scope link | awk '{print $1; exit}'",
        private_key=private_key,
        batch=True,
        capture=True,
        check=False,
    )
    subnet = subnet_output.strip() or "192.168.1.0/24"
    try:
        ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        subnet = ask("Subnet a scanner", "192.168.1.0/24")

    scan = ssh(f"root@{host}", f"nmap -sn {subnet}", private_key=private_key, batch=True, capture=True)
    current_ip = ""
    found: dict[str, str] = {}

    for line in scan.splitlines():
        report = re.search(r"Nmap scan report for .*\((\d+\.\d+\.\d+\.\d+)\)", line)
        if not report:
            report = re.search(r"Nmap scan report for (\d+\.\d+\.\d+\.\d+)", line)
        if report:
            current_ip = report.group(1)
            continue

        mac_match = re.search(r"MAC Address:\s+([0-9A-Fa-f:]{17})", line)
        if mac_match and current_ip:
            mac = mac_match.group(1).upper()
            for role, expected_mac in macs.items():
                if mac == expected_mac:
                    found[role] = current_ip

    return found


def find_proxmox_ips() -> dict[str, str]:
    stack = STACKS["proxmox"]
    host = ask("IP ou DNS du Proxmox", endpoint_host(stack))
    private_key = ask("Chemin de la cle SSH privee locale", configured_private_key(stack))
    ids = vm_ids(stack)

    info("Tentative via QEMU Guest Agent")
    ips = ips_from_guest_agent(host, private_key, ids)

    missing = [role for role in ids if role not in ips]
    if missing:
        print("Agent indisponible ou incomplet, fallback scan nmap/MAC.")
        scanned = scan_ips_by_mac(host, private_key, ids)
        ips.update(scanned)

    info("IP trouvees")
    for role in ("web", "monitoring"):
        ip = ips.get(role, "<non trouvee>")
        print(f"{role:10} {ip}")
        if ip != "<non trouvee>":
            print(f"  ssh -i {private_key} admincloud@{ip}")

    web_ip = ips.get("web")
    monitoring_ip = ips.get("monitoring")
    if web_ip:
        print(f"  web_url: http://{web_ip}")
    if monitoring_ip:
        print(f"  uptime_kuma_url: http://{monitoring_ip}:3001")

    return ips


def azure_ips_from_outputs() -> dict[str, str]:
    outputs = terraform_outputs("azure")
    values = {name: data.get("value") for name, data in outputs.items()}
    ips: dict[str, str] = {}

    if values.get("web_public_ip"):
        ips["web"] = str(values["web_public_ip"])
    if values.get("monitoring_public_ip"):
        ips["monitoring"] = str(values["monitoring_public_ip"])

    return ips


def proxmox_ips_for_ansible() -> dict[str, str]:
    stack = STACKS["proxmox"]
    host = ask("IP ou DNS du Proxmox", endpoint_host(stack))
    private_key = ask("Chemin de la cle SSH privee locale", configured_private_key(stack))
    ids = vm_ids(stack)

    info("Tentative via QEMU Guest Agent")
    ips = ips_from_guest_agent(host, private_key, ids)
    missing = [role for role in ids if role not in ips]

    if missing:
        print("Agent indisponible ou incomplet, fallback scan nmap/MAC.")
        ips.update(scan_ips_by_mac(host, private_key, ids))

    return ips


def private_key_for_stack(stack_name: str) -> str:
    stack = STACKS[stack_name]

    if stack_name == "proxmox":
        return configured_private_key(stack)

    public_key = get_tfvar(stack, "ssh_public_key_path", "~/.ssh/tp_azure_ed25519.pub")
    return public_key[:-4] if public_key.endswith(".pub") else public_key


def ansible_host_aliases() -> dict[str, str]:
    aliases = {"web": "web01", "monitoring": "monitoring01"}

    if not ANSIBLE_INVENTORY.exists():
        return aliases

    current_group = ""
    for raw_line in ANSIBLE_INVENTORY.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_group = line.strip("[]")
            continue
        if current_group in aliases and not current_group.endswith(":vars"):
            aliases[current_group] = line.split()[0]

    return aliases


def write_ansible_inventory(ips: dict[str, str], private_key: str) -> None:
    missing = [role for role in ("web", "monitoring") if role not in ips or not ips[role]]
    if missing:
        raise RuntimeError(f"IP manquante pour Ansible: {', '.join(missing)}")

    aliases = ansible_host_aliases()
    ANSIBLE_DIR.mkdir(parents=True, exist_ok=True)

    content = f"""[web]
{aliases["web"]} ansible_host={ips["web"]} ansible_user=admincloud

[monitoring]
{aliases["monitoring"]} ansible_host={ips["monitoring"]} ansible_user=admincloud

[all:vars]
ansible_ssh_private_key_file={private_key}
ansible_python_interpreter=/usr/bin/python3
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
"""

    ANSIBLE_INVENTORY.write_text(content, encoding="utf-8")
    print(f"Inventaire Ansible mis a jour: {ANSIBLE_INVENTORY}")
    print(f"  {aliases['web']} -> {ips['web']}")
    print(f"  {aliases['monitoring']} -> {ips['monitoring']}")


def install_ansible_linux() -> None:
    if has_command("ansible-playbook"):
        print("Ansible est deja installe.")
        run(["ansible-playbook", "--version"], check=False)
    else:
        if not ask_yes_no("Ansible est absent. Installer Ansible sur ce Linux ?", True):
            raise RuntimeError("Ansible absent.")

        if has_command("apt-get"):
            run(["sudo", "apt-get", "update"])
            run(["sudo", "apt-get", "install", "-y", "ansible"])
        elif has_command("dnf"):
            run(["sudo", "dnf", "install", "-y", "ansible"])
        elif has_command("yum"):
            run(["sudo", "yum", "install", "-y", "ansible"])
        elif has_command("pacman"):
            run(["sudo", "pacman", "-Sy", "--noconfirm", "ansible"])
        else:
            raise RuntimeError("Gestionnaire de paquets non reconnu. Installe Ansible manuellement.")

    if has_command("ansible-galaxy"):
        run(["ansible-galaxy", "collection", "install", "community.docker"], check=False)


def ensure_ansible_supported(control_os: str) -> bool:
    if control_os == "windows":
        print("Ansible n'est pas compatible depuis Windows natif comme control node.")
        print("Tu peux utiliser le reste du script, ou lancer Ansible depuis Linux/WSL separement.")
        return False
    return True


def generate_ansible_inventory(stack_name: str) -> None:
    if stack_name == "azure":
        ips = azure_ips_from_outputs()
    else:
        ips = proxmox_ips_for_ansible()

    private_key = ask("Cle privee SSH pour Ansible", private_key_for_stack(stack_name))
    write_ansible_inventory(ips, private_key)


def run_ansible_playbook(control_os: str, stack_name: str) -> None:
    if not ensure_ansible_supported(control_os):
        return

    install_ansible_linux()

    if not ANSIBLE_INVENTORY.exists() or inventory_has_placeholders():
        print("Inventaire absent ou incomplet, generation maintenant.")
        generate_ansible_inventory(stack_name)
    elif ask_yes_no("Regenerer l'inventaire avec les IP actuelles avant Ansible ?", True):
        generate_ansible_inventory(stack_name)

    private_key = get_inventory_private_key()
    if private_key:
        key_path = expand_user(private_key)
        if key_path.exists():
            try:
                key_path.chmod(0o600)
            except OSError:
                pass

    run(["ansible-playbook", "-i", str(ANSIBLE_INVENTORY), str(ANSIBLE_PLAYBOOK)], cwd=ROOT)


def get_inventory_private_key() -> str:
    if not ANSIBLE_INVENTORY.exists():
        return ""

    for raw_line in ANSIBLE_INVENTORY.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("ansible_ssh_private_key_file="):
            return line.split("=", 1)[1]
    return ""


def inventory_has_placeholders() -> bool:
    if not ANSIBLE_INVENTORY.exists():
        return True
    text = ANSIBLE_INVENTORY.read_text(encoding="utf-8")
    return "IP_DE_LA_VM_WEB" in text or "IP_DE_LA_VM_MONITORING" in text


def show_outputs(stack_name: str) -> None:
    outputs = terraform_outputs(stack_name)
    if not outputs:
        print("Aucun output Terraform disponible.")
        return

    for name, data in outputs.items():
        print(f"{name}: {data.get('value')}")


def stack_menu(stack_name: str, control_os: str) -> None:
    while True:
        info(f"Stack {stack_name}")
        print("1. terraform init")
        print("2. terraform validate")
        print("3. terraform plan")
        print("4. terraform apply")
        print("5. terraform destroy")
        print("6. afficher les outputs")
        print("7. generer inventaire Ansible")
        print("8. installer/verifier Ansible")
        print("9. lancer playbook Ansible")
        if stack_name == "proxmox":
            print("10. preparer Proxmox")
            print("11. retrouver les IP des VM")
        print("0. retour")
        choice = ask("Choix")

        if choice == "1":
            terraform(stack_name, "init")
        elif choice == "2":
            terraform(stack_name, "validate")
        elif choice == "3":
            terraform(stack_name, "plan")
        elif choice == "4":
            terraform(stack_name, "apply")
        elif choice == "5":
            terraform(stack_name, "destroy")
        elif choice == "6":
            show_outputs(stack_name)
        elif choice == "7":
            if ensure_ansible_supported(control_os):
                generate_ansible_inventory(stack_name)
        elif choice == "8":
            if ensure_ansible_supported(control_os):
                install_ansible_linux()
        elif choice == "9":
            run_ansible_playbook(control_os, stack_name)
        elif stack_name == "proxmox" and choice == "10":
            prepare_proxmox()
        elif stack_name == "proxmox" and choice == "11":
            find_proxmox_ips()
        elif choice == "0":
            return
        else:
            print("Choix invalide.")


def main() -> None:
    if platform.system().lower().startswith("win"):
        os.environ.setdefault("PYTHONUTF8", "1")

    control_os = choose_control_os()

    while True:
        info("Assistant Terraform")
        print("1. Azure")
        print("2. Proxmox")
        print("0. quitter")
        choice = ask("Choix")

        if choice == "1":
            stack_menu("azure", control_os)
        elif choice == "2":
            stack_menu("proxmox", control_os)
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
