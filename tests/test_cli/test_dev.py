import re
import sys
import time
import signal
import threading
import subprocess
from typing import List

import pytest

from prisma import utils
from prisma.http import client
from prisma.utils import temp_env_update
from prisma.binaries import platform
from ..utils import Testdir, Runner


PRISMA_MODULE = [sys.executable, '-m', 'prisma']


def test_playground_skip_generate_no_client(runner: Runner, monkeypatch) -> None:
    monkeypatch.setattr(utils, 'module_exists', lambda m: False, raising=True)
    result = runner.invoke(['py', 'dev', 'playground', '--skip-generate'])
    assert result.exit_code == 1
    assert result.output == 'Prisma Client Python has not been generated yet.\n'


@pytest.mark.asyncio
async def test_playground(testdir: Testdir) -> None:
    def output_reader(proc: subprocess.Popen, lines: List[str]) -> List[str]:
        for line in iter(proc.stdout.readline, b''):
            lines.append(line.decode('utf-8'))

        return lines

    lines = []
    schema = testdir.make_schema()
    args = PRISMA_MODULE + ['py', 'dev', 'playground', f'--schema={schema}']

    # ensure host information is still logged
    # with DEBUG logging disabled
    with temp_env_update({'PRISMA_PY_DEBUG': '0'}):
        process = subprocess.Popen(args=args, stdout=subprocess.PIPE)

    thread = threading.Thread(target=output_reader, args=(process, lines))

    try:
        thread.start()
        time.sleep(5)

        stdout = ''.join(lines)
        print(stdout)

        assert 'Generated Prisma Client Python' in stdout

        match = re.search(
            r'Started http server on (?P<url>http://127.0.0.1:\d+)', stdout
        )
        assert match is not None
        url = match.group('url')

        resp = await client.request('GET', url)
        assert resp.status == 200
        assert '<title>Rust Playground</title>' in await resp.text()
    finally:
        if platform.name() == 'windows':
            sig = signal.CTRL_C_EVENT
        else:
            sig = signal.SIGINT

        process.send_signal(sig)
        thread.join(timeout=5)
