# Diretrizes para Agentes de IA (agents.md)

Este documento estabelece as diretrizes operacionais, boas práticas e padrões mandatórios para qualquer Agente de IA trabalhando no repositório do **ReimsOS** e em seus subprojetos (como o `reims-gui`, scripts de empacotamento `.deb` e automação da ISO).

---

## 1. Testes Automatizados (Mandatório)

> [!IMPORTANT]
> **Sempre que possível, crie e execute testes automatizados.**

* **Cobertura Proativa:** Qualquer nova funcionalidade, correção de bug ou refatoração de código deve vir acompanhada dos respectivos testes automatizados (testes unitários, testes de integração ou smoke tests).
* **Execução Antes da Entrega:** O agente **nunca** deve considerar uma tarefa finalizada sem antes executar os testes localmente e verificar que todos passaram com 100% de sucesso.
* **Isolamento e Modos Mock:** Como este projeto lida com virtualização e hardware específico (KVM, Vulkan, `/dev/udmabuf`, GPUs dedicadas), sempre implemente e mantenha modos de teste e simulação (mock) que permitam rodar a suíte de testes em qualquer ambiente (como máquinas de desenvolvimento sem KVM ou servidores de CI/CD).
* **Tolerância Zero a Testes Quebrados:** Em caso de falha em qualquer teste, a correção do problema reportado deve ser priorizada imediatamente antes de qualquer novo commit ou resposta ao usuário.

---

## 2. Qualidade de Código e Padrões de Projeto

* **Python (`reims-gui`):**
  * Uso de anotações de tipo estritas (`type hints` com `from __future__ import annotations`).
  * Código modular, separando camada de apresentação (Qt/PySide6), regras de negócio (`core`) e internacionalização (`i18n`).
  * Tratamento explícito de exceções e logs estruturados (`logging`).
* **Internacionalização (i18n):**
  * Nunca adicione strings estáticas diretamente na interface gráfica. Sempre utilize as chaves de tradução (`t("chave")`) e mantenha sincronizados os arquivos em `locales/` (`pt_BR.json`, `en_US.json`, `es_ES.json`).
* **Scripts Shell / Bash (Build e ISO):**
  * Todos os scripts shell devem iniciar com `set -euo pipefail`.
  * Verifique se scripts de automação são compatíveis com ShellCheck e não dependem de caminhos absolutos arbitrários.

---

## 3. Fluxo de Trabalho e Versionamento

1. **Verificação Prévia:** Analisar o estado atual do repositório (`git status`, testes existentes).
2. **Implementação Incremental:** Realizar alterações coesas e em pequenos passos lógicos.
3. **Validação:** Rodar a suíte de testes (`python3 -m unittest discover -s tests -p "test_*.py"`).
4. **Comunicação Clara:** Documentar o que foi feito, apontar para os arquivos criados ou modificados com links absolutos e destacar os testes executados.
