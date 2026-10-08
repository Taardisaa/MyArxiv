"""Render the focused cache with the existing ArxivFeed binary and templates."""
import functools
import http.server
import json
import pathlib
import shutil
import subprocess
import tempfile
import threading
import tomllib
from collect import collect, ROOT

if __name__ == '__main__':
    import sys
    data = collect(sys.argv[1] if len(sys.argv)>1 else None)
    count = sum(len(p) for groups in data.values() for p in groups.values())
    if not count:
        raise SystemExit('No matching papers; refusing to overwrite the published feed. Check the API or scope.')
    scope = tomllib.loads((ROOT/'scope.toml').read_text())
    with tempfile.TemporaryDirectory() as tmp:
        work = pathlib.Path(tmp)
        for name in ['includes','statics','scripts']:shutil.copytree(ROOT/name,work/name)
        (work/'cache.json').write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False))
        class QuietHandler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=tmp))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        # cache_url must be at root, before the [scripts] table.
        config = (ROOT/'config.toml').read_text().replace('[scripts]',f'cache_url = "http://127.0.0.1:{server.server_port}/cache.json"\n\n[scripts]')
        (work/'config.toml').write_text(config)
        try:subprocess.run([str(ROOT/'arxivfeed')],cwd=work,check=True,timeout=90)
        finally:server.shutdown();server.server_close()
        shutil.copytree(work/'target',ROOT/'target',dirs_exist_ok=True)
    (ROOT/'target/scope.json').write_text(json.dumps({'name':scope['name'],'retention_days':scope['retention_days'],'max_papers':scope['max_papers'],'papers':count},indent=2))
    print(f'Rendered {count} papers; hard cap {scope["max_papers"]}, retention {scope["retention_days"]} days')
