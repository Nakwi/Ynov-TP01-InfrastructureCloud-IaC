#!/usr/bin/env python3
"""Small graphical launcher for the Terraform/Proxmox/Ansible assistant."""

from __future__ import annotations

import contextlib
import os
import platform
import queue
import threading
import traceback
from typing import Callable

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import terraform_assistant as assistant


PALETTE = {
    "bg": "#101624",
    "panel": "#172033",
    "panel_alt": "#1f2a42",
    "border": "#31415f",
    "text": "#edf2ff",
    "muted": "#aab8d4",
    "accent": "#4f8cff",
    "accent_hover": "#72a4ff",
    "success": "#2fbf71",
    "warning": "#f0b429",
    "danger": "#ef5b5b",
    "terminal": "#07111f",
    "terminal_text": "#d9e7ff",
}


class QueueWriter:
    def __init__(self, output_queue: queue.Queue[str]) -> None:
        self.output_queue = output_queue

    def write(self, text: str) -> int:
        if text:
            self.output_queue.put(text)
        return len(text)

    def flush(self) -> None:
        pass


class TerraformGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Assistant IaC - Terraform / Proxmox / Ansible")
        self.geometry("1180x820")
        self.minsize(1040, 720)
        self.configure(bg=PALETTE["bg"])

        self.output_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.action_buttons: list[ttk.Button] = []
        self.current_snapshot: dict[str, str | bool] = {}

        self.stack_var = tk.StringVar(value="proxmox")
        detected_os = "windows" if platform.system().lower().startswith("win") else "linux"
        self.control_os_var = tk.StringVar(value=detected_os)
        self.apply_auto_var = tk.BooleanVar(value=True)
        self.include_ansible_var = tk.BooleanVar(value=True)
        self.prepare_proxmox_var = tk.BooleanVar(value=True)
        self.recreate_token_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Pret")

        self.proxmox_vars: dict[str, tk.StringVar] = {}

        self._configure_style()
        self._build_ui()
        self._load_proxmox_defaults()
        self.after(100, self._drain_output)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        with contextlib.suppress(tk.TclError):
            style.theme_use("clam")

        style.configure(".", font=("Segoe UI", 10))
        style.configure("Root.TFrame", background=PALETTE["bg"])
        style.configure("Header.TFrame", background=PALETTE["panel"])
        style.configure("Surface.TFrame", background=PALETTE["panel"])
        style.configure("Card.TFrame", background=PALETTE["panel_alt"], relief="flat")
        style.configure("Footer.TFrame", background=PALETTE["bg"])

        style.configure("Title.TLabel", background=PALETTE["panel"], foreground=PALETTE["text"], font=("Segoe UI Semibold", 20))
        style.configure("Subtitle.TLabel", background=PALETTE["panel"], foreground=PALETTE["muted"], font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=PALETTE["panel_alt"], foreground=PALETTE["text"], font=("Segoe UI Semibold", 12))
        style.configure("Surface.TLabel", background=PALETTE["panel"], foreground=PALETTE["text"])
        style.configure("Muted.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"])
        style.configure("Status.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"], font=("Segoe UI Semibold", 10))

        style.configure("TNotebook", background=PALETTE["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=PALETTE["panel"], foreground=PALETTE["muted"], padding=(18, 8), borderwidth=0)
        style.map(
            "TNotebook.Tab",
            background=[("selected", PALETTE["panel_alt"]), ("active", PALETTE["panel_alt"])],
            foreground=[("selected", PALETTE["text"]), ("active", PALETTE["text"])],
        )

        style.configure("Panel.TLabelframe", background=PALETTE["panel_alt"], bordercolor=PALETTE["border"], relief="solid")
        style.configure("Panel.TLabelframe.Label", background=PALETTE["panel_alt"], foreground=PALETTE["text"], font=("Segoe UI Semibold", 11))

        style.configure("TLabel", background=PALETTE["panel"], foreground=PALETTE["text"])
        style.configure("TCheckbutton", background=PALETTE["panel"], foreground=PALETTE["text"], focuscolor=PALETTE["panel"])
        style.configure("TRadiobutton", background=PALETTE["panel"], foreground=PALETTE["text"], focuscolor=PALETTE["panel"])
        style.map(
            "TCheckbutton",
            background=[("active", PALETTE["panel"])],
            foreground=[("disabled", PALETTE["muted"]), ("active", PALETTE["text"])],
        )
        style.map(
            "TRadiobutton",
            background=[("active", PALETTE["panel"])],
            foreground=[("disabled", PALETTE["muted"]), ("active", PALETTE["text"])],
        )

        style.configure(
            "TEntry",
            fieldbackground="#eef3ff",
            foreground="#172033",
            bordercolor=PALETTE["border"],
            lightcolor=PALETTE["accent"],
            darkcolor=PALETTE["border"],
            padding=(8, 5),
        )
        style.configure(
            "TCombobox",
            fieldbackground="#eef3ff",
            foreground="#172033",
            arrowcolor=PALETTE["accent"],
            bordercolor=PALETTE["border"],
            padding=(6, 4),
        )

        self._configure_button_style("Action.TButton", PALETTE["panel_alt"], PALETTE["text"], PALETTE["border"])
        self._configure_button_style("Primary.TButton", PALETTE["accent"], "#ffffff", PALETTE["accent_hover"])
        self._configure_button_style("Success.TButton", PALETTE["success"], "#062312", "#48d68b")
        self._configure_button_style("Warning.TButton", PALETTE["warning"], "#2f2100", "#f7c94a")
        self._configure_button_style("Danger.TButton", PALETTE["danger"], "#ffffff", "#ff7777")
        self._configure_button_style("Ghost.TButton", PALETTE["panel"], PALETTE["text"], PALETTE["border"])

    def _configure_button_style(self, name: str, bg: str, fg: str, active_bg: str) -> None:
        style = ttk.Style(self)
        style.configure(name, background=bg, foreground=fg, borderwidth=0, focusthickness=0, padding=(12, 8), font=("Segoe UI Semibold", 10))
        style.map(
            name,
            background=[("disabled", "#2a344c"), ("active", active_bg), ("pressed", active_bg)],
            foreground=[("disabled", "#73809c")],
        )

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14, style="Root.TFrame")
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)

        header = ttk.Frame(root, padding=16, style="Header.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        title_area = ttk.Frame(header, style="Header.TFrame")
        title_area.grid(row=0, column=0, sticky="w")
        ttk.Label(title_area, text="Assistant IaC", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            title_area,
            text="Terraform, Proxmox et Ansible dans une seule console graphique.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        selector = ttk.Frame(header, style="Header.TFrame")
        selector.grid(row=0, column=1, sticky="e")
        ttk.Label(selector, text="Stack").grid(row=0, column=0, padx=(0, 8), sticky="e")
        ttk.Radiobutton(selector, text="Proxmox", variable=self.stack_var, value="proxmox").grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(selector, text="Azure", variable=self.stack_var, value="azure").grid(row=0, column=2, sticky="w", padx=(4, 0))

        ttk.Label(selector, text="Poste local").grid(row=0, column=3, padx=(18, 8), sticky="e")
        os_select = ttk.Combobox(
            selector,
            textvariable=self.control_os_var,
            values=("windows", "linux"),
            width=12,
            state="readonly",
        )
        os_select.grid(row=0, column=4, sticky="e")

        options = ttk.Frame(root, padding=(12, 10), style="Surface.TFrame")
        options.grid(row=1, column=0, sticky="ew", pady=(10, 8))
        ttk.Checkbutton(options, text="Preparer Proxmox dans le parcours complet", variable=self.prepare_proxmox_var).pack(side=tk.LEFT)
        ttk.Checkbutton(options, text="Terraform apply -auto-approve", variable=self.apply_auto_var).pack(side=tk.LEFT, padx=(18, 0))
        ttk.Checkbutton(options, text="Inclure Ansible", variable=self.include_ansible_var).pack(side=tk.LEFT, padx=(18, 0))

        notebook = ttk.Notebook(root)
        notebook.grid(row=2, column=0, sticky="ew")
        notebook.add(self._build_actions_tab(notebook), text="Actions")
        notebook.add(self._build_proxmox_tab(notebook), text="Proxmox")

        log_frame = ttk.LabelFrame(root, text="Logs", style="Panel.TLabelframe", padding=10)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 8))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        self.log = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=18,
            bg=PALETTE["terminal"],
            fg=PALETTE["terminal_text"],
            insertbackground=PALETTE["terminal_text"],
            selectbackground=PALETTE["accent"],
            relief=tk.FLAT,
            borderwidth=0,
            font=("Consolas", 10),
            padx=12,
            pady=10,
        )
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log.configure(state=tk.DISABLED)

        footer = ttk.Frame(root, style="Footer.TFrame")
        footer.grid(row=4, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Effacer les logs", command=self.clear_logs, style="Ghost.TButton").grid(row=0, column=1, padx=(8, 0))
        ttk.Button(footer, text="Quitter", command=self.destroy, style="Danger.TButton").grid(row=0, column=2, padx=(8, 0))

    def _build_actions_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(parent, padding=12, style="Root.TFrame")
        for index in range(4):
            tab.columnconfigure(index, weight=1)

        groups = [
            (
                "Terraform",
                PALETTE["accent"],
                [
                    ("Init", lambda: self.run_task("terraform init", self.action_terraform_init), "Action.TButton"),
                    ("Validate", lambda: self.run_task("terraform validate", self.action_terraform_validate), "Action.TButton"),
                    ("Plan", lambda: self.run_task("terraform plan", self.action_terraform_plan), "Primary.TButton"),
                    ("Apply", self.confirm_apply, "Warning.TButton"),
                    ("Destroy", self.confirm_destroy, "Danger.TButton"),
                    ("Outputs", lambda: self.run_task("terraform outputs", self.action_outputs), "Action.TButton"),
                ],
            ),
            (
                "Proxmox",
                PALETTE["success"],
                [
                    ("Preparer Proxmox", lambda: self.run_task("preparation Proxmox", self.action_prepare_proxmox), "Success.TButton"),
                    ("Retrouver IP des VM", lambda: self.run_task("recherche IP", self.action_find_ips), "Action.TButton"),
                ],
            ),
            (
                "Ansible",
                PALETTE["warning"],
                [
                    ("Generer inventaire", lambda: self.run_task("inventaire Ansible", self.action_generate_inventory), "Action.TButton"),
                    ("Installer/verifier Ansible", lambda: self.run_task("installation Ansible", self.action_install_ansible), "Action.TButton"),
                    ("Lancer playbook", lambda: self.run_task("playbook Ansible", self.action_run_ansible), "Warning.TButton"),
                ],
            ),
            (
                "Workflow",
                "#a78bfa",
                [
                    ("Tout derouler", self.confirm_full_workflow, "Primary.TButton"),
                ],
            ),
        ]

        for col, (title, accent, actions) in enumerate(groups):
            frame = ttk.Frame(tab, padding=10, style="Card.TFrame")
            frame.grid(row=0, column=col, sticky="nsew", padx=5, pady=5)
            frame.columnconfigure(0, weight=1)
            tk.Frame(frame, bg=accent, height=3).grid(row=0, column=0, sticky="ew", pady=(0, 10))
            ttk.Label(frame, text=title, style="Section.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 8))
            for row, (label, command, button_style) in enumerate(actions, start=2):
                button = ttk.Button(frame, text=label, command=command, style=button_style)
                button.grid(row=row, column=0, sticky="ew", pady=3)
                self.action_buttons.append(button)

        return tab

    def _build_proxmox_tab(self, parent: ttk.Notebook) -> ttk.Frame:
        tab = ttk.Frame(parent, padding=14, style="Surface.TFrame")
        tab.columnconfigure(1, weight=1)
        tab.columnconfigure(3, weight=1)

        fields = [
            ("host", "IP/DNS Proxmox"),
            ("private_key", "Cle SSH privee"),
            ("api_user", "User API"),
            ("token_id", "Token ID"),
            ("bridge", "Bridge reseau"),
            ("snippets_datastore", "Datastore snippets/import"),
            ("image_datastore", "Datastore image Debian"),
            ("vm_datastore", "Datastore disques VM"),
            ("cloud_init_datastore", "Datastore cloud-init"),
        ]

        for index, (key, label) in enumerate(fields):
            row = index // 2
            col = (index % 2) * 2
            ttk.Label(tab, text=label, style="Surface.TLabel").grid(row=row, column=col, sticky="w", padx=(0, 8), pady=4)
            var = tk.StringVar()
            self.proxmox_vars[key] = var
            entry = ttk.Entry(tab, textvariable=var)
            entry.grid(row=row, column=col + 1, sticky="ew", pady=4, padx=(0, 16))
            if key == "private_key":
                ttk.Button(tab, text="...", width=3, command=self.browse_private_key).grid(row=row, column=col + 1, sticky="e", pady=4, padx=(0, 18))

        ttk.Checkbutton(tab, text="Creer/recreer le token API", variable=self.recreate_token_var).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        ttk.Button(tab, text="Recharger depuis terraform.tfvars", command=self._load_proxmox_defaults, style="Ghost.TButton").grid(
            row=5, column=2, columnspan=2, sticky="e", pady=(10, 0)
        )

        return tab

    def _load_proxmox_defaults(self) -> None:
        stack = assistant.STACKS["proxmox"]
        defaults = {
            "host": assistant.endpoint_host(stack),
            "private_key": assistant.get_tfvar(stack, "proxmox_ssh_private_key_path", "~/.ssh/tp_azure_ed25519"),
            "api_user": "terraform@pve",
            "token_id": "provider",
            "bridge": assistant.get_tfvar(stack, "network_bridge", "vmbr0"),
            "snippets_datastore": assistant.get_tfvar(stack, "snippets_datastore_id", "local"),
            "image_datastore": assistant.get_tfvar(stack, "image_datastore_id", "local"),
            "vm_datastore": assistant.get_tfvar(stack, "vm_datastore_id", "local-lvm"),
            "cloud_init_datastore": assistant.get_tfvar(stack, "cloud_init_datastore_id", "local-lvm"),
        }
        for key, value in defaults.items():
            self.proxmox_vars[key].set(value)

    def browse_private_key(self) -> None:
        path = filedialog.askopenfilename(title="Choisir la cle SSH privee")
        if path:
            self.proxmox_vars["private_key"].set(path)

    def selected_stack(self) -> str:
        if "stack" in self.current_snapshot:
            return str(self.current_snapshot["stack"])
        return self.stack_var.get()

    def selected_control_os(self) -> str:
        if "control_os" in self.current_snapshot:
            return str(self.current_snapshot["control_os"])
        return self.control_os_var.get()

    def form_value(self, key: str) -> str:
        if key in self.current_snapshot:
            return str(self.current_snapshot[key])
        return self.proxmox_vars[key].get()

    def option_value(self, key: str, fallback: tk.BooleanVar) -> bool:
        if key in self.current_snapshot:
            return bool(self.current_snapshot[key])
        return fallback.get()

    def snapshot_state(self) -> dict[str, str | bool]:
        snapshot: dict[str, str | bool] = {
            "stack": self.stack_var.get(),
            "control_os": self.control_os_var.get(),
            "apply_auto": self.apply_auto_var.get(),
            "include_ansible": self.include_ansible_var.get(),
            "prepare_proxmox": self.prepare_proxmox_var.get(),
            "recreate_token": self.recreate_token_var.get(),
        }
        for key, var in self.proxmox_vars.items():
            snapshot[key] = var.get()
        return snapshot

    def run_task(self, title: str, func: Callable[[], None]) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Action en cours", "Une action est deja en cours.")
            return

        self.current_snapshot = self.snapshot_state()
        self.status_var.set(f"En cours: {title}")
        self._set_buttons_state(tk.DISABLED)

        def target() -> None:
            writer = QueueWriter(self.output_queue)
            try:
                self.output_queue.put(f"\n== {title} ==\n")
                with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                    func()
                self.output_queue.put(f"\n== Termine: {title} ==\n")
                self.output_queue.put("__STATUS__:Pret\n")
            except SystemExit:
                self.output_queue.put("\nAction interrompue.\n")
                self.output_queue.put("__STATUS__:Pret\n")
            except Exception:
                self.output_queue.put("\nErreur pendant l'action:\n")
                self.output_queue.put(traceback.format_exc())
                self.output_queue.put("__STATUS__:Erreur\n")
            finally:
                self.output_queue.put("__ENABLE_BUTTONS__\n")

        self.worker = threading.Thread(target=target, daemon=True)
        self.worker.start()

    def _drain_output(self) -> None:
        while True:
            try:
                text = self.output_queue.get_nowait()
            except queue.Empty:
                break

            if text == "__ENABLE_BUTTONS__\n":
                self._set_buttons_state(tk.NORMAL)
                continue
            if text.startswith("__STATUS__:"):
                self.status_var.set(text.split(":", 1)[1].strip())
                continue

            self.log.configure(state=tk.NORMAL)
            self.log.insert(tk.END, text)
            self.log.see(tk.END)
            self.log.configure(state=tk.DISABLED)

        self.after(100, self._drain_output)

    def _set_buttons_state(self, state: str) -> None:
        for button in self.action_buttons:
            button.configure(state=state)

    def clear_logs(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)

    def confirm_apply(self) -> None:
        if not messagebox.askyesno("Terraform apply", "Lancer Terraform apply sur la stack selectionnee ?"):
            return
        self.run_task("terraform apply", self.action_terraform_apply)

    def confirm_destroy(self) -> None:
        if not messagebox.askyesno("Terraform destroy", "Detruire les ressources Terraform de cette stack ?"):
            return
        self.run_task("terraform destroy", self.action_terraform_destroy)

    def confirm_full_workflow(self) -> None:
        if self.apply_auto_var.get():
            ok = messagebox.askyesno(
                "Parcours complet",
                "Le parcours complet va lancer terraform apply -auto-approve. Continuer ?",
            )
            if not ok:
                return
        self.run_task("parcours complet", self.action_full_workflow)

    def action_terraform_init(self) -> None:
        assistant.terraform(self.selected_stack(), "init")

    def action_terraform_validate(self) -> None:
        assistant.terraform(self.selected_stack(), "validate")

    def action_terraform_plan(self) -> None:
        assistant.terraform(self.selected_stack(), "plan")

    def action_terraform_apply(self) -> None:
        command = "apply-auto" if self.option_value("apply_auto", self.apply_auto_var) else "apply"
        assistant.terraform(self.selected_stack(), command)

    def action_terraform_destroy(self) -> None:
        assistant.terraform(self.selected_stack(), "destroy")

    def action_outputs(self) -> None:
        assistant.show_outputs(self.selected_stack())

    def action_prepare_proxmox(self) -> None:
        self.prepare_proxmox_from_form()

    def prepare_proxmox_from_form(self) -> None:
        stack = assistant.STACKS["proxmox"]
        host = self.form_value("host").strip()
        private_key = self.form_value("private_key").strip()
        api_user = self.form_value("api_user").strip() or "terraform@pve"
        token_id = self.form_value("token_id").strip() or "provider"
        bridge = self.form_value("bridge").strip() or "vmbr0"
        snippets_datastore = self.form_value("snippets_datastore").strip() or "local"
        image_datastore = self.form_value("image_datastore").strip() or "local"
        vm_datastore = self.form_value("vm_datastore").strip() or "local-lvm"
        cloud_init_datastore = self.form_value("cloud_init_datastore").strip() or "local-lvm"

        assistant.info("SSH")
        assistant.ensure_ssh_key(private_key)
        assistant.install_root_key(host, private_key)

        assistant.info("Preparation du node")
        node_name = assistant.prepare_proxmox_node(host, private_key, snippets_datastore)
        print(f"Node detecte: {node_name}")

        assistant.info("API Proxmox")
        api_token_id, token_secret = assistant.ensure_api_user(
            host,
            private_key,
            api_user,
            token_id,
            self.option_value("recreate_token", self.recreate_token_var),
        )

        assistant.info("Mise a jour terraform.tfvars")
        assistant.set_tfvar(stack, "proxmox_endpoint", f"https://{host}:8006/")
        assistant.set_tfvar(stack, "proxmox_ssh_username", "root")
        assistant.set_tfvar(stack, "proxmox_ssh_agent", False)
        assistant.set_tfvar(stack, "proxmox_ssh_private_key_path", private_key)
        assistant.set_tfvar(stack, "ssh_public_key_path", f"{private_key}.pub")
        assistant.set_tfvar(stack, "proxmox_node_name", node_name)
        assistant.set_tfvar(stack, "network_bridge", bridge)
        assistant.set_tfvar(stack, "snippets_datastore_id", snippets_datastore)
        assistant.set_tfvar(stack, "image_datastore_id", image_datastore)
        assistant.set_tfvar(stack, "vm_datastore_id", vm_datastore)
        assistant.set_tfvar(stack, "cloud_init_datastore_id", cloud_init_datastore)
        assistant.set_tfvar(stack, "proxmox_api_token_id", api_token_id)
        if token_secret:
            assistant.set_tfvar(stack, "proxmox_api_token", token_secret)
        assistant.set_tfvar(stack, "qemu_guest_agent_enabled", True)
        print("terraform.tfvars mis a jour.")

    def action_find_ips(self) -> None:
        ips = self.proxmox_ips_from_form()
        self.print_ips(ips)

    def proxmox_ips_from_form(self) -> dict[str, str]:
        stack = assistant.STACKS["proxmox"]
        host = self.form_value("host").strip() or assistant.endpoint_host(stack)
        private_key = self.form_value("private_key").strip() or assistant.configured_private_key(stack)
        ids = assistant.vm_ids(stack)

        assistant.info("Tentative via QEMU Guest Agent")
        ips = assistant.ips_from_guest_agent(host, private_key, ids)
        missing = [role for role in ids if role not in ips]

        if missing:
            print("Agent indisponible ou incomplet, fallback scan nmap/MAC.")
            ips.update(assistant.scan_ips_by_mac(host, private_key, ids))

        return ips

    def print_ips(self, ips: dict[str, str]) -> None:
        assistant.info("IP trouvees")
        for role in ("web", "monitoring"):
            ip = ips.get(role, "<non trouvee>")
            print(f"{role:10} {ip}")
            if ip != "<non trouvee>":
                private_key = self.form_value("private_key").strip()
                print(f"  ssh -i {private_key} admincloud@{ip}")

        if ips.get("web"):
            print(f"  web_url: http://{ips['web']}")
        if ips.get("monitoring"):
            print(f"  uptime_kuma_url: http://{ips['monitoring']}:3001")

    def action_generate_inventory(self) -> None:
        self.generate_inventory_from_gui()

    def generate_inventory_from_gui(self) -> None:
        stack_name = self.selected_stack()
        control_os = self.selected_control_os()

        if stack_name == "azure":
            ips = assistant.azure_ips_from_outputs()
            windows_key = assistant.private_key_for_stack(stack_name)
        else:
            ips = self.proxmox_ips_from_form()
            windows_key = self.form_value("private_key").strip() or assistant.private_key_for_stack(stack_name)

        inventory_key = assistant.wsl_private_key_path(windows_key) if control_os == "windows" else windows_key
        assistant.write_ansible_inventory(ips, inventory_key)

    def action_install_ansible(self) -> None:
        self.ensure_ansible_noninteractive()

    def ensure_ansible_noninteractive(self) -> None:
        control_os = self.selected_control_os()
        if control_os == "windows":
            self.ensure_ansible_wsl_noninteractive()
        else:
            self.ensure_ansible_linux_noninteractive()

    def ensure_ansible_wsl_noninteractive(self) -> None:
        if not assistant.has_command("wsl"):
            print("WSL n'est pas detecte, ouverture d'une fenetre admin pour installer Debian WSL2.")
            assistant.run([
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command \"wsl --install -d Debian; Read-Host ''Appuie sur Entree pour fermer''\"'",
            ])
            raise RuntimeError("Relance l'interface apres l'installation de Debian WSL2.")

        if assistant.WSL_DISTRO not in assistant.wsl_distros():
            assistant.run(["wsl", "--install", "-d", assistant.WSL_DISTRO])
            raise RuntimeError("Relance l'interface apres l'installation de Debian WSL2.")

        probe = assistant.run_wsl_bash("command -v ansible-playbook", check=False, capture=True, echo_output=False)
        if probe.returncode != 0:
            assistant.run_wsl_bash("sudo apt-get update")
            assistant.run_wsl_bash("sudo apt-get install -y ansible openssh-client python3")
        else:
            print("Ansible est deja installe dans Debian WSL.")
            assistant.run_wsl_bash("ansible-playbook --version", check=False)

        assistant.run_wsl_bash("ansible-galaxy collection install community.docker", check=False)

    def ensure_ansible_linux_noninteractive(self) -> None:
        if assistant.has_command("ansible-playbook"):
            print("Ansible est deja installe.")
            assistant.run(["ansible-playbook", "--version"], check=False)
        else:
            if assistant.has_command("apt-get"):
                assistant.run(["sudo", "apt-get", "update"])
                assistant.run(["sudo", "apt-get", "install", "-y", "ansible"])
            elif assistant.has_command("dnf"):
                assistant.run(["sudo", "dnf", "install", "-y", "ansible"])
            elif assistant.has_command("yum"):
                assistant.run(["sudo", "yum", "install", "-y", "ansible"])
            elif assistant.has_command("pacman"):
                assistant.run(["sudo", "pacman", "-Sy", "--noconfirm", "ansible"])
            else:
                raise RuntimeError("Gestionnaire de paquets non reconnu. Installe Ansible manuellement.")

        if assistant.has_command("ansible-galaxy"):
            assistant.run(["ansible-galaxy", "collection", "install", "community.docker"], check=False)

    def action_run_ansible(self) -> None:
        self.ensure_ansible_noninteractive()
        self.generate_inventory_from_gui()

        control_os = self.selected_control_os()
        stack_name = self.selected_stack()

        if control_os == "windows":
            windows_key = (
                self.form_value("private_key").strip()
                if stack_name == "proxmox"
                else assistant.private_key_for_stack(stack_name)
            )
            assistant.prepare_wsl_ssh_key(windows_key)
            root_wsl = assistant.windows_path_to_wsl(assistant.ROOT)
            assistant.run_wsl_bash(
                f"cd {assistant.shell_quote(root_wsl)} && "
                "ansible-playbook -i ansible/inventaire.ini ansible/playbook.yaml"
            )
        else:
            key = assistant.get_inventory_private_key()
            if key:
                key_path = assistant.expand_user(key)
                if key_path.exists():
                    try:
                        key_path.chmod(0o600)
                    except OSError:
                        pass
            assistant.run(["ansible-playbook", "-i", str(assistant.ANSIBLE_INVENTORY), str(assistant.ANSIBLE_PLAYBOOK)], cwd=assistant.ROOT)

    def action_full_workflow(self) -> None:
        stack = self.selected_stack()

        if stack == "proxmox" and self.option_value("prepare_proxmox", self.prepare_proxmox_var):
            self.prepare_proxmox_from_form()

        assistant.terraform(stack, "init")
        assistant.terraform(stack, "validate")
        assistant.terraform(stack, "plan")

        if self.option_value("apply_auto", self.apply_auto_var):
            assistant.terraform(stack, "apply-auto")

        if stack == "proxmox":
            ips = self.proxmox_ips_from_form()
            self.print_ips(ips)
        else:
            assistant.show_outputs(stack)

        if self.option_value("include_ansible", self.include_ansible_var):
            self.action_run_ansible()


def main() -> None:
    if platform.system().lower().startswith("win"):
        os.environ.setdefault("PYTHONUTF8", "1")

    app = TerraformGui()
    app.mainloop()


if __name__ == "__main__":
    main()
