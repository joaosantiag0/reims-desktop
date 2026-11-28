"""Reims Web — web-based VM manager (Proxmox-style) for Reims Desktop.

Reuses the Qt-free core layer of reims-gui (`reims_gui.core.*`) to talk to the
`reims-ctl` CLI and expose it over a small FastAPI application, so the macOS VM
fleet can be managed from any browser on the LAN (http://host:8006).
"""

__version__ = "0.1.0"
