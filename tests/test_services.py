"""The local supervisor owns only processes it starts and can be paused safely."""
from persona_agent.services import Services
from persona_agent import setup_wizard as sw
import pytest


def test_close_terminates_only_registered_live_processes(tmp_path):
    calls = []
    class Process:
        def poll(self):
            return None
        def terminate(self):
            calls.append("terminate")
        def wait(self, timeout):
            calls.append("wait")
            return 0
    services = Services(tmp_path)
    services.processes["agent"] = Process()
    services.processes["astrbot"] = Process()
    services.close()
    assert calls == ["terminate", "wait", "terminate", "wait"]
    assert services.processes == {}
    services.close()
    assert len(calls) == 4


def test_shutdown_prevents_a_background_job_from_starting_more_children(tmp_path):
    services = Services(tmp_path)
    services.shutdown()
    with pytest.raises(RuntimeError, match="closed"):
        services.start_agent()
    with pytest.raises(RuntimeError, match="closed"):
        services.start_astrbot()


def test_agent_launcher_uses_fresh_configuration_and_never_puts_keys_in_argv(tmp_path, monkeypatch):
    services = Services(tmp_path)
    sw.write_env(tmp_path / ".env", {"LLM_API_KEY": "fresh-secret", "SERVER_PORT": "0"})
    monkeypatch.setenv("LLM_API_KEY", "stale-secret")
    launches = []
    monkeypatch.setattr(services, "_spawn", lambda *args, **kwargs: launches.append((args, kwargs)))
    monkeypatch.setattr(services, "_ready", lambda *args, **kwargs: None)
    services.start_agent()
    args, kwargs = launches[0]
    assert "fresh-secret" not in " ".join(args[1])
    assert kwargs["env"]["LLM_API_KEY"] == "fresh-secret"
    assert kwargs["env"]["AGENT_HOME"] == str(tmp_path)
    assert int(sw.env_get(tmp_path / ".env", "SERVER_PORT")) > 0
