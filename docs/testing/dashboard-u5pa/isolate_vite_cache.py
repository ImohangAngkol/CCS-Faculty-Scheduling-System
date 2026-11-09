"""Test-only cache isolation; never edits the actual application's Vite config."""
import hashlib
import json
from pathlib import Path
import tempfile


def prepare(snapshot,owned):
    snapshot=Path(snapshot).resolve();owned=Path(owned).resolve()
    assert snapshot.name=='repository' and snapshot.parent==owned
    assert owned.parent==Path(tempfile.gettempdir()).resolve()
    assert owned.name.startswith(('u5c-r1-snapshot-','u5o-frontend-'))
    path=snapshot/'frontend/vite.config.ts';raw=path.read_bytes();text=raw.decode('utf-8')
    assert text.count('defineConfig({')==1 and 'cacheDir:' not in text
    destination=owned/'vite-cache'
    updated=text.replace('defineConfig({','defineConfig({cacheDir:'+json.dumps(str(destination))+',')
    path.write_text(updated,encoding='utf-8',newline='\n')
    return dict(scope='Owned test config transformation only; plugins, source, API and production config unchanged',
        original_config_sha256=hashlib.sha256(raw).hexdigest(),test_config_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        isolated_cache=str(destination),shared_node_modules_cache_used=False,
        rationale='Existing dependency junction otherwise allows different disposable Vite roots to use the same writable dependency cache. This risk is established statically; it is not proven to explain previous render timeouts.')
