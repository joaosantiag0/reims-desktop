# Reims Desktop

<div align="center">
  <img src="iso-builder/customization/reims-logo.png" alt="Reims Desktop Logo" width="140" />
  <h3>Sistema Operacional e Interface Gráfica para Virtualização macOS com Aceleração Vulkan</h3>
  <p>Construído sobre o Ubuntu 24.04 LTS (Noble) com ambiente ultra-leve LXQt, Calamares e suporte nativo ao <a href="https://github.com/steelbrain/reims-vgpu">reims-vgpu</a>.</p>
</div>

---

## 🚀 Visão Geral

O **Reims Desktop** é uma distribuição Linux especializada projetada para transformar qualquer PC ou notebook compatível (Intel/AMD + GPUs NVIDIA ou AMD) em uma estação de trabalho de alta performance para virtualização de **macOS** com aceleração de GPU por hardware via **Vulkan** (`/dev/udmabuf` + KVM).

O projeto elimina bloatware, otimiza o kernel e a pilha gráfica e entrega uma experiência pronta para uso, com instalador gráfico em português, inglês e espanhol.

---

## 🛠️ Binários Oficiais (`reims-desktop*`)

Todos os binários do projeto foram padronizados sob o prefixo `reims-desktop*` para facilitar o uso no terminal e automações:

| Binário | Descrição |
| :--- | :--- |
| **`reims-desktop`** | Interface gráfica principal em Qt (Reims Desktop Control Center) para gerenciar, criar e executar máquinas virtuais. *(compatível com `reims-gui`)* |
| **`reims-desktop-ctl`** | Linha de comando para diagnóstico (`doctor`), alocação de GPUs e provisionamento de VMs macOS. *(compatível com `reims-ctl`)* |
| **`reims-desktop-update`** | Utilitário CLI para verificação e aplicação de atualizações do sistema direto do GitHub Releases ou Git master. *(compatível com `reims-update`)* |
| **`reims-desktop-util`** | Ferramenta utilitária de suporte a imagens de disco e automação QEMU. *(compatível com `reims-util`)* |

---

## 📦 Estrutura do Repositório

```text
reims-desktop/
├── reims-gui/          # Aplicação gráfica Qt6/PySide6 (Reims Desktop) com suporte a i18n
├── packaging/          # Automação de empacotamento Debian (.deb)
│   ├── templates/      # Estrutura base de reims-core, reims-gui e reims-vgpu
│   └── scripts/        # Scripts para compilar e gerar os pacotes .deb
├── iso-builder/        # Pipeline de construção e remasterização da ISO Live CD
│   ├── config/         # Configurações do Calamares, pacotes essenciais e autostart
│   ├── customization/  # Logos Plymouth, papéis de parede, touchpad e prompts de boas-vindas
│   └── scripts/        # Scripts de build da ISO (build_iso.sh, remaster_iso.sh)
└── .github/workflows/  # CI/CD: Testes automatizados e publicação de releases
```

---

## 🔄 Sistema de Atualização Contínua

O **Reims Desktop** possui um mecanismo de atualização integrado diretamente com este repositório público no GitHub:

1. **Pela Interface Gráfica:**
   - Clique no botão **"Atualizações"** na barra superior do Reims Desktop.
   - O aplicativo consulta as releases do GitHub em segundo plano e apresenta as notas da versão com opção de atualização com um clique.

2. **Pelo Terminal:**
   ```bash
   # Verifica se há novas atualizações
   reims-desktop-update --check

   # Instala a versão mais recente dos pacotes oficiais
   reims-desktop-update

   # Ou atualiza diretamente a partir da branch principal do Git
   reims-desktop-update --git
   ```

---

## 🧪 Testes Automatizados

O repositório segue regras estritas de qualidade e cobertura de testes automatizados (em conformidade com [agents.md](agents.md)):

```bash
# Executa toda a suíte de testes (ISO, Reims Desktop e Empacotamento Debian)
python3 -m unittest discover -s iso-builder/tests -p "test_*.py"
PYTHONPATH=reims-gui/src python3 -m unittest discover -s reims-gui/tests -p "test_*.py"
python3 -m unittest discover -s packaging/tests -p "test_*.py"
```

---

## 📄 Licença

Distribuído sob licença de código aberto. Veja os arquivos de controle para os detalhes de cada componente.
