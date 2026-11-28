# Reims Web

Console web (estilo Proxmox VE) para gerenciar as VMs macOS aceleradas do Reims
Desktop a partir de qualquer navegador, sem abrir mão do `reims-ctl` como
backend. Escuta em **`:8006`** (mesma porta convencionada pelo Proxmox).

- **Backend:** FastAPI + WebSocket (uvicorn), reutilizando **1:1** a camada core
  Qt-free do `reims-gui` (`reims_gui.core.ctl_client`, `system_stats`,
  `models`, `i18n`).
- **Frontend:** SPA em HTML/CSS/JS puro, **sem build de Node**, servida pelo
  próprio FastAPI — enxuto o suficiente para entrar no ISO/.deb.
- **Auth:** senha de administrador → bearer token em memória (TTL 24 h). Sem
  senha configurada, roda em modo aberto (apenas para dev/local).
- **Mock mode:** `--mock` conversa com o ctl em memória; desenvolva e teste em
  qualquer máquina (inclusive macOS, sem KVM/Vulkan), conforme `agents.md`.

## Rodar em desenvolvimento

```bash
cd reims-web
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Mock (sem KVM/Vulkan) — http://localhost:8006
PYTHONPATH=../reims-gui/src:src python -m reims_web --mock --dev

# Com auth (produção-like)
REIMS_WEB_PASSWORD=s3cret PYTHONPATH=../reims-gui/src:src python -m reims_web
```

## API

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| POST | `/api/login` | senha → token |
| POST | `/api/logout` | revoga o token |
| GET | `/api/auth/status` | `{auth_required}` |
| GET | `/api/i18n?lang=` | dicionário de traduções (locales compartilhadas) |
| GET/POST | `/api/vms` | lista VMs / inicia criação (task em background) |
| POST | `/api/vms/{name}/start` | liga VM |
| POST | `/api/vms/{name}/stop?force=` | desliga/força desligamento |
| DELETE | `/api/vms/{name}` | exclui VM |
| GET | `/api/vms/{name}/console` | sondagem de console (noVNC groundwork) |
| GET | `/api/doctor` | diagnóstico KVM/udmabuf/Vulkan/QEMU |
| GET | `/api/gpus` | GPUs físicas disponíveis |
| GET | `/api/stats` | amostra única de CPU/RAM do host |
| WS | `/api/ws/stats?token=` | stream ao vivo de CPU/RAM |
| GET | `/api/tasks/{id}` | progresso da criação de VM |

## Produção (ReimsOS)

Empacotado como `reims-web`, com o serviço systemd `reims-web.service`
escutando em `0.0.0.0:8006`. Defina a senha do admin via
`/etc/reims/web-password` (root-only) ou `REIMS_WEB_PASSWORD` no unit.

## Testes

```bash
PYTHONPATH=../reims-gui/src:src python -m unittest discover -s tests -p "test_*.py"
```

## Roadmap (paridade Proxmox)

- [x] Dashboard com doctor, gráficos CPU/RAM ao vivo e cards de VM
- [x] Start/stop/force-stop/delete + wizard de criação com progresso
- [x] Auth por senha + token, i18n (pt_BR/en_US/es_ES)
- [ ] Console web via noVNC (depende de endpoint VNC do QEMU no backend)
- [ ] Empacotamento `.deb` (`reims-web`) + unit systemd no ISO
- [ ] Métricas por VM (guest agent) e snapshots
