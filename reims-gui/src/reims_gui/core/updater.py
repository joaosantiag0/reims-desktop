"""Sistema de Atualização do ReimsOS via GitHub Releases e Git.

Responsável por consultar atualizações públicas no GitHub, comparar versões,
baixar pacotes .deb de releases e aplicar atualizações no sistema operacional.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_REPO = "joaosantiag0/reims-desktop"
DEFAULT_VERSION = "0.1.0"


@dataclass
class ReleaseAsset:
    name: str
    size: int
    download_url: str
    content_type: str = "application/vnd.debian.binary-package"


@dataclass
class ReleaseInfo:
    tag_name: str
    version: str
    name: str
    body: str
    published_at: str
    html_url: str
    assets: List[ReleaseAsset] = field(default_factory=list)

    @property
    def deb_assets(self) -> List[ReleaseAsset]:
        """Retorna apenas os assets de pacotes Debian (.deb)."""
        return [a for a in self.assets if a.name.endswith(".deb")]


class SystemUpdater:
    """Gerenciador de atualizações do ReimsOS."""

    def __init__(
        self,
        repo: Optional[str] = None,
        current_version: Optional[str] = None,
    ) -> None:
        self.repo = repo or os.environ.get("REIMS_GITHUB_REPO", DEFAULT_REPO)
        self.current_version = current_version or self._detect_current_version()

    @staticmethod
    def _detect_current_version() -> str:
        """Detecta a versão atual do ReimsOS a partir do pacote ou arquivo de versão."""
        # 1. Tenta ler de /etc/reims-version
        version_file = Path("/etc/reims-version")
        if version_file.exists():
            try:
                v = version_file.read_text(encoding="utf-8").strip()
                if v:
                    return v
            except Exception as e:
                logger.debug("Falha ao ler /etc/reims-version: %s", e)

        # 2. Tenta ler via dpkg se disponível
        try:
            res = subprocess.run(
                ["dpkg-query", "-W", "-f=${Version}", "reims-core"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass

        # 3. Fallback para __version__ do pacote Python
        try:
            import reims_gui
            return getattr(reims_gui, "__version__", DEFAULT_VERSION)
        except Exception:
            return DEFAULT_VERSION

    @staticmethod
    def parse_version(v_str: str) -> Tuple[int, ...]:
        """Converte uma string de versão (ex: 'v0.2.1', '1.0.0') em tupla numérica para comparação."""
        clean = v_str.strip().lstrip("vV")
        # Extrai partes numéricas
        nums = re.findall(r"\d+", clean)
        if not nums:
            return (0, 0, 0)
        return tuple(int(n) for n in nums)

    def is_newer(self, remote_ver: str, local_ver: Optional[str] = None) -> bool:
        """Verifica se a versão remota é estritamente maior que a versão local."""
        local = local_ver or self.current_version
        v_remote = self.parse_version(remote_ver)
        v_local = self.parse_version(local)
        return v_remote > v_local

    def check_for_updates(self) -> Optional[ReleaseInfo]:
        """Consulta a API do GitHub Releases para verificar se há versão mais recente."""
        # Modo Mock para testes unitários ou ambientes sem rede
        if os.environ.get("REIMS_MOCK_UPDATER") == "1":
            mock_tag = os.environ.get("REIMS_MOCK_TAG", "v0.2.0")
            if self.is_newer(mock_tag, self.current_version):
                return ReleaseInfo(
                    tag_name=mock_tag,
                    version=mock_tag.lstrip("vV"),
                    name=f"ReimsOS {mock_tag} Release",
                    body="## Novidades do ReimsOS\n- Atualização de performance\n- Correções de compatibilidade",
                    published_at="2026-11-23T20:00:00Z",
                    html_url=f"https://github.com/{self.repo}/releases/tag/{mock_tag}",
                    assets=[
                        ReleaseAsset(
                            name=f"reims-core_{mock_tag.lstrip('vV')}_all.deb",
                            size=102400,
                            download_url=f"https://github.com/{self.repo}/releases/download/{mock_tag}/reims-core.deb",
                        ),
                        ReleaseAsset(
                            name=f"reims-gui_{mock_tag.lstrip('vV')}_all.deb",
                            size=204800,
                            download_url=f"https://github.com/{self.repo}/releases/download/{mock_tag}/reims-gui.deb",
                        ),
                    ],
                )
            return None

        url = f"https://api.github.com/repos/{self.repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": f"ReimsOS-Updater/{self.current_version}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "")
            remote_version = tag_name.lstrip("vV")

            if not self.is_newer(remote_version, self.current_version):
                logger.info(
                    "ReimsOS está atualizado (%s >= %s)",
                    self.current_version,
                    remote_version,
                )
                return None

            assets: List[ReleaseAsset] = []
            for asset in data.get("assets", []):
                assets.append(
                    ReleaseAsset(
                        name=asset.get("name", ""),
                        size=asset.get("size", 0),
                        download_url=asset.get("browser_download_url", ""),
                        content_type=asset.get("content_type", ""),
                    )
                )

            return ReleaseInfo(
                tag_name=tag_name,
                version=remote_version,
                name=data.get("name", tag_name),
                body=data.get("body", ""),
                published_at=data.get("published_at", ""),
                html_url=data.get("html_url", ""),
                assets=assets,
            )

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.warning("Nenhuma release encontrada no repositório %s", self.repo)
            else:
                logger.error("Erro HTTP ao consultar GitHub Releases: %s", e)
            return None
        except Exception as e:
            logger.error("Falha ao verificar atualizações do ReimsOS: %s", e)
            return None

    def download_assets(
        self,
        release: ReleaseInfo,
        target_dir: Path | str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[Path]:
        """Baixa os pacotes .deb da release para a pasta especificada."""
        dest = Path(target_dir)
        dest.mkdir(parents=True, exist_ok=True)
        downloaded: List[Path] = []

        deb_assets = release.deb_assets
        if not deb_assets:
            logger.warning("Nenhum pacote .deb encontrado nos assets da release %s", release.tag_name)
            return []

        # Modo Mock
        if os.environ.get("REIMS_MOCK_UPDATER") == "1":
            for asset in deb_assets:
                pkg_path = dest / asset.name
                pkg_path.write_bytes(b"MOCK_DEBIAN_PACKAGE")
                downloaded.append(pkg_path)
                if progress_callback:
                    progress_callback(asset.size, asset.size, asset.name)
            return downloaded

        for asset in deb_assets:
            pkg_path = dest / asset.name
            req = urllib.request.Request(
                asset.download_url,
                headers={"User-Agent": f"ReimsOS-Updater/{self.current_version}"},
            )

            logger.info("Baixando %s de %s...", asset.name, asset.download_url)
            with urllib.request.urlopen(req, timeout=30) as resp, open(pkg_path, "wb") as f:
                total_size = asset.size or int(resp.headers.get("Content-Length", 0))
                downloaded_size = 0
                block_size = 65536

                while True:
                    chunk = resp.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded_size, total_size, asset.name)

            downloaded.append(pkg_path)

        return downloaded

    def install_debs(
        self,
        deb_files: List[Path],
        dry_run: bool = False,
    ) -> Tuple[bool, str]:
        """Aplica os pacotes .deb no sistema usando apt/dpkg."""
        if not deb_files:
            return False, "Nenhum pacote fornecido para instalação"

        if dry_run or os.environ.get("REIMS_MOCK_UPDATER") == "1":
            file_names = ", ".join(p.name for p in deb_files)
            logger.info("[MODO SIMULAÇÃO] Instalando pacotes: %s", file_names)
            return True, f"Simulação de instalação bem-sucedida ({file_names})"

        file_paths = [str(p.resolve()) for p in deb_files]
        cmd = ["apt-get", "install", "--reinstall", "-y"] + file_paths

        # Se não for root, invoca via sudo
        if os.geteuid() != 0:
            cmd = ["sudo", "-E"] + cmd

        logger.info("Executando instalação de pacotes: %s", " ".join(cmd))
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                logger.info("Atualização instalada com sucesso!")
                return True, "Pacotes instalados com sucesso!"
            else:
                err_msg = res.stderr.strip() or res.stdout.strip()
                logger.error("Falha ao instalar pacotes: %s", err_msg)
                return False, f"Falha na instalação: {err_msg}"
        except Exception as e:
            logger.error("Exceção ao executar instalação de pacotes: %s", e)
            return False, str(e)

    def update_from_git(
        self,
        repo_url: Optional[str] = None,
        branch: str = "master",
        dry_run: bool = False,
    ) -> Tuple[bool, str]:
        """Atualiza componentes do sistema clonando/puxando a branch master do GitHub."""
        git_url = repo_url or f"https://github.com/{self.repo}.git"

        if dry_run or os.environ.get("REIMS_MOCK_UPDATER") == "1":
            logger.info("[MODO SIMULAÇÃO] Atualização git de %s (%s)", git_url, branch)
            return True, f"Simulação de atualização via git concluída ({git_url})"

        work_dir = Path("/tmp/reims-git-update")
        try:
            if not (work_dir / ".git").exists():
                logger.info("Clonando repositório %s para %s...", git_url, work_dir)
                if work_dir.exists():
                    shutil.rmtree(work_dir)
                subprocess.run(
                    ["git", "clone", "--depth=1", "-b", branch, git_url, str(work_dir)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            else:
                logger.info("Puxando atualizações do git em %s...", work_dir)
                subprocess.run(
                    ["git", "-C", str(work_dir), "pull", "--ff-only"],
                    check=True,
                    capture_output=True,
                    text=True,
                )

            # Executa build e empacotamento local se o script estiver presente
            build_script = work_dir / "packaging" / "scripts" / "build_all.sh"
            if build_script.exists():
                logger.info("Recompilando pacotes do repositório clonado...")
                subprocess.run([str(build_script)], check=True, cwd=str(work_dir))
                debs = list((work_dir / "dist").glob("*.deb"))
                if debs:
                    return self.install_debs(debs, dry_run=dry_run)

            return True, "Repositório git sincronizado com sucesso!"

        except Exception as e:
            logger.error("Erro durante atualização via git: %s", e)
            return False, str(e)
