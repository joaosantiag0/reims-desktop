# Guidelines for AI Agents (agents.md)

This document establishes operational guidelines, best practices, and mandatory standards for any AI Agent working in the **Reims Desktop** repository and its subprojects (such as `reims-gui`, `.deb` packaging scripts, and ISO automation).

---

## 1. Automated Testing (Mandatory)

> [!IMPORTANT]
> **Always create and run automated tests whenever possible.**

* **Proactive Coverage:** Any new feature, bug fix, or code refactoring must be accompanied by relevant automated tests (unit tests, integration tests, or smoke tests).
* **Execution Before Completion:** The agent must **never** consider a task complete without first running all test suites locally and verifying that all tests pass with 100% success.
* **Isolation and Mock Modes:** Because this project interfaces with hardware virtualization (KVM, Vulkan, `/dev/udmabuf`, dedicated GPUs), always maintain test and mock modes that allow the test suite to run in any environment (such as macOS development machines without KVM or headless CI/CD servers).
* **Zero Tolerance for Broken Tests:** In case of any test failure, fixing the reported issue takes immediate priority before making new commits or replying to the user.

---

## 2. Code Quality and Design Standards

* **Python (`reims-gui`):**
  * Strict type annotations (`type hints` with `from __future__ import annotations`).
  * Modular code separating presentation (Qt/PySide6/qt_compat), business logic (`core`), and internationalization (`i18n`).
  * Explicit exception handling and structured logging (`logging`).
* **Internationalization (i18n):**
  * Never add hardcoded static strings directly into the graphical interface. Always use translation keys (`t("key")`) and keep locale files synchronized in `locales/` (`en_US.json`, `pt_BR.json`, `es_ES.json`).
* **Shell Scripts / Bash (Build and ISO):**
  * All shell scripts must start with `set -euo pipefail`.
  * Ensure automation scripts are ShellCheck compliant and do not rely on arbitrary hardcoded absolute paths.

---

## 3. Workflow and Version Control

1. **Pre-check:** Inspect current repository status (`git status`, existing test suites).
2. **Incremental Implementation:** Make cohesive changes in small, logical steps.
3. **Validation:** Run all test suites across projects.
4. **Clear Communication:** Document changes clearly with absolute file links and state test results.
