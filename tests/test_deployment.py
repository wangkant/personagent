"""Deployment regressions; runnable on Windows and Linux without credentials."""
import io
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


class _JSONResponse(io.BytesIO):
    """What urlopen returns, as far as health._get / _post_json use it."""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class DeploymentTests(unittest.TestCase):
    def test_non_qq_deployment_does_not_require_onebot(self):
        from persona_agent import health
        with patch.dict(os.environ, {'QQ_BOT_ID': ''}), \
                patch.object(health, 'CHECKS', [('OneBot bridge', health.check_onebot, True)]), \
                patch.object(health, '_get', side_effect=AssertionError('must not call OneBot')):
            results = health.run_checks()
        self.assertTrue(health.all_critical_ok(results))
        self.assertIsNone(results[0]['ok'])
        self.assertFalse(results[0]['critical'])

    def test_qq_through_a_connector_does_not_require_onebot(self):
        from persona_agent import health
        env = {'QQ_BOT_ID': '10000', 'CONNECTOR_QQ_PLATFORMS': 'aiocqhttp',
               'QQ_ONEBOT_URL': 'http://127.0.0.1:3000'}
        with patch.dict(os.environ, env), \
                patch.object(health, 'CHECKS', [('OneBot bridge', health.check_onebot, True)]), \
                patch.object(health, '_get', side_effect=OSError('connection refused')):
            results = health.run_checks()
        self.assertFalse(results[0]['ok'])
        self.assertFalse(results[0]['critical'])
        self.assertTrue(health.all_critical_ok(results))

    def test_a_blank_onebot_url_is_not_configured_not_failing(self):
        from persona_agent import health
        env = {'QQ_BOT_ID': '10000', 'QQ_ONEBOT_URL': '', 'CONNECTOR_QQ_PLATFORMS': ''}
        with patch.dict(os.environ, env), \
                patch.object(health, 'CHECKS', [('OneBot bridge', health.check_onebot, True)]), \
                patch.object(health, '_get', side_effect=AssertionError('must not call OneBot')):
            results = health.run_checks()
        self.assertIsNone(results[0]['ok'])
        self.assertIn('not configured', results[0]['detail'])
        self.assertTrue(health.all_critical_ok(results))

    def test_loopback_probes_bypass_the_proxy(self):
        from persona_agent import health
        self.assertTrue(health._is_loopback('http://127.0.0.1:3000/get_login_info'))
        self.assertTrue(health._is_loopback('http://localhost:11434/v1'))
        self.assertTrue(health._is_loopback('http://[::1]:8080/'))
        self.assertFalse(health._is_loopback('https://api.deepseek.com/v1'))
        opened = []

        def opener(kind):
            def _open(req, timeout=None):
                opened.append((kind, req.full_url))
                return _JSONResponse(b'{"data": {}}')
            return _open

        with patch.object(health._DIRECT, 'open', side_effect=opener('direct')), \
                patch.object(health.urllib.request, 'urlopen', side_effect=opener('env')):
            health._get('http://127.0.0.1:3000/get_login_info')
            health._get('https://example.org/x')
        self.assertEqual(opened, [('direct', 'http://127.0.0.1:3000/get_login_info'),
                                  ('env', 'https://example.org/x')])

    def test_a_probe_retries_without_a_field_a_reasoning_model_refuses(self):
        import urllib.error
        from persona_agent import health
        sent = []

        def fake_urlopen(req, timeout=None):
            body = json.loads(req.data)
            sent.append(sorted(body))
            if 'max_tokens' in body:
                raise urllib.error.HTTPError(
                    req.full_url, 400, 'Bad Request', {},
                    io.BytesIO(b'{"error": {"message": "Unsupported parameter: '
                               b"'max_tokens' is not supported with this model. "
                               b"Use 'max_completion_tokens' instead.\"}}"))
            return _JSONResponse(b'{"choices": [{"message": {"content": "ok"}}]}')

        with patch.object(health.urllib.request, 'urlopen', side_effect=fake_urlopen):
            out = health._post_json('https://api.openai.com/v1/chat/completions',
                                    {'model': 'gpt-5-mini', 'max_tokens': 8, 'messages': []},
                                    {'Authorization': 'Bearer k'})
        self.assertEqual(out['choices'][0]['message']['content'], 'ok')
        self.assertEqual(sent, [['max_tokens', 'messages', 'model'],
                                ['max_completion_tokens', 'messages', 'model']])

    def test_endpoint_spellings(self):
        for base in ("https://example.org", "https://example.org/",
                     "https://example.org/v1", "https://example.org/v1/",
                     "https://example.org/v1/chat/completions"):
            self.assertEqual(chat_completions_url(base),
                             "https://example.org/v1/chat/completions")
        self.assertEqual(chat_completions_url("https://example.org/proxy/v1/"),
                         "https://example.org/proxy/v1/chat/completions")

    def test_a_vendor_version_root_gets_only_chat_completions(self):
        from persona_agent.endpoints import embeddings_url
        cases = {
            "https://open.bigmodel.cn/api/paas/v4":
                "https://open.bigmodel.cn/api/paas/v4/chat/completions",
            "https://ark.cn-beijing.volces.com/api/v3/":
                "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            "https://generativelanguage.googleapis.com/v1beta/openai/":
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            # A bare /openai is Groq's root, which still needs its /v1.
            "https://api.groq.com/openai":
                "https://api.groq.com/openai/v1/chat/completions",
            "https://proxy.corp/llm-proxy":
                "https://proxy.corp/llm-proxy/v1/chat/completions",
        }
        for base, want in cases.items():
            self.assertEqual(chat_completions_url(base), want)
            self.assertEqual(embeddings_url(base),
                             want[:-len("/chat/completions")] + "/embeddings")


    def test_main_honors_dotenv_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copyfile(ROOT / 'main.py', root / 'main.py')
            (root / '.env').write_text('SERVER_HOST=127.0.0.2\nSERVER_PORT=8129\n', encoding='utf-8')
            code = ("import runpy, uvicorn, json; "
                    "uvicorn.Server.run=lambda self, *a, **k: print(json.dumps("
                    "{'host': self.config.host, 'port': self.config.port})); "
                    "runpy.run_path('main.py', run_name='__main__')")
            env = {**os.environ, 'PYTHONPATH': str(ROOT), 'AGENT_HOME': temp}
            for key in ('SERVER_HOST', 'SERVER_PORT', 'PYTHON_DOTENV_DISABLED'):
                env.pop(key, None)
            for override, expected in ((None, 8129), ('8130', 8130)):
                if override:
                    env['SERVER_PORT'] = override
                result = subprocess.run([sys.executable, '-c', code], cwd=temp,
                                        env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                config = json.loads(result.stdout)
                self.assertEqual(config['host'], '127.0.0.2')
                self.assertEqual(config['port'], expected)
