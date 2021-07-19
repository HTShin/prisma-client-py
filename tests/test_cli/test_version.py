import re
import json

from _pytest.monkeypatch import MonkeyPatch

from tests.utils import Runner


HASH = re.compile(r'[a-f0-9]{40}')
PLACEHOLDER = re.compile(r'.*')
SEMANTIC_VERSION = re.compile(r'(\d?\d\.){2}\d?\d')
PATTERN = re.compile(
    f'prisma               : (?P<prisma>{SEMANTIC_VERSION.pattern})\n'
    f'prisma client python : (?P<prisma_client_python>{SEMANTIC_VERSION.pattern})\n'
    f'platform             : (?P<platform>{PLACEHOLDER.pattern})\n'
    f'engines              : (?P<engines>{HASH.pattern})\n'
    f'install path         : (?P<install_path>{PLACEHOLDER.pattern})\n'
    f'installed extras     : (?P<installed_extras>{PLACEHOLDER.pattern})'
)


def test_version(runner: Runner) -> None:
    result = runner.invoke(['py', 'version'])
    assert result.exit_code == 0
    assert PATTERN.match(result.output) is not None, result.output


def test_version_json(runner: Runner) -> None:
    result = runner.invoke(['py', 'version', '--json'])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert SEMANTIC_VERSION.match(data['prisma'])
    assert SEMANTIC_VERSION.match(data['prisma-client-python'])
    assert PLACEHOLDER.match(data['platform'])
    assert HASH.match(data['engines'])
    assert isinstance(data['installed-extras'], list)


def test_same_output(runner: Runner) -> None:
    result = runner.invoke(['py', 'version', '--json'])
    assert result.exit_code == 0
    data = json.loads(result.output)

    result = runner.invoke(['py', 'version'])
    assert result.exit_code == 0
    output = result.output

    match = PATTERN.match(output)
    assert match is not None

    # "-" is not a valid character in regex group names
    groups = {k.replace('_', '-'): v for k, v in match.groupdict().items()}
    data['installed-extras'] = str(data['installed-extras'])
    assert groups == data


def test_no_extras_installed(runner: Runner, monkeypatch: MonkeyPatch) -> None:
    from prisma.cli.commands import version

    def patched_import_module(mod: str) -> None:
        raise ImportError(mod)

    monkeypatch.setattr(version, 'import_module', patched_import_module, raising=True)

    result = runner.invoke(['py', 'version'])
    assert result.exit_code == 0

    match = PATTERN.match(result.output)
    assert match is not None
    assert match.group('installed_extras') == '[]'


def test_no_extras_installed_json(runner: Runner, monkeypatch: MonkeyPatch) -> None:
    from prisma.cli.commands import version

    def patched_import_module(mod: str) -> None:
        raise ImportError(mod)

    monkeypatch.setattr(version, 'import_module', patched_import_module, raising=True)

    result = runner.invoke(['py', 'version', '--json'])
    assert result.exit_code == 0

    data = json.loads(result.output)
    assert data['installed-extras'] == []
