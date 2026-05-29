"""
Deployer — pushes a generated scraper to the Hetzner server and adds crontab entry.
"""
import subprocess
import logging
from pathlib import Path

SERVER = "root@5.78.183.141"
SSH_KEY = Path.home() / ".ssh" / "id_ed25519"
REMOTE_BODIES = "/opt/pharma-scraper/bodies"
REMOTE_RUNNER = "/opt/pharma-scraper/runner.py"

log = logging.getLogger("deployer")


def _ssh(cmd: str) -> tuple[int, str]:
    result = subprocess.run(
        ["ssh", "-i", str(SSH_KEY), "-o", "StrictHostKeyChecking=no", SERVER, cmd],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode, result.stdout + result.stderr


def _scp(local: Path, remote: str) -> bool:
    result = subprocess.run(
        ["scp", "-i", str(SSH_KEY), "-o", "StrictHostKeyChecking=no",
         str(local), f"{SERVER}:{remote}"],
        capture_output=True, text=True, timeout=30,
    )
    return result.returncode == 0


def deploy(body_file: Path, market: dict) -> bool:
    """
    1. SCP the scraper to the server
    2. Add import + instantiation to runner.py
    3. Add crontab entry
    Returns True on success.
    """
    body_code = f"{market['body']}_{market['code']}"
    country_code = market['code']
    fname = body_file.name
    module_name = fname.replace(".py", "")

    # Derive class name from file
    class_name = _infer_class_name(body_file)
    if not class_name:
        log.error(f"Could not determine class name from {fname}")
        return False

    # 1. Upload file
    if not _scp(body_file, f"{REMOTE_BODIES}/{fname}"):
        log.error(f"SCP failed for {fname}")
        return False
    log.info(f"Uploaded {fname} to server")

    # 2. Add import to runner.py if not already there
    rc, out = _ssh(f"grep -q '{class_name}' {REMOTE_RUNNER} && echo 'exists' || echo 'missing'")
    if "missing" in out:
        import_line = f"from bodies.{module_name} import {class_name}"
        instance_line = f"    {class_name}(),"
        # Add import after last 'from bodies' import
        patch = (
            f"sed -i '/^from bodies\\./{{h;d}};x;/^from bodies\\./{{p;s/.*/from bodies.{module_name} import {class_name}/;p;d}}' {REMOTE_RUNNER}"
        )
        # Simpler: append import near top, append instance near end
        _ssh(f"sed -i '/^from bodies\\.zamra_zambia/a {import_line}' {REMOTE_RUNNER}")
        _ssh(f"sed -i '/ZAMRAZambiaScraper(),/a {instance_line}' {REMOTE_RUNNER}")
        log.info(f"Added {class_name} to runner.py")

    # 3. Add crontab entry
    # Stagger at :55 past each hour to avoid collisions; use body_code hash for minute offset
    minute = (hash(body_code) % 55)
    hour = 7  # All new scrapers run in the 07:xx UTC block
    cron_line = (
        f"{minute} {hour} * * * "
        f"cd /opt/pharma-scraper && export $(cat .env | xargs) && "
        f".venv/bin/python3 runner.py --body {body_code} "
        f">> /var/log/pharma-scraper.log 2>&1"
    )
    rc, existing = _ssh("crontab -l 2>/dev/null")
    if body_code not in existing:
        new_cron = existing.rstrip() + f"\n{cron_line}\n"
        _ssh(f"echo '{new_cron}' | crontab -")
        log.info(f"Added crontab entry for {body_code} at {minute} {hour} UTC")

    return True


def _infer_class_name(body_file: Path) -> str | None:
    """Extract the scraper class name from the file."""
    import re
    src = body_file.read_text()
    m = re.search(r"^class (\w+)\(BaseRegulatoryScraper\)", src, re.MULTILINE)
    return m.group(1) if m else None
