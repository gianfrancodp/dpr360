import installer_cli


class DummyLogger:
    def __init__(self, *_args, **_kwargs):
        pass


def complete_tools():
    return {
        "exiftool": "exiftool.exe",
        "rawtherapee": "rawtherapee-cli.exe",
        "pto_gen": "pto_gen.exe",
        "cpfind": "cpfind.exe",
        "cpclean": "cpclean.exe",
        "autooptimiser": "autooptimiser.exe",
        "pano_modify": "pano_modify.exe",
        "nona": "nona.exe",
        "enblend": "enblend.exe",
    }


def test_installer_returns_zero_for_complete_toolchain(monkeypatch):
    monkeypatch.setattr(installer_cli, "UsageLogger", DummyLogger)
    monkeypatch.setattr(installer_cli, "load_config", lambda _root: {})
    monkeypatch.setattr(installer_cli, "detect_tools", lambda _root, _cfg: complete_tools())

    assert installer_cli.main([]) == 0


def test_installer_returns_nonzero_for_partial_toolchain(monkeypatch, capsys):
    partial = complete_tools()
    partial["exiftool"] = ""
    monkeypatch.setattr(installer_cli, "UsageLogger", DummyLogger)
    monkeypatch.setattr(installer_cli, "load_config", lambda _root: {})
    monkeypatch.setattr(installer_cli, "detect_tools", lambda _root, _cfg: partial)

    assert installer_cli.main([]) == installer_cli.PARTIAL_TOOLCHAIN_EXIT_CODE
    assert "Mancano: exiftool" in capsys.readouterr().out


def test_auto_install_failure_is_reported(monkeypatch, capsys):
    partial = complete_tools()
    partial["exiftool"] = ""
    monkeypatch.setattr(installer_cli, "UsageLogger", DummyLogger)
    monkeypatch.setattr(installer_cli, "load_config", lambda _root: {})
    monkeypatch.setattr(installer_cli, "detect_tools", lambda _root, _cfg: partial)
    monkeypatch.setattr(
        installer_cli,
        "install_exiftool_official",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("download failed")),
    )

    assert installer_cli.main(["--auto"]) == installer_cli.PARTIAL_TOOLCHAIN_EXIT_CODE
    output = capsys.readouterr().out
    assert "fallback manuale" in output
    assert "download failed" in output
