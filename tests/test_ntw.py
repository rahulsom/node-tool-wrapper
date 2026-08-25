import os

from conftest import cleanup_container, respond_to, spawn_container


def test_select_node_caches_download():
    """A second selectNode call for the same version/os/arch reuses the cached tarball"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        select_cmd = "bash -c 'export NTW_LOG_LEVEL=2 NTW_OFFLINE=1; source /ntw/.ntw.sh; selectNode v18.20.4'"
        respond_to(child, '#', select_cmd)
        child.expect('#', timeout=120)
        first_output = child.before
        assert "doesn't exist locally" in first_output or 'Downloading' in first_output

        child.sendline(select_cmd)
        child.expect('#', timeout=60)
        second_output = child.before
        assert 'Using cached' in second_output, f"Expected cache hit, got: {second_output}"
    finally:
        cleanup_container(child, container_name)


def test_select_tool_skips_reinstall_when_version_matches():
    """selectTool does not reinstall a tool that is already at the requested version"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        install_cmd = (
            "bash -c 'export NTW_LOG_LEVEL=2 NTW_OFFLINE=1 NPM_CONFIG_PROGRESS=false; source /ntw/.ntw.sh; "
            "selectNode v20.11.0; selectTool npm 10.5.0'"
        )
        respond_to(child, '#', install_cmd)
        child.expect('#', timeout=120)
        first_output = child.before
        assert 'is at version 10.2.4. Installing 10.5.0' in first_output, f"Got: {first_output}"

        child.sendline(install_cmd)
        child.expect('#', timeout=60)
        second_output = child.before
        assert 'is already at version' in second_output, f"Expected skip message, got: {second_output}"
        assert 'Installing 10.5.0' not in second_output
    finally:
        cleanup_container(child, container_name)


def test_npmrc_registry_overrides_default_npm_url():
    """A registry entry in .npmrc is picked up as NTW_NPM_URL instead of the default"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        setup_cmd = (
            "bash -c 'cd /workspace && echo \"registry=https://registry.example.test/\" > .npmrc "
            "&& NTW_LOG_LEVEL=2 source /ntw/.ntw.sh'"
        )
        respond_to(child, '#', setup_cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'NTW_NPM_URL: https://registry.example.test/' in output, f"Got: {output}"
    finally:
        cleanup_container(child, container_name)


def test_ci_env_skips_update_check():
    """Sourcing with CI set does not attempt to git clone/pull the update-check repo"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        cmd = "bash -c 'export NTW_LOG_LEVEL=2 CI=true; source /ntw/.ntw.sh'"
        respond_to(child, '#', cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'Running on CI. Skipping ntw update check.' in output, f"Got: {output}"
        assert 'Cloning into' not in output, f"Expected no git clone, got: {output}"
    finally:
        cleanup_container(child, container_name)


def test_offline_env_skips_update_check():
    """Sourcing with NTW_OFFLINE=1 does not attempt to git clone/pull the update-check repo"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        cmd = "bash -c 'export NTW_LOG_LEVEL=2 NTW_OFFLINE=1; source /ntw/.ntw.sh'"
        respond_to(child, '#', cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'NTW_OFFLINE=1. Skipping ntw update check.' in output, f"Got: {output}"
        assert 'Cloning into' not in output, f"Expected no git clone, got: {output}"
    finally:
        cleanup_container(child, container_name)


def test_log_level_suppresses_console_output_but_not_log_file():
    """NTW_LOG_LEVEL gates what's printed to the console, but every message is always written to NTW_LOG_FILE"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        cmd = (
            "bash -c 'export NTW_LOG_LEVEL=0; export NTW_LOG_FILE=/tmp/ntw-quiet.log; "
            "source /ntw/.ntw.sh > /tmp/ntw-quiet.out 2>&1; "
            "echo CONSOLE_INFO_COUNT=$(grep -c INFO /tmp/ntw-quiet.out); "
            "echo FILE_INFO_COUNT=$(grep -c INFO /tmp/ntw-quiet.log)'"
        )
        respond_to(child, '#', cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'CONSOLE_INFO_COUNT=0' in output, f"Got: {output}"
        assert 'FILE_INFO_COUNT=0' not in output, f"Expected log file to contain INFO entries, got: {output}"
    finally:
        cleanup_container(child, container_name)
