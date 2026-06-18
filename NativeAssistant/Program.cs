using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace NativeAssistant
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    public class MainForm : Form
    {
        readonly Color Bg = Color.FromArgb(15, 23, 42);
        readonly Color PanelBg = Color.FromArgb(24, 33, 52);
        readonly Color CardBg = Color.FromArgb(31, 42, 66);
        readonly Color Border = Color.FromArgb(64, 82, 118);
        readonly Color TextMain = Color.FromArgb(238, 242, 255);
        readonly Color TextMuted = Color.FromArgb(170, 184, 212);
        readonly Color Blue = Color.FromArgb(79, 140, 255);
        readonly Color Green = Color.FromArgb(47, 191, 113);
        readonly Color Yellow = Color.FromArgb(240, 180, 41);
        readonly Color Red = Color.FromArgb(239, 91, 91);
        readonly Color TerminalBg = Color.FromArgb(7, 17, 31);

        readonly string Root;
        readonly Dictionary<string, TextBox> ProxmoxFields = new Dictionary<string, TextBox>();
        readonly Dictionary<string, TextBox> AzureFields = new Dictionary<string, TextBox>();
        readonly List<Button> ActionButtons = new List<Button>();

        ComboBox stackCombo;
        ComboBox osCombo;
        CheckBox prepareProxmoxCheck;
        CheckBox autoApproveCheck;
        CheckBox includeAnsibleCheck;
        CheckBox recreateTokenCheck;
        TextBox logBox;
        Label statusLabel;
        Panel configHost;
        Control proxmoxConfig;
        Control azureConfig;

        public MainForm()
        {
            Root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            Text = "IaC Assistant";
            StartPosition = FormStartPosition.CenterScreen;
            MinimumSize = new Size(1180, 820);
            Size = new Size(1400, 900);
            BackColor = Bg;
            Font = new Font("Segoe UI", 9.5f);

            BuildUi();
            LoadProxmoxDefaults();
            LoadAzureDefaults();
            UpdateConfigPanel();
        }

        void BuildUi()
        {
            var shell = new TableLayoutPanel();
            shell.Dock = DockStyle.Fill;
            shell.BackColor = Bg;
            shell.Padding = new Padding(14);
            shell.RowCount = 5;
            shell.ColumnCount = 1;
            shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 104));
            shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 54));
            shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 430));
            shell.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 52));
            Controls.Add(shell);

            shell.Controls.Add(BuildHeader(), 0, 0);
            shell.Controls.Add(BuildOptions(), 0, 1);
            shell.Controls.Add(BuildBody(), 0, 2);
            shell.Controls.Add(BuildLogs(), 0, 3);
            shell.Controls.Add(BuildFooter(), 0, 4);
        }

        Panel BuildHeader()
        {
            var header = PanelBox(PanelBg);
            header.Padding = new Padding(18);

            var title = new Label();
            title.Text = "Assistant IaC";
            title.ForeColor = TextMain;
            title.Font = new Font("Segoe UI Semibold", 22f);
            title.AutoSize = true;
            title.Location = new Point(18, 18);
            header.Controls.Add(title);

            var subtitle = new Label();
            subtitle.Text = "Terraform, Proxmox et Ansible dans une interface Windows native.";
            subtitle.ForeColor = TextMuted;
            subtitle.Font = new Font("Segoe UI", 10f);
            subtitle.AutoSize = true;
            subtitle.Location = new Point(21, 62);
            header.Controls.Add(subtitle);

            var right = new Panel();
            right.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            right.Size = new Size(420, 70);
            right.Location = new Point(Width - 480, 23);
            right.BackColor = PanelBg;
            header.Controls.Add(right);
            header.Resize += delegate { right.Location = new Point(header.Width - right.Width - 18, 23); };

            var stackLabel = SmallLabel("Stack");
            stackLabel.Location = new Point(0, 6);
            right.Controls.Add(stackLabel);

            stackCombo = new ComboBox();
            stackCombo.DropDownStyle = ComboBoxStyle.DropDownList;
            stackCombo.Items.AddRange(new object[] { "proxmox", "azure" });
            stackCombo.SelectedIndex = 0;
            stackCombo.Size = new Size(132, 28);
            stackCombo.Location = new Point(0, 30);
            stackCombo.SelectedIndexChanged += delegate { UpdateConfigPanel(); };
            right.Controls.Add(stackCombo);

            var osLabel = SmallLabel("Poste local");
            osLabel.Location = new Point(164, 6);
            right.Controls.Add(osLabel);

            osCombo = new ComboBox();
            osCombo.DropDownStyle = ComboBoxStyle.DropDownList;
            osCombo.Items.AddRange(new object[] { "windows", "linux" });
            osCombo.SelectedIndex = Environment.OSVersion.Platform == PlatformID.Win32NT ? 0 : 1;
            osCombo.Size = new Size(132, 28);
            osCombo.Location = new Point(164, 30);
            right.Controls.Add(osCombo);

            return header;
        }

        Panel BuildOptions()
        {
            var panel = PanelBox(PanelBg);
            panel.Padding = new Padding(14, 12, 14, 12);

            prepareProxmoxCheck = StyledCheck("Preparer la plateforme dans le parcours complet", true);
            prepareProxmoxCheck.Location = new Point(18, 15);
            panel.Controls.Add(prepareProxmoxCheck);

            autoApproveCheck = StyledCheck("Terraform apply -auto-approve", true);
            autoApproveCheck.Location = new Point(340, 15);
            panel.Controls.Add(autoApproveCheck);

            includeAnsibleCheck = StyledCheck("Inclure Ansible", true);
            includeAnsibleCheck.Location = new Point(590, 15);
            panel.Controls.Add(includeAnsibleCheck);

            return panel;
        }

        Control BuildBody()
        {
            var body = new TableLayoutPanel();
            body.Dock = DockStyle.Fill;
            body.BackColor = Bg;
            body.ColumnCount = 2;
            body.RowCount = 1;
            body.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 69));
            body.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 31));
            body.Controls.Add(BuildActionCards(), 0, 0);
            body.Controls.Add(BuildConfigPanel(), 1, 0);
            return body;
        }

        Control BuildConfigPanel()
        {
            configHost = new Panel();
            configHost.Dock = DockStyle.Fill;
            configHost.BackColor = Bg;

            proxmoxConfig = BuildProxmoxForm();
            azureConfig = BuildAzureForm();
            configHost.Controls.Add(proxmoxConfig);
            configHost.Controls.Add(azureConfig);

            return configHost;
        }

        void UpdateConfigPanel()
        {
            if (proxmoxConfig == null || azureConfig == null)
                return;

            bool azure = StackName() == "azure";
            proxmoxConfig.Visible = !azure;
            azureConfig.Visible = azure;
            if (azure)
                azureConfig.BringToFront();
            else
                proxmoxConfig.BringToFront();
        }

        Control BuildActionCards()
        {
            var grid = new TableLayoutPanel();
            grid.Dock = DockStyle.Fill;
            grid.BackColor = Bg;
            grid.Padding = new Padding(6);
            grid.ColumnCount = 3;
            grid.RowCount = 2;
            for (int i = 0; i < 3; i++)
                grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 33.333f));
            grid.RowStyles.Add(new RowStyle(SizeType.Percent, 50));
            grid.RowStyles.Add(new RowStyle(SizeType.Percent, 50));

            var terraform = ActionCard("Terraform", Blue, new ButtonSpec[] {
                new ButtonSpec("Init", Blue, delegate { RunTask("terraform init", delegate { Terraform("init"); }); }),
                new ButtonSpec("Validate", Blue, delegate { RunTask("terraform validate", delegate { Terraform("validate"); }); }),
                new ButtonSpec("Plan", Blue, delegate { RunTask("terraform plan", delegate { Terraform("plan"); }); }),
                new ButtonSpec("Apply", Yellow, ConfirmApply),
                new ButtonSpec("Destroy", Red, ConfirmDestroy),
                new ButtonSpec("Outputs", Blue, delegate { RunTask("terraform outputs", delegate { Terraform("output"); }); })
            });
            grid.Controls.Add(terraform, 0, 0);
            grid.SetRowSpan(terraform, 2);

            grid.Controls.Add(ActionCard("Plateforme", Green, new ButtonSpec[] {
                new ButtonSpec("Preparer Proxmox", Green, delegate { RunTask("preparation Proxmox", PrepareProxmox); }),
                new ButtonSpec("Preparer Azure", Green, delegate { RunTask("preparation Azure", PrepareAzure); }),
                new ButtonSpec("Retrouver IP des VM", Blue, delegate { RunTask("recherche IP", delegate { PrintIps(FindProxmoxIps()); }); })
            }), 1, 0);

            grid.Controls.Add(ActionCard("Ansible", Yellow, new ButtonSpec[] {
                new ButtonSpec("Generer inventaire", Blue, delegate { RunTask("inventaire Ansible", GenerateInventory); }),
                new ButtonSpec("Installer/verifier", Blue, delegate { RunTask("installation Ansible", EnsureAnsible); }),
                new ButtonSpec("Lancer playbook", Yellow, delegate { RunTask("playbook Ansible", RunAnsible); })
            }), 2, 0);

            var workflow = ActionCard("Workflow", Color.FromArgb(167, 139, 250), new ButtonSpec[] {
                new ButtonSpec("Tout derouler", Color.FromArgb(167, 139, 250), ConfirmFullWorkflow)
            });
            grid.Controls.Add(workflow, 1, 1);
            grid.SetColumnSpan(workflow, 2);

            return grid;
        }

        Panel ActionCard(string title, Color accent, ButtonSpec[] buttons)
        {
            var card = PanelBox(CardBg);
            card.Padding = new Padding(12);
            card.Margin = new Padding(5);

            var accentBar = new Panel();
            accentBar.BackColor = accent;
            accentBar.Height = 4;
            accentBar.Dock = DockStyle.Top;
            card.Controls.Add(accentBar);

            var titleLabel = new Label();
            titleLabel.Text = title;
            titleLabel.ForeColor = TextMain;
            titleLabel.Font = new Font("Segoe UI Semibold", 13f);
            titleLabel.AutoSize = true;
            titleLabel.Location = new Point(14, 18);
            card.Controls.Add(titleLabel);

            int y = 56;
            foreach (var spec in buttons)
            {
                var button = StyledButton(spec.Text, spec.Color);
                button.Location = new Point(14, y);
                button.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;
                button.Width = 210;
                button.Click += spec.Handler;
                card.Controls.Add(button);
                ActionButtons.Add(button);
                y += 34;
            }

            card.Resize += delegate
            {
                foreach (Control control in card.Controls)
                {
                    var b = control as Button;
                    if (b != null)
                        b.Width = Math.Max(120, card.Width - 28);
                }
            };

            return card;
        }

        Control BuildProxmoxForm()
        {
            var panel = PanelBox(PanelBg);
            panel.Dock = DockStyle.Fill;
            panel.Padding = new Padding(14);

            var layout = new TableLayoutPanel();
            layout.Dock = DockStyle.Fill;
            layout.BackColor = PanelBg;
            layout.ColumnCount = 1;
            layout.RowCount = 2;
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            panel.Controls.Add(layout);

            var title = new Label();
            title.Text = "Parametres Proxmox";
            title.ForeColor = TextMain;
            title.Font = new Font("Segoe UI Semibold", 12.5f);
            title.Dock = DockStyle.Fill;
            title.TextAlign = ContentAlignment.MiddleLeft;
            layout.Controls.Add(title, 0, 0);

            var form = new TableLayoutPanel();
            form.Dock = DockStyle.Fill;
            form.BackColor = PanelBg;
            form.ColumnCount = 2;
            form.RowCount = 10;
            form.Padding = new Padding(0, 12, 0, 0);
            form.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 132));
            form.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            for (int i = 0; i < 10; i++)
                form.RowStyles.Add(new RowStyle(SizeType.Absolute, 31));

            string[,] fields = new string[,] {
                {"host", "IP/DNS Proxmox"},
                {"private_key", "Cle SSH privee"},
                {"api_user", "User API"},
                {"token_id", "Token ID"},
                {"bridge", "Bridge reseau"},
                {"snippets_datastore", "Datastore snippets/import"},
                {"image_datastore", "Datastore image Debian"},
                {"vm_datastore", "Datastore disques VM"},
                {"cloud_init_datastore", "Datastore cloud-init"}
            };

            for (int i = 0; i < fields.GetLength(0); i++)
            {
                AddFormRow(form, i, fields[i, 0], fields[i, 1], fields[i, 0] == "private_key");
            }

            var bottom = new Panel();
            bottom.Dock = DockStyle.Fill;
            bottom.BackColor = PanelBg;

            recreateTokenCheck = StyledCheck("Creer/recreer le token API", false);
            recreateTokenCheck.Location = new Point(0, 5);
            bottom.Controls.Add(recreateTokenCheck);

            var reload = StyledButton("Recharger depuis terraform.tfvars", Blue);
            reload.Width = 250;
            reload.Location = new Point(0, 0);
            reload.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            reload.Click += delegate { LoadProxmoxDefaults(); };
            bottom.Controls.Add(reload);
            bottom.Resize += delegate
            {
                reload.Location = new Point(Math.Max(0, bottom.Width - reload.Width), 0);
            };

            form.Controls.Add(bottom, 0, 9);
            form.SetColumnSpan(bottom, 2);
            layout.Controls.Add(form, 0, 1);

            return panel;
        }

        Control BuildAzureForm()
        {
            var panel = PanelBox(PanelBg);
            panel.Dock = DockStyle.Fill;
            panel.Padding = new Padding(14);

            var layout = new TableLayoutPanel();
            layout.Dock = DockStyle.Fill;
            layout.BackColor = PanelBg;
            layout.ColumnCount = 1;
            layout.RowCount = 3;
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 54));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            panel.Controls.Add(layout);

            var title = new Label();
            title.Text = "Parametres Azure";
            title.ForeColor = TextMain;
            title.Font = new Font("Segoe UI Semibold", 12.5f);
            title.Dock = DockStyle.Fill;
            title.TextAlign = ContentAlignment.MiddleLeft;
            layout.Controls.Add(title, 0, 0);

            var hint = new Label();
            hint.Text = "Renseigne l'abonnement, ton IP admin et la cle SSH avant plan/apply.";
            hint.ForeColor = TextMuted;
            hint.Font = new Font("Segoe UI", 9f);
            hint.Dock = DockStyle.Fill;
            hint.TextAlign = ContentAlignment.TopLeft;
            layout.Controls.Add(hint, 0, 1);

            var form = new TableLayoutPanel();
            form.Dock = DockStyle.Fill;
            form.BackColor = PanelBg;
            form.ColumnCount = 2;
            form.RowCount = 9;
            form.Padding = new Padding(0, 4, 0, 0);
            form.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 132));
            form.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            for (int i = 0; i < 9; i++)
                form.RowStyles.Add(new RowStyle(SizeType.Absolute, 31));

            string[,] fields = new string[,] {
                {"subscription_id", "Subscription ID"},
                {"project_name", "Projet"},
                {"location", "Region"},
                {"admin_username", "Utilisateur VM"},
                {"ssh_public_key_path", "Cle SSH publique"},
                {"admin_ip_cidr", "IP admin CIDR"},
                {"web_vm_size", "Taille VM web"},
                {"monitoring_vm_size", "Taille monitoring"}
            };

            for (int i = 0; i < fields.GetLength(0); i++)
            {
                AddAzureRow(form, i, fields[i, 0], fields[i, 1], fields[i, 0] == "ssh_public_key_path");
            }

            var bottom = new Panel();
            bottom.Dock = DockStyle.Fill;
            bottom.BackColor = PanelBg;

            var login = StyledButton("Preparer Azure", Green);
            login.Width = 130;
            login.Location = new Point(0, 0);
            login.Click += delegate { RunTask("preparation Azure", PrepareAzure); };
            bottom.Controls.Add(login);

            var save = StyledButton("Enregistrer Azure", Green);
            save.Width = 170;
            save.Location = new Point(140, 0);
            save.Click += delegate { SaveAzureTfvars(); };
            bottom.Controls.Add(save);

            form.Controls.Add(bottom, 0, 8);
            form.SetColumnSpan(bottom, 2);
            layout.Controls.Add(form, 0, 2);

            return panel;
        }

        void AddFormRow(TableLayoutPanel form, int row, string key, string label, bool browse)
        {
            var lbl = SmallLabel(label);
            lbl.Dock = DockStyle.Fill;
            lbl.TextAlign = ContentAlignment.MiddleLeft;
            form.Controls.Add(lbl, 0, row);

            if (browse)
            {
                var picker = new TableLayoutPanel();
                picker.Dock = DockStyle.Fill;
                picker.BackColor = PanelBg;
                picker.ColumnCount = 2;
                picker.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
                picker.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 36));

                var box = StyledTextBox();
                ProxmoxFields[key] = box;
                picker.Controls.Add(box, 0, 0);

                var button = StyledButton("...", Border);
                button.Dock = DockStyle.Fill;
                button.Click += delegate
                {
                    using (var dialog = new OpenFileDialog())
                    {
                        dialog.Title = "Choisir la cle SSH privee";
                        if (dialog.ShowDialog(this) == DialogResult.OK)
                            box.Text = dialog.FileName;
                    }
                };
                picker.Controls.Add(button, 1, 0);
                form.Controls.Add(picker, 1, row);
                return;
            }

            var input = StyledTextBox();
            ProxmoxFields[key] = input;
            form.Controls.Add(input, 1, row);
        }

        void AddAzureRow(TableLayoutPanel form, int row, string key, string label, bool browse)
        {
            var lbl = SmallLabel(label);
            lbl.Dock = DockStyle.Fill;
            lbl.TextAlign = ContentAlignment.MiddleLeft;
            form.Controls.Add(lbl, 0, row);

            if (browse)
            {
                var picker = new TableLayoutPanel();
                picker.Dock = DockStyle.Fill;
                picker.BackColor = PanelBg;
                picker.ColumnCount = 2;
                picker.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
                picker.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 36));

                var box = StyledTextBox();
                AzureFields[key] = box;
                picker.Controls.Add(box, 0, 0);

                var button = StyledButton("...", Border);
                button.Dock = DockStyle.Fill;
                button.Click += delegate
                {
                    using (var dialog = new OpenFileDialog())
                    {
                        dialog.Title = "Choisir la cle SSH publique";
                        if (dialog.ShowDialog(this) == DialogResult.OK)
                            box.Text = dialog.FileName;
                    }
                };
                picker.Controls.Add(button, 1, 0);
                form.Controls.Add(picker, 1, row);
                return;
            }

            var input = StyledTextBox();
            AzureFields[key] = input;
            form.Controls.Add(input, 1, row);
        }

        TextBox StyledTextBox()
        {
            var box = new TextBox();
            box.BackColor = Color.FromArgb(238, 243, 255);
            box.ForeColor = Color.FromArgb(23, 32, 51);
            box.BorderStyle = BorderStyle.FixedSingle;
            box.Dock = DockStyle.Fill;
            box.Margin = new Padding(0, 2, 0, 3);
            return box;
        }

        Control BuildLogs()
        {
            var frame = PanelBox(CardBg);
            frame.Padding = new Padding(12);

            var label = new Label();
            label.Text = "Logs";
            label.ForeColor = TextMain;
            label.Font = new Font("Segoe UI Semibold", 12f);
            label.AutoSize = true;
            label.Dock = DockStyle.Top;
            frame.Controls.Add(label);

            logBox = new TextBox();
            logBox.Multiline = true;
            logBox.ScrollBars = ScrollBars.Vertical;
            logBox.ReadOnly = true;
            logBox.BackColor = TerminalBg;
            logBox.ForeColor = Color.FromArgb(217, 231, 255);
            logBox.BorderStyle = BorderStyle.None;
            logBox.Font = new Font("Consolas", 10f);
            logBox.Dock = DockStyle.Fill;
            logBox.Margin = new Padding(0, 12, 0, 0);
            frame.Controls.Add(logBox);
            logBox.BringToFront();

            return frame;
        }

        Control BuildFooter()
        {
            var footer = new Panel();
            footer.BackColor = Bg;
            footer.Dock = DockStyle.Fill;

            statusLabel = new Label();
            statusLabel.Text = "Pret";
            statusLabel.ForeColor = TextMuted;
            statusLabel.Font = new Font("Segoe UI Semibold", 10f);
            statusLabel.AutoSize = true;
            statusLabel.Location = new Point(4, 15);
            footer.Controls.Add(statusLabel);

            var clear = StyledButton("Effacer les logs", Border);
            clear.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            clear.Width = 150;
            clear.Location = new Point(footer.Width - 260, 8);
            clear.Click += delegate { logBox.Clear(); };
            footer.Controls.Add(clear);

            var quit = StyledButton("Quitter", Red);
            quit.Anchor = AnchorStyles.Top | AnchorStyles.Right;
            quit.Width = 100;
            quit.Location = new Point(footer.Width - 104, 8);
            quit.Click += delegate { Close(); };
            footer.Controls.Add(quit);

            footer.Resize += delegate
            {
                clear.Location = new Point(footer.Width - 260, 8);
                quit.Location = new Point(footer.Width - 104, 8);
            };

            return footer;
        }

        void AddField(Control parent, string key, string label, int x, int y, bool browse)
        {
            var lbl = SmallLabel(label);
            lbl.Location = new Point(x, y);
            parent.Controls.Add(lbl);

            var box = new TextBox();
            box.BackColor = Color.FromArgb(238, 243, 255);
            box.ForeColor = Color.FromArgb(23, 32, 51);
            box.BorderStyle = BorderStyle.FixedSingle;
            box.Location = new Point(x + 170, y - 3);
            box.Size = new Size(browse ? 300 : 330, 25);
            ProxmoxFields[key] = box;
            parent.Controls.Add(box);

            if (browse)
            {
                var button = StyledButton("...", Border);
                button.Size = new Size(32, 25);
                button.Location = new Point(x + 475, y - 4);
                button.Click += delegate
                {
                    using (var dialog = new OpenFileDialog())
                    {
                        dialog.Title = "Choisir la cle SSH privee";
                        if (dialog.ShowDialog(this) == DialogResult.OK)
                            box.Text = dialog.FileName;
                    }
                };
                parent.Controls.Add(button);
            }
        }

        Label SmallLabel(string text)
        {
            var label = new Label();
            label.Text = text;
            label.ForeColor = TextMuted;
            label.Font = new Font("Segoe UI", 9.5f);
            label.AutoSize = true;
            return label;
        }

        CheckBox StyledCheck(string text, bool value)
        {
            var check = new CheckBox();
            check.Text = text;
            check.Checked = value;
            check.AutoSize = true;
            check.ForeColor = TextMain;
            check.BackColor = PanelBg;
            check.FlatStyle = FlatStyle.Flat;
            return check;
        }

        Button StyledButton(string text, Color color)
        {
            var button = new Button();
            button.Text = text;
            button.Height = 30;
            button.FlatStyle = FlatStyle.Flat;
            button.FlatAppearance.BorderSize = 0;
            button.BackColor = color;
            button.ForeColor = color == Yellow ? Color.FromArgb(47, 33, 0) : Color.White;
            button.Font = new Font("Segoe UI Semibold", 9.5f);
            button.Cursor = Cursors.Hand;
            return button;
        }

        Panel PanelBox(Color color)
        {
            var panel = new Panel();
            panel.BackColor = color;
            panel.Dock = DockStyle.Fill;
            panel.Margin = new Padding(0, 0, 0, 10);
            return panel;
        }

        void LoadProxmoxDefaults()
        {
            string stack = Path.Combine(Root, "Proxmox");
            SetField("host", EndpointHost(stack));
            SetField("private_key", GetTfvar(stack, "proxmox_ssh_private_key_path", "~/.ssh/tp_azure_ed25519"));
            SetField("api_user", "terraform@pve");
            SetField("token_id", "provider");
            SetField("bridge", GetTfvar(stack, "network_bridge", "vmbr0"));
            SetField("snippets_datastore", GetTfvar(stack, "snippets_datastore_id", "local"));
            SetField("image_datastore", GetTfvar(stack, "image_datastore_id", "local"));
            SetField("vm_datastore", GetTfvar(stack, "vm_datastore_id", "local-lvm"));
            SetField("cloud_init_datastore", GetTfvar(stack, "cloud_init_datastore_id", "local-lvm"));
        }

        void LoadAzureDefaults()
        {
            string stack = Path.Combine(Root, "azure");
            SetAzureField("subscription_id", GetTfvar(stack, "subscription_id", ""));
            SetAzureField("project_name", GetTfvar(stack, "project_name", "tp-cloud"));
            SetAzureField("location", GetTfvar(stack, "location", "spaincentral"));
            SetAzureField("admin_username", GetTfvar(stack, "admin_username", "admincloud"));
            SetAzureField("ssh_public_key_path", GetTfvar(stack, "ssh_public_key_path", "~/.ssh/tp_azure_ed25519.pub"));
            SetAzureField("admin_ip_cidr", GetTfvar(stack, "admin_ip_cidr", ""));
            SetAzureField("web_vm_size", GetTfvar(stack, "web_vm_size", "Standard_B2ats_v2"));
            SetAzureField("monitoring_vm_size", GetTfvar(stack, "monitoring_vm_size", "Standard_B2ats_v2"));
        }

        void SaveAzureTfvars()
        {
            string stack = Path.Combine(Root, "azure");
            SetTfvar(stack, "subscription_id", AzureField("subscription_id"));
            SetTfvar(stack, "project_name", AzureField("project_name"));
            SetTfvar(stack, "location", AzureField("location"));
            SetTfvar(stack, "admin_username", AzureField("admin_username"));
            SetTfvar(stack, "ssh_public_key_path", AzureField("ssh_public_key_path"));
            SetTfvar(stack, "admin_ip_cidr", AzureField("admin_ip_cidr"));
            SetTfvar(stack, "web_vm_size", AzureField("web_vm_size"));
            SetTfvar(stack, "monitoring_vm_size", AzureField("monitoring_vm_size"));
            AppendLog("azure/terraform.tfvars mis a jour." + Environment.NewLine);
        }

        void SetField(string name, string value)
        {
            if (ProxmoxFields.ContainsKey(name))
                ProxmoxFields[name].Text = value;
        }

        void SetAzureField(string name, string value)
        {
            if (AzureFields.ContainsKey(name))
                AzureFields[name].Text = value;
        }

        void SetAzureFieldSafe(string name, string value)
        {
            if (!AzureFields.ContainsKey(name))
                return;

            var box = AzureFields[name];
            if (box.InvokeRequired)
            {
                box.Invoke(new Action<string, string>(SetAzureFieldSafe), name, value);
                return;
            }
            box.Text = value;
        }

        string Field(string name)
        {
            return TextBoxValue(ProxmoxFields, name);
        }

        string AzureField(string name)
        {
            return TextBoxValue(AzureFields, name);
        }

        string TextBoxValue(Dictionary<string, TextBox> fields, string name)
        {
            if (!fields.ContainsKey(name))
                return "";

            var box = fields[name];
            if (box.InvokeRequired)
                return (string)box.Invoke(new Func<string>(delegate { return box.Text.Trim(); }));
            return box.Text.Trim();
        }

        void RunTask(string title, Action action)
        {
            SetButtons(false);
            statusLabel.Text = "En cours: " + title;
            AppendLog(Environment.NewLine + "== " + title + " ==" + Environment.NewLine);
            Task.Factory.StartNew(delegate
            {
                try
                {
                    action();
                    AppendLog(Environment.NewLine + "== Termine: " + title + " ==" + Environment.NewLine);
                    SetStatus("Pret");
                }
                catch (ActionRequiredException ex)
                {
                    AppendLog(Environment.NewLine + "ACTION REQUISE:" + Environment.NewLine + ex.Message + Environment.NewLine);
                    SetStatus("Action requise");
                }
                catch (Exception ex)
                {
                    AppendLog(Environment.NewLine + "ERREUR:" + Environment.NewLine + ex + Environment.NewLine);
                    SetStatus("Erreur");
                }
                finally
                {
                    BeginInvoke(new Action(delegate { SetButtons(true); }));
                }
            });
        }

        void SetButtons(bool enabled)
        {
            foreach (var button in ActionButtons)
                button.Enabled = enabled;
        }

        void SetStatus(string text)
        {
            if (InvokeRequired)
                BeginInvoke(new Action<string>(SetStatus), text);
            else
                statusLabel.Text = text;
        }

        void AppendLog(string text)
        {
            if (InvokeRequired)
            {
                BeginInvoke(new Action<string>(AppendLog), text);
                return;
            }
            logBox.AppendText(text);
            logBox.SelectionStart = logBox.TextLength;
            logBox.ScrollToCaret();
        }

        void ConfirmApply(object sender, EventArgs e)
        {
            if (MessageBox.Show(this, "Lancer Terraform apply sur la stack selectionnee ?", "Terraform apply", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                RunTask("terraform apply", delegate { Terraform("apply"); });
        }

        void ConfirmDestroy(object sender, EventArgs e)
        {
            if (MessageBox.Show(this, "Detruire les ressources Terraform de cette stack ?", "Terraform destroy", MessageBoxButtons.YesNo, MessageBoxIcon.Warning) == DialogResult.Yes)
                RunTask("terraform destroy", delegate { Terraform("destroy"); });
        }

        void ConfirmFullWorkflow(object sender, EventArgs e)
        {
            string message = autoApproveCheck.Checked
                ? "Le parcours complet va lancer terraform apply -auto-approve. Continuer ?"
                : "Le parcours complet va derouler init, validate, plan, outputs et Ansible. Continuer ?";
            if (MessageBox.Show(this, message, "Parcours complet", MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.Yes)
                RunTask("parcours complet", FullWorkflow);
        }

        string StackName()
        {
            return stackCombo.SelectedItem == null ? "proxmox" : stackCombo.SelectedItem.ToString();
        }

        string ControlOs()
        {
            return osCombo.SelectedItem == null ? "windows" : osCombo.SelectedItem.ToString();
        }

        string StackPath(string stack)
        {
            return Path.Combine(Root, stack == "azure" ? "azure" : "Proxmox");
        }

        void Terraform(string command)
        {
            string stack = StackName();
            string cwd = StackPath(stack);
            if (stack == "azure")
                SaveAzureTfvars();
            if (command == "apply")
            {
                RunProcess("terraform", autoApproveCheck.Checked ? "apply -auto-approve" : "apply", cwd);
                return;
            }
            if (command == "output")
            {
                RunProcess("terraform", "output", cwd);
                return;
            }
            RunProcess("terraform", command, cwd);
        }

        void PrepareAzure()
        {
            infoAzure("Preparation Azure");
            EnsureAzureSshKey();
            FillAzureAdminIpIfMissing();
            SaveAzureTfvars();

            if (ControlOs() == "windows")
            {
                string az = EnsureAzureCliWindows();
                RunAzureWindows(az, "login --use-device-code");
                SaveAzureSubscriptionFromOutput(RunAzureWindows(az, "account show --query id -o tsv", false));
            }
            else if (IsWindowsHost())
            {
                EnsureAzureCliWsl();
                RunProcess("wsl", "-d Debian -- bash -lc " + QuoteArg("az login --use-device-code"), Root);
                string subscription = RunProcess("wsl", "-d Debian -- bash -lc " + QuoteArg("az account show --query id -o tsv"), Root, false);
                SaveAzureSubscriptionFromOutput(subscription);
            }
            else
            {
                EnsureAzureCliLinux();
                RunProcess("az", "login --use-device-code", Root);
                SaveAzureSubscriptionFromOutput(RunProcess("az", "account show --query id -o tsv", Root, false));
            }

            SaveAzureTfvars();
            AppendLog("Azure est pret pour Terraform." + Environment.NewLine);
        }

        void infoAzure(string title)
        {
            AppendLog(Environment.NewLine + "-- " + title + " --" + Environment.NewLine);
        }

        void EnsureAzureSshKey()
        {
            string publicKey = OrDefault(AzureField("ssh_public_key_path"), "~/.ssh/tp_azure_ed25519.pub");
            string expandedPublic = ExpandUser(publicKey);
            string privateKey = expandedPublic.EndsWith(".pub", StringComparison.OrdinalIgnoreCase)
                ? expandedPublic.Substring(0, expandedPublic.Length - 4)
                : expandedPublic;
            string realPublic = expandedPublic.EndsWith(".pub", StringComparison.OrdinalIgnoreCase)
                ? expandedPublic
                : expandedPublic + ".pub";

            if (File.Exists(privateKey) && File.Exists(realPublic))
            {
                AppendLog("Cle SSH Azure deja presente: " + realPublic + Environment.NewLine);
                return;
            }

            string keyDir = Path.GetDirectoryName(privateKey);
            if (!string.IsNullOrEmpty(keyDir))
                Directory.CreateDirectory(keyDir);
            RunProcess("ssh-keygen", "-t ed25519 -f " + QuoteArg(privateKey) + " -C tp-azure -N \"\"", Root);
            if (!publicKey.EndsWith(".pub", StringComparison.OrdinalIgnoreCase))
                SetAzureFieldSafe("ssh_public_key_path", realPublic);
        }

        void FillAzureAdminIpIfMissing()
        {
            if (!string.IsNullOrWhiteSpace(AzureField("admin_ip_cidr")))
                return;

            try
            {
                ServicePointManager.SecurityProtocol = ServicePointManager.SecurityProtocol | SecurityProtocolType.Tls12;
                using (var client = new WebClient())
                {
                    string ip = client.DownloadString("https://api.ipify.org").Trim();
                    if (Regex.IsMatch(ip, "^\\d+\\.\\d+\\.\\d+\\.\\d+$"))
                    {
                        SetAzureFieldSafe("admin_ip_cidr", ip + "/32");
                        AppendLog("IP publique detectee pour SSH Azure: " + ip + "/32" + Environment.NewLine);
                    }
                }
            }
            catch (Exception ex)
            {
                AppendLog("Impossible de detecter l'IP publique automatiquement: " + ex.Message + Environment.NewLine);
            }
        }

        string EnsureAzureCliWindows()
        {
            string az = AzureCliCommand();
            if (az.Length > 0)
            {
                RunAzureWindows(az, "version", false);
                return az;
            }

            if (!CommandExists("winget"))
                throw new Exception("Azure CLI est absent et winget est introuvable. Installe winget ou Azure CLI manuellement.");

            AppendLog("Azure CLI absent: installation via winget." + Environment.NewLine);
            RunProcess("winget", "install -e --id Microsoft.AzureCLI --accept-package-agreements --accept-source-agreements", Root);

            az = AzureCliCommand();
            if (az.Length == 0)
                throw new Exception("Azure CLI semble installe, mais n'est pas encore visible. Relance l'application.");
            return az;
        }

        string AzureCliCommand()
        {
            if (IsWindowsHost())
            {
                string output = RunProcess("where", "az", Root, false);
                var candidates = new List<string>();
                foreach (string rawLine in output.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
                {
                    string line = rawLine.Trim();
                    if (line.Length > 0)
                        candidates.Add(line);
                }

                foreach (string path in candidates)
                {
                    if (path.EndsWith(".cmd", StringComparison.OrdinalIgnoreCase) ||
                        path.EndsWith(".bat", StringComparison.OrdinalIgnoreCase) ||
                        path.EndsWith(".exe", StringComparison.OrdinalIgnoreCase))
                        return path;
                }

                foreach (string path in candidates)
                {
                    string cmd = path + ".cmd";
                    if (File.Exists(cmd))
                        return cmd;
                }
            }
            else if (CommandExists("az"))
            {
                return "az";
            }

            string[] known = new string[] {
                @"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
                @"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
            };
            foreach (string path in known)
            {
                if (File.Exists(path))
                    return path;
            }
            return "";
        }

        string RunAzureWindows(string az, string args)
        {
            return RunAzureWindows(az, args, true);
        }

        string RunAzureWindows(string az, string args, bool check)
        {
            if (az.EndsWith(".cmd", StringComparison.OrdinalIgnoreCase) || az.EndsWith(".bat", StringComparison.OrdinalIgnoreCase))
                return RunProcess("cmd.exe", "/c " + QuoteArg(az) + " " + args, Root, check);
            if (Path.GetExtension(az).Length == 0)
                return RunProcess("cmd.exe", "/c " + QuoteArg(az) + " " + args, Root, check);
            return RunProcess(az, args, Root, check);
        }

        void EnsureAzureCliWsl()
        {
            EnsureDebianWsl();
            string command =
                "set -e; " +
                "if command -v az >/dev/null 2>&1; then az version; " +
                "else sudo apt-get update && sudo apt-get install -y curl ca-certificates gnupg && curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash; fi";
            RunProcess("wsl", "-d Debian -- bash -lc " + QuoteArg(command), Root);
        }

        void EnsureAzureCliLinux()
        {
            if (CommandExists("az"))
            {
                RunProcess("az", "version", Root, false);
                return;
            }

            if (!CommandExists("bash"))
                throw new Exception("Azure CLI absent et bash introuvable.");

            if (CommandExists("apt-get"))
            {
                string command = "sudo apt-get update && sudo apt-get install -y curl ca-certificates gnupg && curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash";
                RunProcess("bash", "-lc " + QuoteArg(command), Root);
                return;
            }

            throw new Exception("Azure CLI absent. Installe-le manuellement pour cette distribution Linux.");
        }

        void SaveAzureSubscriptionFromOutput(string output)
        {
            string subscription = output.Trim();
            Match match = Regex.Match(subscription, "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
            if (!match.Success)
                return;

            if (string.IsNullOrWhiteSpace(AzureField("subscription_id")))
            {
                SetAzureFieldSafe("subscription_id", match.Value);
                SetTfvar(StackPath("azure"), "subscription_id", match.Value);
                AppendLog("Subscription Azure detectee: " + match.Value + Environment.NewLine);
            }
        }

        void PrepareProxmox()
        {
            string stack = StackPath("proxmox");
            string host = Field("host");
            string privateKey = Field("private_key");
            string apiUser = OrDefault(Field("api_user"), "terraform@pve");
            string tokenId = OrDefault(Field("token_id"), "provider");
            string bridge = OrDefault(Field("bridge"), "vmbr0");
            string snippets = OrDefault(Field("snippets_datastore"), "local");
            string image = OrDefault(Field("image_datastore"), "local");
            string vmStore = OrDefault(Field("vm_datastore"), "local-lvm");
            string cloudInit = OrDefault(Field("cloud_init_datastore"), "local-lvm");

            EnsureSshKey(privateKey);
            InstallRootKey(host, privateKey);
            string node = PrepareNode(host, privateKey, snippets);
            AppendLog("Node detecte: " + node + Environment.NewLine);

            string fullTokenId;
            string secret;
            EnsureApiUser(host, privateKey, apiUser, tokenId, recreateTokenCheck.Checked, out fullTokenId, out secret);

            SetTfvar(stack, "proxmox_endpoint", "https://" + host + ":8006/");
            SetTfvar(stack, "proxmox_ssh_username", "root");
            SetTfvar(stack, "proxmox_ssh_agent", "false", true);
            SetTfvar(stack, "proxmox_ssh_private_key_path", privateKey);
            SetTfvar(stack, "ssh_public_key_path", privateKey + ".pub");
            SetTfvar(stack, "proxmox_node_name", node);
            SetTfvar(stack, "network_bridge", bridge);
            SetTfvar(stack, "snippets_datastore_id", snippets);
            SetTfvar(stack, "image_datastore_id", image);
            SetTfvar(stack, "vm_datastore_id", vmStore);
            SetTfvar(stack, "cloud_init_datastore_id", cloudInit);
            SetTfvar(stack, "proxmox_api_token_id", fullTokenId);
            if (!string.IsNullOrWhiteSpace(secret))
                SetTfvar(stack, "proxmox_api_token", secret);
            SetTfvar(stack, "qemu_guest_agent_enabled", "true", true);
            AppendLog("terraform.tfvars mis a jour." + Environment.NewLine);
        }

        void EnsureSshKey(string privateKey)
        {
            string expanded = ExpandUser(privateKey);
            string pub = expanded + ".pub";
            if (File.Exists(expanded) && File.Exists(pub))
            {
                AppendLog("Cle SSH deja presente: " + expanded + Environment.NewLine);
                return;
            }
            Directory.CreateDirectory(Path.GetDirectoryName(expanded));
            RunProcess("ssh-keygen", "-t ed25519 -f " + QuoteArg(expanded) + " -C tp-proxmox -N \"\"", Root);
        }

        void InstallRootKey(string host, string privateKey)
        {
            string pubPath = ExpandUser(privateKey) + ".pub";
            string pub = File.ReadAllText(pubPath).Trim();
            string remote =
                "mkdir -p /root/.ssh && chmod 700 /root/.ssh && " +
                "touch /root/.ssh/authorized_keys && " +
                "(grep -qxF -- " + ShellQuote(pub) + " /root/.ssh/authorized_keys || echo " + ShellQuote(pub) + " >> /root/.ssh/authorized_keys) && " +
                "chmod 600 /root/.ssh/authorized_keys && systemctl enable --now ssh";
            RunSsh("root@" + host, remote, privateKey, false);
            RunSsh("root@" + host, "echo ok", privateKey, true);
        }

        string PrepareNode(string host, string privateKey, string datastore)
        {
            string remote = string.Join("; ", new string[] {
                "set -e",
                "systemctl enable --now ssh",
                "pvesm set " + ShellQuote(datastore) + " --content iso,vztmpl,backup,import,snippets",
                "snippet_dir=$(pvesm path " + ShellQuote(datastore + ":snippets") + " 2>/dev/null || true)",
                "if [ -z \"$snippet_dir\" ]; then snippet_dir=/var/lib/vz/snippets; fi",
                "mkdir -p \"$snippet_dir\"",
                "chmod 755 \"$snippet_dir\"",
                "if ! command -v nmap >/dev/null 2>&1; then apt-get update -y && apt-get install -y nmap; fi",
                "hostname"
            });
            string output = RunSsh("root@" + host, remote, privateKey, true);
            string[] lines = output.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
            return lines.Length == 0 ? "pve" : lines[lines.Length - 1].Trim();
        }

        void EnsureApiUser(string host, string privateKey, string apiUser, string tokenId, bool recreate, out string fullTokenId, out string secret)
        {
            fullTokenId = apiUser + "!" + tokenId;
            secret = "";
            string remote = string.Join("; ", new string[] {
                "pveum user add " + ShellQuote(apiUser) + " --comment 'Terraform user' 2>/dev/null || true",
                "pveum acl modify / --users " + ShellQuote(apiUser) + " --roles Administrator",
                "pveum user token list " + ShellQuote(apiUser) + " || true"
            });
            RunSsh("root@" + host, remote, privateKey, true);
            if (!recreate)
                return;

            string tokenRemote = string.Join("; ", new string[] {
                "pveum user token remove " + ShellQuote(apiUser) + " " + ShellQuote(tokenId) + " 2>/dev/null || true",
                "pveum user token add " + ShellQuote(apiUser) + " " + ShellQuote(tokenId) + " --privsep 0 --output-format json"
            });
            string output = RunSsh("root@" + host, tokenRemote, privateKey, true);
            Match value = Regex.Match(output, "\"value\"\\s*:\\s*\"([^\"]+)\"");
            Match full = Regex.Match(output, "\"full-tokenid\"\\s*:\\s*\"([^\"]+)\"");
            if (full.Success)
                fullTokenId = full.Groups[1].Value;
            if (value.Success)
                secret = value.Groups[1].Value;
            else
            {
                Match uuid = Regex.Match(output, "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}");
                if (uuid.Success)
                    secret = uuid.Value;
            }
        }

        Dictionary<string, string> FindProxmoxIps()
        {
            string stack = StackPath("proxmox");
            string host = OrDefault(Field("host"), EndpointHost(stack));
            string privateKey = OrDefault(Field("private_key"), GetTfvar(stack, "proxmox_ssh_private_key_path", "~/.ssh/tp_azure_ed25519"));
            string node = GetTfvar(stack, "proxmox_node_name", "pve");
            var vmids = new Dictionary<string, string>();
            vmids["web"] = GetTfvar(stack, "web_vm_id", "201");
            vmids["monitoring"] = GetTfvar(stack, "monitoring_vm_id", "202");
            var ips = new Dictionary<string, string>();

            foreach (var item in vmids)
            {
                string output = RunSsh("root@" + host, "pvesh get /nodes/" + node + "/qemu/" + item.Value + "/agent/network-get-interfaces --output-format json", privateKey, true, false);
                Match ip = Regex.Match(output, "\"ip-address\"\\s*:\\s*\"((?!127\\.)\\d+\\.\\d+\\.\\d+\\.\\d+)\"");
                if (ip.Success)
                    ips[item.Key] = ip.Groups[1].Value;
            }

            if (ips.Count < vmids.Count)
            {
                AppendLog("Agent indisponible ou incomplet, fallback scan nmap/MAC." + Environment.NewLine);
                var scanned = ScanIpsByMac(host, privateKey, vmids);
                foreach (var item in scanned)
                    ips[item.Key] = item.Value;
            }

            return ips;
        }

        Dictionary<string, string> ScanIpsByMac(string host, string privateKey, Dictionary<string, string> vmids)
        {
            var macs = new Dictionary<string, string>();
            foreach (var item in vmids)
            {
                string config = RunSsh("root@" + host, "qm config " + item.Value, privateKey, true, false);
                Match mac = Regex.Match(config, "net0:\\s+\\S+=([0-9A-Fa-f:]{17}),");
                if (mac.Success)
                    macs[item.Key] = mac.Groups[1].Value.ToUpperInvariant();
            }

            string subnet = RunSsh("root@" + host, "ip -4 route show dev vmbr0 proto kernel scope link | awk '{print $1; exit}'", privateKey, true, false).Trim();
            if (string.IsNullOrWhiteSpace(subnet))
                subnet = "192.168.1.0/24";
            string scan = RunSsh("root@" + host, "nmap -sn " + subnet, privateKey, true, false);

            var found = new Dictionary<string, string>();
            string currentIp = "";
            foreach (string line in scan.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                Match report = Regex.Match(line, "Nmap scan report for .*\\((\\d+\\.\\d+\\.\\d+\\.\\d+)\\)");
                if (!report.Success)
                    report = Regex.Match(line, "Nmap scan report for (\\d+\\.\\d+\\.\\d+\\.\\d+)");
                if (report.Success)
                {
                    currentIp = report.Groups[1].Value;
                    continue;
                }

                Match mac = Regex.Match(line, "MAC Address:\\s+([0-9A-Fa-f:]{17})");
                if (mac.Success && currentIp.Length > 0)
                {
                    string normalized = mac.Groups[1].Value.ToUpperInvariant();
                    foreach (var item in macs)
                    {
                        if (item.Value == normalized)
                            found[item.Key] = currentIp;
                    }
                }
            }
            return found;
        }

        void PrintIps(Dictionary<string, string> ips)
        {
            AppendLog("IP trouvees" + Environment.NewLine);
            PrintIpLine(ips, "web");
            PrintIpLine(ips, "monitoring");
            if (ips.ContainsKey("web"))
                AppendLog("  web_url: http://" + ips["web"] + Environment.NewLine);
            if (ips.ContainsKey("monitoring"))
                AppendLog("  uptime_kuma_url: http://" + ips["monitoring"] + ":3001" + Environment.NewLine);
        }

        void PrintIpLine(Dictionary<string, string> ips, string role)
        {
            string ip = ips.ContainsKey(role) ? ips[role] : "<non trouvee>";
            AppendLog(role.PadRight(11) + ip + Environment.NewLine);
            if (ips.ContainsKey(role))
                AppendLog("  ssh -i " + Field("private_key") + " admincloud@" + ip + Environment.NewLine);
        }

        void GenerateInventory()
        {
            string stack = StackName();
            Dictionary<string, string> ips = stack == "azure" ? AzureIpsFromOutputs() : FindProxmoxIps();
            if (!ips.ContainsKey("web") || !ips.ContainsKey("monitoring"))
                throw new Exception("IP manquante pour Ansible.");

            string key = stack == "proxmox" ? OrDefault(Field("private_key"), PrivateKeyForStack(stack)) : PrivateKeyForStack(stack);
            if (ControlOs() == "windows")
                key = "~/.ssh/" + Path.GetFileName(ExpandUser(key));

            string inventory = "[web]\r\n" +
                "web01 ansible_host=" + ips["web"] + " ansible_user=admincloud\r\n\r\n" +
                "[monitoring]\r\n" +
                "monitoring01 ansible_host=" + ips["monitoring"] + " ansible_user=admincloud\r\n\r\n" +
                "[all:vars]\r\n" +
                "ansible_ssh_private_key_file=" + key + "\r\n" +
                "ansible_python_interpreter=/usr/bin/python3\r\n" +
                "ansible_ssh_common_args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'\r\n";
            string ansibleDir = Path.Combine(Root, "ansible");
            Directory.CreateDirectory(ansibleDir);
            File.WriteAllText(Path.Combine(ansibleDir, "inventaire.ini"), inventory, Encoding.UTF8);
            AppendLog("Inventaire Ansible mis a jour." + Environment.NewLine);
        }

        Dictionary<string, string> AzureIpsFromOutputs()
        {
            string output = RunProcess("terraform", "output -json", StackPath("azure"), true);
            var ips = new Dictionary<string, string>();
            Match web = Regex.Match(output, "\"web_public_ip\"\\s*:\\s*\\{[^}]*\"value\"\\s*:\\s*\"([^\"]+)\"");
            Match mon = Regex.Match(output, "\"monitoring_public_ip\"\\s*:\\s*\\{[^}]*\"value\"\\s*:\\s*\"([^\"]+)\"");
            if (web.Success) ips["web"] = web.Groups[1].Value;
            if (mon.Success) ips["monitoring"] = mon.Groups[1].Value;
            return ips;
        }

        void EnsureAnsible()
        {
            if (ControlOs() == "windows")
                EnsureAnsibleWsl();
            else
                EnsureAnsibleLinux();
        }

        void EnsureAnsibleWsl()
        {
            EnsureDebianWsl();
            string command = "command -v ansible-playbook || (sudo apt-get update && sudo apt-get install -y ansible openssh-client python3); ansible-galaxy collection install community.docker";
            RunProcess("wsl", "-d Debian -- bash -lc " + QuoteArg(command), Root);
        }

        void EnsureDebianWsl()
        {
            EnsureVirtualizationForWsl();

            if (!CommandExists("wsl"))
            {
                StartDebianWslInstall();
                throw new ActionRequiredException(WslInstallMessage());
            }

            string list = RunProcess("wsl", "-l -q", Root, true).Replace("\0", "");
            if (list.IndexOf("Debian", StringComparison.OrdinalIgnoreCase) < 0)
            {
                StartDebianWslInstall();
                throw new ActionRequiredException(WslInstallMessage());
            }

            string probe = RunProcess("wsl", "-d Debian -- bash -lc " + QuoteArg("echo ok"), Root, false);
            if (probe.IndexOf("ok", StringComparison.OrdinalIgnoreCase) < 0)
                throw new ActionRequiredException(WslInitMessage());
        }

        void EnsureVirtualizationForWsl()
        {
            string output = RunProcess("powershell", "-NoProfile -Command " + QuoteArg("(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty VirtualizationFirmwareEnabled)"), Root, false);
            if (output.IndexOf("False", StringComparison.OrdinalIgnoreCase) >= 0)
                throw new ActionRequiredException(WslVirtualizationMessage());
        }

        void StartDebianWslInstall()
        {
            RunProcess("powershell", "-NoProfile -ExecutionPolicy Bypass -Command \"Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -Command \\\"wsl --install --no-distribution; wsl --set-default-version 2; wsl --install -d Debian; Read-Host ''Appuie sur Entree pour fermer''\\\"'\"", Root);
        }

        string WslVirtualizationMessage()
        {
            return
                "WSL2 ne peut pas demarrer car la virtualisation est desactivee dans le BIOS/UEFI." + Environment.NewLine +
                "Sur ton CPU AMD, active l'option SVM Mode / AMD-V dans le BIOS, sauvegarde, puis redemarre Windows." + Environment.NewLine +
                "Ensuite relance IaC Assistant et clique a nouveau sur Installer/verifier Ansible.";
        }

        string WslInstallMessage()
        {
            return
                "Debian WSL2 vient d'etre lance en installation." + Environment.NewLine +
                "1. Si Windows le demande, redemarre le PC." + Environment.NewLine +
                "2. Ouvre Debian depuis le menu Demarrer." + Environment.NewLine +
                "3. Cree l'utilisateur Linux et son mot de passe." + Environment.NewLine +
                "4. Relance IaC Assistant, puis clique a nouveau sur Installer/verifier Ansible.";
        }

        string WslInitMessage()
        {
            return
                "Debian WSL est installe mais pas encore initialise." + Environment.NewLine +
                "Ouvre Debian depuis le menu Demarrer, cree l'utilisateur Linux, puis relance ce bouton.";
        }

        void EnsureAnsibleLinux()
        {
            if (CommandExists("ansible-playbook"))
            {
                RunProcess("ansible-playbook", "--version", Root);
                return;
            }
            if (CommandExists("apt-get"))
                RunProcess("sudo", "apt-get update && sudo apt-get install -y ansible", Root);
            else if (CommandExists("dnf"))
                RunProcess("sudo", "dnf install -y ansible", Root);
            else if (CommandExists("yum"))
                RunProcess("sudo", "yum install -y ansible", Root);
            else if (CommandExists("pacman"))
                RunProcess("sudo", "pacman -Sy --noconfirm ansible", Root);
            else
                throw new Exception("Gestionnaire de paquets non reconnu.");
        }

        void RunAnsible()
        {
            EnsureAnsible();
            GenerateInventory();

            if (ControlOs() == "windows")
            {
                string key = StackName() == "proxmox" ? OrDefault(Field("private_key"), PrivateKeyForStack(StackName())) : PrivateKeyForStack(StackName());
                CopyKeyToWsl(key);
                string rootWsl = WindowsPathToWsl(Root);
                RunProcess("wsl", "-d Debian -- bash -lc " + QuoteArg("cd " + ShellQuote(rootWsl) + " && ansible-playbook -i ansible/inventaire.ini ansible/playbook.yaml"), Root);
            }
            else
            {
                RunProcess("ansible-playbook", "-i " + QuoteArg(Path.Combine(Root, "ansible", "inventaire.ini")) + " " + QuoteArg(Path.Combine(Root, "ansible", "playbook.yaml")), Root);
            }
        }

        void CopyKeyToWsl(string key)
        {
            string expanded = ExpandUser(key);
            string wslPath = WindowsPathToWsl(expanded);
            string name = Path.GetFileName(expanded);
            string command = "mkdir -p ~/.ssh && cp " + ShellQuote(wslPath) + " ~/.ssh/" + name + " && chmod 600 ~/.ssh/" + name;
            RunProcess("wsl", "-d Debian -- bash -lc " + QuoteArg(command), Root);
        }

        void FullWorkflow()
        {
            if (prepareProxmoxCheck.Checked)
            {
                if (StackName() == "proxmox")
                    PrepareProxmox();
                else
                    PrepareAzure();
            }
            Terraform("init");
            Terraform("validate");
            Terraform("plan");
            if (autoApproveCheck.Checked)
                Terraform("apply");
            if (StackName() == "proxmox")
                PrintIps(FindProxmoxIps());
            else
                Terraform("output");
            if (includeAnsibleCheck.Checked)
                RunAnsible();
        }

        string RunSsh(string target, string remote, string privateKey, bool batch)
        {
            return RunSsh(target, remote, privateKey, batch, true);
        }

        string RunSsh(string target, string remote, string privateKey, bool batch, bool check)
        {
            if (!batch)
                return RunVisibleSsh(target, remote, privateKey, check);

            string args = "-o StrictHostKeyChecking=accept-new ";
            args += "-o BatchMode=yes ";
            string expanded = ExpandUser(privateKey);
            if (File.Exists(expanded))
                args += "-i " + QuoteArg(expanded) + " ";
            args += target + " " + QuoteArg(remote);
            return RunProcess("ssh", args, Root, check);
        }

        string RunVisibleSsh(string target, string remote, string privateKey, bool check)
        {
            AppendLog("Ouverture d'une fenetre SSH pour la connexion initiale a " + target + "." + Environment.NewLine);
            string expanded = ExpandUser(privateKey);
            string scriptPath = Path.Combine(Path.GetTempPath(), "iac-assistant-ssh.ps1");
            var script = new StringBuilder();
            script.AppendLine("$ErrorActionPreference = 'Continue'");
            script.AppendLine("Write-Host 'Connexion SSH initiale vers " + target.Replace("'", "''") + "'");
            script.AppendLine("$sshArgs = @('-o','StrictHostKeyChecking=accept-new')");
            if (File.Exists(expanded))
                script.AppendLine("$sshArgs += @('-i'," + PsQuote(expanded) + ")");
            script.AppendLine("$sshArgs += @(" + PsQuote(target) + "," + PsQuote(remote) + ")");
            script.AppendLine("& ssh @sshArgs");
            script.AppendLine("$code = $LASTEXITCODE");
            script.AppendLine("if ($code -ne 0) { Read-Host 'SSH a echoue. Appuie sur Entree pour fermer'; exit $code }");
            File.WriteAllText(scriptPath, script.ToString(), Encoding.UTF8);

            var psi = new ProcessStartInfo("powershell.exe", "-NoProfile -ExecutionPolicy Bypass -File " + QuoteArg(scriptPath));
            psi.UseShellExecute = true;
            psi.WindowStyle = ProcessWindowStyle.Normal;
            var process = Process.Start(psi);
            process.WaitForExit();
            if (check && process.ExitCode != 0)
                throw new Exception("Connexion SSH initiale echouee.");
            return "";
        }

        string RunProcess(string file, string args, string cwd)
        {
            return RunProcess(file, args, cwd, true);
        }

        string RunProcess(string file, string args, string cwd, bool check)
        {
            AppendLog("$ " + file + " " + args + Environment.NewLine);
            var psi = new ProcessStartInfo(file, args);
            psi.WorkingDirectory = cwd;
            psi.UseShellExecute = false;
            psi.RedirectStandardOutput = true;
            psi.RedirectStandardError = true;
            psi.CreateNoWindow = true;
            var process = new Process();
            process.StartInfo = psi;
            var output = new StringBuilder();
            process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs e)
            {
                if (e.Data != null)
                {
                    output.AppendLine(e.Data);
                    AppendLog(e.Data + Environment.NewLine);
                }
            };
            process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs e)
            {
                if (e.Data != null)
                {
                    output.AppendLine(e.Data);
                    AppendLog(e.Data + Environment.NewLine);
                }
            };
            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            process.WaitForExit();
            if (check && process.ExitCode != 0)
                throw new Exception("Commande echouee: " + file + " " + args);
            return output.ToString();
        }

        bool CommandExists(string name)
        {
            try
            {
                string finder = IsWindowsHost() ? "where" : "which";
                string output = RunProcess(finder, name, Root, false);
                return output.Trim().Length > 0;
            }
            catch
            {
                return false;
            }
        }

        bool IsWindowsHost()
        {
            return Environment.OSVersion.Platform == PlatformID.Win32NT;
        }

        string ReadTfvars(string stack)
        {
            string path = Path.Combine(stack, "terraform.tfvars");
            return File.Exists(path) ? File.ReadAllText(path) : "";
        }

        string GetTfvar(string stack, string name, string fallback)
        {
            string text = ReadTfvars(stack);
            Match match = Regex.Match(text, "(?m)^\\s*" + Regex.Escape(name) + "\\s*=\\s*(.+?)\\s*$");
            if (!match.Success)
                return fallback;
            string value = match.Groups[1].Value.Trim();
            if (value.StartsWith("\"") && value.EndsWith("\"") && value.Length >= 2)
                value = value.Substring(1, value.Length - 2);
            return value;
        }

        void SetTfvar(string stack, string name, string value)
        {
            SetTfvar(stack, name, value, false);
        }

        void SetTfvar(string stack, string name, string value, bool raw)
        {
            string path = Path.Combine(stack, "terraform.tfvars");
            string text = File.Exists(path) ? File.ReadAllText(path) : "";
            string hcl = raw ? value : "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
            string line = name + " = " + hcl;
            Regex regex = new Regex("(?m)^\\s*" + Regex.Escape(name) + "\\s*=.*$");
            if (regex.IsMatch(text))
                text = regex.Replace(text, line, 1);
            else
            {
                if (text.Length > 0 && !text.EndsWith("\n"))
                    text += Environment.NewLine;
                text += line + Environment.NewLine;
            }
            File.WriteAllText(path, text);
        }

        string EndpointHost(string stack)
        {
            string endpoint = GetTfvar(stack, "proxmox_endpoint", "https://192.168.1.126:8006/");
            Match match = Regex.Match(endpoint, "https?://([^/:]+)");
            return match.Success ? match.Groups[1].Value : "192.168.1.126";
        }

        string PrivateKeyForStack(string stackName)
        {
            string stack = StackPath(stackName);
            if (stackName == "proxmox")
                return GetTfvar(stack, "proxmox_ssh_private_key_path", "~/.ssh/tp_azure_ed25519");
            string publicKey = GetTfvar(stack, "ssh_public_key_path", "~/.ssh/tp_azure_ed25519.pub");
            return publicKey.EndsWith(".pub") ? publicKey.Substring(0, publicKey.Length - 4) : publicKey;
        }

        string ExpandUser(string path)
        {
            if (path.StartsWith("~/") || path.StartsWith("~\\"))
                return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), path.Substring(2));
            return Environment.ExpandEnvironmentVariables(path);
        }

        string WindowsPathToWsl(string path)
        {
            string full = Path.GetFullPath(path);
            Match match = Regex.Match(full, "^([A-Za-z]):\\\\(.*)$");
            if (!match.Success)
                return full.Replace("\\", "/");
            return "/mnt/" + match.Groups[1].Value.ToLowerInvariant() + "/" + match.Groups[2].Value.Replace("\\", "/");
        }

        string OrDefault(string value, string fallback)
        {
            return string.IsNullOrWhiteSpace(value) ? fallback : value;
        }

        string QuoteArg(string value)
        {
            return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
        }

        string ShellQuote(string value)
        {
            return "'" + value.Replace("'", "'\"'\"'") + "'";
        }

        string PsQuote(string value)
        {
            return "'" + value.Replace("'", "''") + "'";
        }

        class ActionRequiredException : Exception
        {
            public ActionRequiredException(string message) : base(message)
            {
            }
        }

        class ButtonSpec
        {
            public string Text;
            public Color Color;
            public EventHandler Handler;

            public ButtonSpec(string text, Color color, EventHandler handler)
            {
                Text = text;
                Color = color;
                Handler = handler;
            }
        }
    }
}
