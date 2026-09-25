"""Deployment regressions; runnable on Windows and Linux without credentials."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
from persona_agent.endpoints import chat_completions_url


class DeploymentTests(unittest.TestCase):
    def test_non_qq_deployment_does_not_require_onebot(self):
        from persona_agent import health
        with patch.dict(os.environ, {'BOT_QQ': ''}), \
                patch.object(health, 'CHECKS', [('OneBot bridge', health.check_onebot, True)]), \
                patch.object(health, '_get', side_effect=AssertionError('must not call OneBot')):
            results = health.run_checks()
        self.assertTrue(health.all_critical_ok(results))
        self.assertIsNone(results[0]['ok'])
        self.assertFalse(results[0]['critical'])

    def test_qq_through_a_connector_does_not_require_onebot(self):
        from persona_agent import health
        env = {'BOT_QQ': '10000', 'GATEWAY_NATIVE_PLATFORMS': 'aiocqhttp'}
        with patch.dict(os.environ, env), \
                patch.object(health, 'CHECKS', [('OneBot bridge', health.check_onebot, True)]), \
                patch.object(health, '_get', side_effect=OSError('connection refused')):
            results = health.run_checks()
        self.assertFalse(results[0]['ok'])
        self.assertFalse(results[0]['critical'])
        self.assertTrue(health.all_critical_ok(results))

    def test_endpoint_spellings(self):
        for base in ("https://example.org", "https://example.org/",
                     "https://example.org/v1", "https://example.org/v1/",
                     "https://example.org/v1/chat/completions"):
            self.assertEqual(chat_completions_url(base),
                             "https://example.org/v1/chat/completions")
        self.assertEqual(chat_completions_url("https://example.org/proxy/v1/"),
                         "https://example.org/proxy/v1/chat/completions")


    def test_main_honors_dotenv_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copyfile(ROOT / 'main.py', root / 'main.py')
            (root / '.env').write_text('HOST=127.0.0.2\nPORT=8129\n', encoding='utf-8')
            code = ("import runpy, uvicorn, json; "
                    "uvicorn.Server.run=lambda self, *a, **k: print(json.dumps("
                    "{'host': self.config.host, 'port': self.config.port})); "
                    "runpy.run_path('main.py', run_name='__main__')")
            env = {**os.environ, 'PYTHONPATH': str(ROOT), 'AGENT_HOME': temp}
            for key in ('HOST', 'PORT', 'PYTHON_DOTENV_DISABLED'):
                env.pop(key, None)
            for override, expected in ((None, 8129), ('8130', 8130)):
                if override:
                    env['PORT'] = override
                result = subprocess.run([sys.executable, '-c', code], cwd=temp,
                                        env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = json.loads(result.stdout)
                self.assertEqual(config['host'], '127.0.0.2')
                self.assertEqual(config['port'], expected)
