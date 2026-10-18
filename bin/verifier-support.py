"""Stable preparation inputs plus checked, mode-specific native build receipts."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024): value.update(block)
    return value.hexdigest()


def files_digest(paths, base=None):
    values = []
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.is_file(): raise ValueError('unknown or symlinked verifier input')
        values.append([str(path.relative_to(base) if base else path), digest(path)])
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def installed_tools(root):
    modules = root / 'node_modules'
    if modules.is_symlink() or not modules.is_dir(): raise ValueError('installed tool tree is unavailable')
    modules = modules.resolve()
    value = hashlib.sha256()
    for path in sorted(modules.rglob('*')):
        relative = path.relative_to(modules).as_posix()
        # This sole generated tree changes ABI during checked preparation.
        # Its loaded .node bytes are independently checked against the receipt.
        if relative == 'better-sqlite3/build' or relative.startswith('better-sqlite3/build/'):
            continue
        if path.is_symlink():
            if not path.resolve().is_relative_to(modules): raise ValueError('installed tool link escapes its source tree')
            content = 'link:' + os.readlink(path)
        elif path.is_file(): content = digest(path)
        elif path.is_dir(): continue
        else: raise ValueError('unknown installed tool input')
        value.update(relative.encode() + b'\0' + content.encode() + b'\0')
    return value.hexdigest()


def native_inputs(root):
    modules = root / 'node_modules'
    package = modules / 'better-sqlite3'
    paths = [root / 'package.json', root / 'package-lock.json', modules / '.package-lock.json']
    for name in ['better-sqlite3', 'electron', 'electron-builder']:
        paths.append(modules / name / 'package.json')
    paths += [package / 'binding.gyp']
    for folder in ['src', 'deps']:
        paths += [p for p in (package / folder).rglob('*') if p.is_file()]
    electron = modules / 'electron/dist'
    candidates = [electron / 'electron', electron / 'electron.exe',
                  electron / 'Electron.app/Contents/MacOS/Electron',
                  electron / 'Electron.app/Contents/Frameworks/Electron Framework.framework/Versions/A/Electron Framework']
    binaries = [path for path in candidates if path.is_file()]
    if not binaries: raise ValueError('Electron executable provenance is unavailable')
    paths += binaries
    for name in ['.npmrc', 'electron-builder.yml', 'electron-builder.yaml', 'electron-builder.json', 'electron-builder.js', 'electron-builder.cjs']:
        if (root / name).exists(): paths.append(root / name)
    node, npm = shutil.which('node'), shutil.which('npm')
    if not node or not npm: raise ValueError('Node or npm is unavailable')
    tools = {name: {'path': str(Path(path).resolve()), 'sha256': digest(Path(path).resolve())}
             for name, path in [('node', node), ('npm', npm)]}
    versions = subprocess.check_output([node, '-p', 'JSON.stringify(process.versions)'], timeout=5).decode().strip()
    config_paths = [Path.home() / '.npmrc']
    for setting in ['userconfig', 'globalconfig']:
        config_paths.append(Path(subprocess.check_output([npm, 'config', 'get', setting], cwd=root, timeout=5).decode().strip()))
    for name in ['NPM_CONFIG_USERCONFIG', 'NPM_CONFIG_GLOBALCONFIG', 'npm_config_userconfig', 'npm_config_globalconfig']:
        if os.environ.get(name): config_paths.append(Path(os.environ[name]))
    configs = [path for path in config_paths if path.exists()]
    return {'productInputs': files_digest(paths, root), 'tools': tools, 'versions': versions,
            'npmConfig': files_digest(configs),
            'buildEnvironment': hashlib.sha256(json.dumps({k: v for k, v in os.environ.items()
                if k.lower().startswith('npm_config_') or k in {'CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS'}}, sort_keys=True).encode()).hexdigest()}


def native_binary(root):
    path = root / 'node_modules/better-sqlite3/build/Release/better_sqlite3.node'
    if path.is_symlink() or not path.is_file(): raise ValueError('native database binary is unavailable')
    return path


def receipt(root):
    return root / 'build/dispatcher-tests/native-preparation.json'


def record_native(root, mode, inputs):
    path = receipt(root)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    value = {'version': 1, 'mode': mode, 'inputs': inputs, 'binary': digest(native_binary(root))}
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as output:
        json.dump(value, output)
        temporary = output.name
    os.replace(temporary, path)


def verify_native(root, inputs):
    path = receipt(root)
    if path.is_symlink() or not path.is_file(): raise ValueError('no checked native preparation receipt')
    value = json.loads(path.read_text())
    if (value.get('version') != 1 or value.get('mode') not in {'node', 'electron'} or
            value.get('inputs') != inputs or value.get('binary') != digest(native_binary(root))):
        raise ValueError('native database provenance changed or is unknown')
    # A successful, checked rebuild may change ABI and output bytes. The stable
    # input key stays equal across those intentional Node/Electron transitions.
    return inputs
