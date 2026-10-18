#!/usr/bin/env python3
"""Audit/apply narrow Antigravity GPS research grants without printing settings."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile

READ_RULES = [f'command({cmd})' for cmd in (
    'rg', 'sed', 'cat', 'git status', 'git diff', 'git ls-files',
    'git rev-parse', 'git branch --show-current')]
READ_RULES += [f'read_url({domain})' for domain in (
    'developer.mozilla.org', 'developers.google.com', 'maplibre.org', 'wiki.openstreetmap.org')]


def configure(path, workspace, apply=False):
    data = json.loads(path.read_text()) if path.exists() else {}
    permissions = data.setdefault('permissions', {})
    allowed = permissions.setdefault('allow', [])
    trusted = data.setdefault('trustedWorkspaces', [])
    if not isinstance(allowed, list) or not isinstance(trusted, list):
        raise ValueError('permissions.allow/trustedWorkspaces phải là danh sách')
    blocked = set(permissions.get('deny', [])) | set(permissions.get('ask', []))
    conflicts = [rule for rule in READ_RULES if rule in blocked]
    if conflicts:
        raise ValueError('Quyền đã đặt deny/ask, cần xử lý thủ công: ' + ', '.join(conflicts))
    missing = [rule for rule in READ_RULES if rule not in allowed]
    print('Quyền đọc cần bổ sung: ' + (', '.join(missing) or 'không có'))
    if 'command(*)' in allowed or 'read_file(*)' in allowed or 'write_file(*)' in allowed:
        print('Lưu ý: cấu hình sẵn có chứa quyền wildcard; script không thay đổi các quyền này.')
    if apply and (missing or str(workspace) not in trusted):
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            backup_dir = Path(tempfile.mkdtemp(prefix='gps-permissions-backup-'))
            backup = backup_dir / 'settings.json'
            shutil.copy2(path, backup)
            backup.chmod(0o600)
            print(f'Backup: {backup}')
        allowed.extend(missing)
        if str(workspace) not in trusted:
            trusted.append(str(workspace))
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as output:
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.write('\n')
            temp_path = Path(output.name)
        temp_path.chmod(0o600)
        temp_path.replace(path)
        print('Đã áp dụng quyền đọc và trust đúng workspace.')
    return missing


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    configure(Path.home() / '.gemini/antigravity-cli/settings.json', Path.cwd().resolve(), args.apply)
