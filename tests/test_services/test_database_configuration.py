import builtins
import runpy
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import sqlalchemy


def load_database_configuration(monkeypatch, url, available):
    """Exercise module startup; replace only DB connection and driver imports."""
    from src import config
    memory_engine = sqlalchemy.create_engine('sqlite:///:memory:')
    original_import = builtins.__import__
    attempted_urls = []

    def import_driver(name, *args, **kwargs):
        if name in {'psycopg', 'psycopg2'}:
            if name not in available:
                raise ImportError('Driver unavailable')
            return ModuleType(name)
        return original_import(name, *args, **kwargs)

    def capture_engine(database_url, **kwargs):
        attempted_urls.append(database_url)
        return memory_engine

    monkeypatch.setattr(config, 'get_settings', lambda: SimpleNamespace(database_url=url))
    monkeypatch.setattr(builtins, '__import__', import_driver)
    monkeypatch.setattr(sqlalchemy, 'create_engine', capture_engine)
    try:
        module = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'src/db.py'))
        return module, attempted_urls
    finally:
        memory_engine.dispose()


@pytest.mark.parametrize('available,driver', [({'psycopg', 'psycopg2'}, 'psycopg'), ({'psycopg'}, 'psycopg'),
                                               ({'psycopg2'}, 'psycopg2')])
def test_generic_postgres_uses_an_installed_driver(monkeypatch, available, driver):
    module, attempted = load_database_configuration(monkeypatch, 'postgresql://test@db.example/test', available)
    assert attempted == [f'postgresql+{driver}://test@db.example/test']
    assert not module['is_sqlite']


def test_missing_postgres_drivers_fails_without_sqlite_fallback(monkeypatch):
    with pytest.raises(RuntimeError, match='PostgreSQL.*driver'):
        load_database_configuration(monkeypatch, 'postgresql://test@db.example/test', set())


@pytest.mark.parametrize('url', ['postgresql+psycopg://test@db.example/test',
                                'postgresql+psycopg2://test@db.example/test'])
def test_explicit_postgres_driver_is_honored(monkeypatch, url):
    _, attempted = load_database_configuration(monkeypatch, url, {'psycopg', 'psycopg2'})
    assert attempted == [url]


def test_explicit_missing_postgres_driver_cannot_select_sqlite(monkeypatch):
    _, attempted = load_database_configuration(monkeypatch, 'postgresql+psycopg://test@db.example/test', set())
    assert attempted == ['postgresql+psycopg://test@db.example/test']


def test_explicit_sqlite_url_is_preserved(monkeypatch):
    _, attempted = load_database_configuration(monkeypatch, 'sqlite:///:memory:', set())
    assert attempted == ['sqlite:///:memory:']
