from dpr360.process import external_process_env


def test_windows_external_process_env_removes_posix_locale_variables():
    source = {
        "PATH": r"C:\Windows\System32",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "LC_CTYPE": "C.UTF-8",
    }

    result = external_process_env(source, platform="nt")

    assert result == {"PATH": r"C:\Windows\System32"}
    assert source["LANG"] == "C.UTF-8"


def test_non_windows_external_process_env_preserves_locale_variables():
    source = {"PATH": "/usr/bin", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"}

    assert external_process_env(source, platform="posix") == source
