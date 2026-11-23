# Reims Control Center (reims-gui)

Interface gráfica nativa (GUI) para gerenciamento de máquinas virtuais macOS com aceleração gráfica [reims-vgpu](https://github.com/steelbrain/reims-vgpu) através do utilitário `reims-ctl`.

Construído para o **ReimsOS** (base Ubuntu 24.04 LTS / LXQt), mas compatível com qualquer distribuição Linux com suporte a KVM e Vulkan.

---

## Recursos

* **Gerenciador de VMs:** Listagem visual com status em tempo real (Executando, Desligada, Erro), vCPUs, RAM e vGPU associada.
* **Assistente de Criação (New VM Wizard):**
  * Escolha da versão do macOS (macOS 26 Tahoe, macOS 15 Sequoia, macOS 14 Sonoma).
  * Ajuste de vCPUs, RAM e tamanho de disco com sliders intuitivos.
  * Seleção de GPU física para aceleração Vulkan.
  * Download direto de instaladores oficiais da Apple via `reims-util`.
* **Painel de Diagnóstico (Host Health):**
  * Verificação em tempo real de KVM (`/dev/kvm`), suporte a `/dev/udmabuf`, drivers Vulkan (NVIDIA/AMD/Intel) e binário QEMU compatível.
* **Ações Rápidas:**
  * Iniciar VM (abre janela gráfica dedicada com aceleração gráfica).
  * Visualizador em terminal (`reims-ctl view`).
  * Parada suave (ACPI) ou forçada.
  * Ajuste de configurações da máquina (`reims-ctl set`).
* **Internacionalização (i18n):**
  * Suporte nativo completo para **Português do Brasil (pt_BR)**, **Inglês (en_US)** e **Espanhol (es_ES)**, com detecção automática do idioma do sistema e troca dinâmica na barra superior.
* **Modo Mock / Demonstração:**
  * Permite rodar e testar a interface mesmo em computadores sem o hardware KVM/Vulkan instalado (`reims-gui --mock`).

---

## Instalação e Execução

### Requisitos
* Python >= 3.10
* `PySide6` (Qt 6)
* `reims-ctl` e `qemu-reims-vgpu` instalados no sistema (ou utilize a flag `--mock`).

### Executando em Ambiente Virtual

```bash
cd reims-gui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Executar a aplicação
python3 -m reims_gui.main

# Executar em modo mock (simulação para testes de UI)
python3 -m reims_gui.main --mock
```

---

## Estrutura do Código

```
reims-gui/
├── src/reims_gui/
│   ├── main.py              # Ponto de entrada da aplicação
│   ├── core/
│   │   ├── models.py        # Modelos de dados (VmInfo, GpuDevice, DoctorHealth)
│   │   └── ctl_client.py    # Wrapper assíncrono para o CLI reims-ctl (+ modo Mock)
│   ├── i18n/
│   │   ├── translator.py    # Gerenciador de traduções com suporte a troca dinâmica
│   │   └── locales/         # Dicionários de idiomas (pt_BR, en_US, es_ES)
│   └── ui/
│       ├── main_window.py   # Janela principal
│       ├── theme.py         # Folhas de estilo modernas para Qt6
│       ├── widgets/         # Componentes: vm_card, doctor_bar, header
│       └── dialogs/         # Assistente de criação de VM e diálogo de ajustes
└── tests/                   # Testes unitários do cliente e i18n
```
