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


def test_force_flag_bypasses_update_check_freshness():
    """Running .ntw.sh --force syncs the repo cache even when last-update-check is fresh"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        cmd = (
            "bash -c 'export NTW_LOG_LEVEL=3 NTW_HOME=/tmp/ntw-force-test; "
            "mkdir -p $NTW_HOME; date +%s > $NTW_HOME/last-update-check; "
            "/ntw/.ntw.sh --force'"
        )
        respond_to(child, '#', cmd)
        child.expect('#', timeout=60)
        output = child.before
        assert 'Force flag set. Setting do_update_cache to 1' in output, f"Got: {output}"
        assert 'Cloning into' in output, f"Expected a repo clone despite fresh last-update-check, got: {output}"
    finally:
        cleanup_container(child, container_name)


def test_sourcing_with_no_home_does_not_crash():
    """.ntw.sh must not rely on $HOME being set: some tools (e.g. Spotless's npm formatter)
    launch child processes with a minimal environment that has PATH but no HOME."""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        cmd = "env -i PATH=\"$PATH\" NTW_LOG_LEVEL=2 bash -c 'source /ntw/.ntw.sh; echo SOURCED_OK'"
        respond_to(child, '#', cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'unbound variable' not in output, f"Got: {output}"
        assert 'SOURCED_OK' in output, f"Expected successful sourcing, got: {output}"
    finally:
        cleanup_container(child, container_name)


def test_sourcing_does_not_leak_escape_codes_to_stdout():
    """The tput capability probe must not write its reset sequence to real stdout - callers
    that treat a wrapped command's stdout as a clean protocol channel (e.g. Spotless reading
    a version string) would otherwise get corrupted output."""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        cmd = (
            "bash -c 'export NTW_OFFLINE=1; source /ntw/.ntw.sh 2>/dev/null | od -An -tx1 | tr -d \" \\n\"; "
            "echo; echo DONE_OD'"
        )
        respond_to(child, '#', cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'DONE_OD' in output, f"Got: {output}"
        assert '1b28' not in output.lower(), (
            f"Found a leaked escape sequence on stdout: {output}"
        )
    finally:
        cleanup_container(child, container_name)


def test_npmrc_registry_falls_back_to_home_npmrc():
    """When the local .npmrc has no registry entry (or doesn't exist), fall back to ~/.npmrc"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        setup_cmd = (
            "bash -c 'echo \"registry=https://home.registry.example.test/\" > ~/.npmrc "
            "&& cd /workspace && rm -f .npmrc "
            "&& NTW_LOG_LEVEL=2 source /ntw/.ntw.sh'"
        )
        respond_to(child, '#', setup_cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'NTW_NPM_URL: https://home.registry.example.test/' in output, f"Got: {output}"
    finally:
        cleanup_container(child, container_name)


def test_npmrc_local_registry_takes_priority_over_home():
    """A registry entry in the local .npmrc wins over one in ~/.npmrc"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        setup_cmd = (
            "bash -c 'echo \"registry=https://home.registry.example.test/\" > ~/.npmrc "
            "&& cd /workspace && echo \"registry=https://local.registry.example.test/\" > .npmrc "
            "&& NTW_LOG_LEVEL=2 source /ntw/.ntw.sh'"
        )
        respond_to(child, '#', setup_cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'NTW_NPM_URL: https://local.registry.example.test/' in output, f"Got: {output}"
    finally:
        cleanup_container(child, container_name)


def test_select_node_skips_download_when_system_node_matches():
    """selectNode uses an already-installed system node of the requested version instead of downloading"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        setup_cmd = (
            "mkdir -p /fakebin && printf '#!/bin/bash\\necho v18.20.4\\n' > /fakebin/node && chmod +x /fakebin/node"
        )
        respond_to(child, '#', setup_cmd)
        child.expect('#', timeout=30)
        setup_cmd = (
            "PATH=/fakebin:$PATH NTW_LOG_LEVEL=2 NTW_OFFLINE=1 bash -c 'source /ntw/.ntw.sh; selectNode v18.20.4'"
        )
        respond_to(child, '#', setup_cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'Using it instead of provisioning' in output, f"Got: {output}"
        assert 'Downloading' not in output, f"Expected no download, got: {output}"
    finally:
        cleanup_container(child, container_name)


def test_select_node_download_has_a_connect_timeout():
    """A curl call in selectNode against an unroutable host fails fast instead of hanging"""
    container_name = f"ntw-test-{os.getpid()}"
    child = spawn_container(container_name)
    try:
        cmd = (
            "bash -c 'export NTW_LOG_LEVEL=2 NTW_NODE_DIST_URL=http://203.0.113.1/dist; "
            "source /ntw/.ntw.sh; "
            "time timeout 20 bash -c \"selectNode v18.20.4\" ; echo EXIT_CODE=$?'"
        )
        respond_to(child, '#', cmd)
        child.expect('#', timeout=30)
        output = child.before
        assert 'EXIT_CODE=124' not in output, f"curl hung past the 20s outer timeout: {output}"
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
