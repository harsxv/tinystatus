import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

import tinystatus


def mock_response(status=None, error=None):
    response = MagicMock(status=status)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=response, side_effect=error)
    context.__aexit__ = AsyncMock(return_value=None)
    return context


# ---------------------------------------------------------------------------
# check_http
# ---------------------------------------------------------------------------

class TestCheckHttp:
    @pytest.mark.asyncio
    async def test_returns_true_on_expected_status(self):
        with patch("tinystatus.aiohttp.ClientSession.get", return_value=mock_response(200)):
            result = await tinystatus.check_http("https://example.com", 200, False)
            assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_unexpected_status(self):
        with patch("tinystatus.aiohttp.ClientSession.get", return_value=mock_response(500)):
            result = await tinystatus.check_http("https://example.com", 200, False)
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_connection_error(self):
        with patch("tinystatus.aiohttp.ClientSession.get",
                   return_value=mock_response(error=ConnectionError("refused"))):
            result = await tinystatus.check_http("https://example.com", 200, False)
            assert result is False

    @pytest.mark.asyncio
    async def test_selfsigned_disables_ssl(self):
        with patch("tinystatus.aiohttp.ClientSession.get", return_value=mock_response(200)):
            result = await tinystatus.check_http("https://selfsigned.local", 200, True)
            assert result is True


# ---------------------------------------------------------------------------
# check_ping
# ---------------------------------------------------------------------------

class TestCheckPing:
    @pytest.mark.asyncio
    async def test_returns_true_when_ping_succeeds(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("tinystatus.subprocess.run", return_value=mock_result) as mock_run:
            result = await tinystatus.check_ping("8.8.8.8")
            assert result is True
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_ping_fails(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("tinystatus.subprocess.run", return_value=mock_result):
            result = await tinystatus.check_ping("unreachable.host")
            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        with patch("tinystatus.subprocess.run", side_effect=OSError("not found")):
            result = await tinystatus.check_ping("badhost")
            assert result is False


# ---------------------------------------------------------------------------
# check_port
# ---------------------------------------------------------------------------

class TestCheckPort:
    @pytest.mark.asyncio
    async def test_returns_true_when_port_open(self):
        mock_writer = MagicMock(wait_closed=AsyncMock())
        with patch("tinystatus.asyncio.open_connection", return_value=(AsyncMock(), mock_writer)):
            result = await tinystatus.check_port("localhost", 5432)
            assert result is True
            mock_writer.close.assert_called_once()
            mock_writer.wait_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_false_when_port_closed(self):
        with patch("tinystatus.asyncio.open_connection", side_effect=ConnectionRefusedError):
            result = await tinystatus.check_port("localhost", 9999)
            assert result is False


# ---------------------------------------------------------------------------
# run_checks
# ---------------------------------------------------------------------------

class TestRunChecks:
    @pytest.mark.asyncio
    async def test_runs_mixed_check_types(self):
        checks = [
            {"name": "Web", "type": "http", "host": "https://example.com", "expected_code": 200},
            {"name": "DNS", "type": "ping", "host": "8.8.8.8"},
            {"name": "DB", "type": "port", "host": "localhost", "port": 5432},
        ]

        with patch("tinystatus.check_http", new_callable=AsyncMock, return_value=True) as mock_http, \
             patch("tinystatus.check_ping", new_callable=AsyncMock, return_value=True) as mock_ping, \
             patch("tinystatus.check_port", new_callable=AsyncMock, return_value=False) as mock_port:

            results = await tinystatus.run_checks(checks)

            assert len(results) == 3
            assert results[0] == {"name": "Web", "url": None, "status": True}
            assert results[1] == {"name": "DNS", "url": None, "status": True}
            assert results[2] == {"name": "DB", "url": None, "status": False}

            mock_http.assert_awaited_once_with("https://example.com", 200, False)
            mock_ping.assert_awaited_once_with("8.8.8.8")
            mock_port.assert_awaited_once_with("localhost", 5432)

    @pytest.mark.asyncio
    async def test_http_check_with_selfsigned(self):
        checks = [
            {"name": "Local", "type": "http", "host": "https://local.dev", "expected_code": 200, "ssc": True},
        ]
        with patch("tinystatus.check_http", new_callable=AsyncMock, return_value=True) as mock_http:
            results = await tinystatus.run_checks(checks)
            assert results[0]["status"] is True
            mock_http.assert_awaited_once_with("https://local.dev", 200, True)

    @pytest.mark.asyncio
    async def test_preserves_url_field(self):
        checks = [
            {"name": "GitHub", "type": "http", "host": "https://github.com",
             "expected_code": 200, "url": "https://docs.github.com"},
        ]
        with patch("tinystatus.check_http", new_callable=AsyncMock, return_value=True):
            results = await tinystatus.run_checks(checks)
            assert results[0]["url"] == "https://docs.github.com"


# ---------------------------------------------------------------------------
# History management
# ---------------------------------------------------------------------------

class TestLoadHistory:
    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        with patch.object(tinystatus, "STATUS_HISTORY_FILE", str(tmp_path / "nonexistent.json")):
            assert tinystatus.load_history() == {}

    def test_loads_existing_history(self, tmp_path):
        history_file = tmp_path / "history.json"
        data = {"service1": [{"timestamp": "2024-01-01T00:00:00", "status": True}]}
        history_file.write_text(json.dumps(data))
        with patch.object(tinystatus, "STATUS_HISTORY_FILE", str(history_file)):
            assert tinystatus.load_history() == data


class TestSaveHistory:
    def test_writes_history_to_file(self, tmp_path):
        history_file = tmp_path / "history.json"
        data = {"service1": [{"timestamp": "2024-01-01T00:00:00", "status": True}]}
        with patch.object(tinystatus, "STATUS_HISTORY_FILE", str(history_file)):
            tinystatus.save_history(data)
        assert json.loads(history_file.read_text()) == data


class TestUpdateHistory:
    def test_appends_new_entries(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text("{}")
        results = {
            "Group 1": [
                {"name": "Web", "status": True},
                {"name": "API", "status": False},
            ]
        }
        with patch.object(tinystatus, "STATUS_HISTORY_FILE", str(history_file)):
            tinystatus.update_history(results)
            history = tinystatus.load_history()

        assert "Web" in history
        assert "API" in history
        assert len(history["Web"]) == 1
        assert history["Web"][0]["status"] is True
        assert history["API"][0]["status"] is False

    def test_respects_max_history_entries(self, tmp_path):
        history_file = tmp_path / "history.json"
        existing = {"Web": [{"timestamp": f"t{i}", "status": True} for i in range(100)]}
        history_file.write_text(json.dumps(existing))

        results = {"Group 1": [{"name": "Web", "status": False}]}
        with patch.object(tinystatus, "STATUS_HISTORY_FILE", str(history_file)), \
             patch.object(tinystatus, "MAX_HISTORY_ENTRIES", 100):
            tinystatus.update_history(results)
            history = tinystatus.load_history()

        assert len(history["Web"]) == 100
        assert history["Web"][-1]["status"] is False
