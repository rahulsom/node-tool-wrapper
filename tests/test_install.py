import os
import subprocess

import pexpect

from conftest import cleanup_container, respond_to, spawn_container

NODE_MARKER = 'What version of nodejs do you want to install?'
TOOL_NAME_MARKER = 'What tool do you want to install?'
TOOL_VERSION_MARKER_NPM = 'What version of npm do you want to install?'
TOOL_VERSION_MARKER_YARN = 'What version of yarn do you want to install?'


def _run_docker_and_copy_wrapper(container_name, tool_name):
    """Copy the generated wrapper file from container and clean up"""
    filename = f'{tool_name}w'
    result = subprocess.run(
        ['docker', 'cp', f'{container_name}:/workspace/{filename}', '-'],
        capture_output=True,
        text=True,
        check=True
    )
    subprocess.run(['docker', 'rm', '-f', container_name],
                  capture_output=True, check=False)
    return result.stdout


def test_preconfigured_npm():
    """Test that pre-configured npmw works correctly"""
    child = spawn_container(mount=(os.getcwd(), '/workspace'))
    respond_to(child, '#', 'cd /workspace')
    respond_to(child, '#', './npmw')
    child.expect('#', timeout=120)
    output = child.before
    assert 'npm@11.6.0' in output, f"Expected npm version 11.6.0, got: {output}"
    cleanup_container(child)


def _run_install(container_name, node_version, tool_name, tool_version_marker=None, tool_version=None):
    child = spawn_container(
        container_name,
        command='/ntw/install.sh',
        extra_args='-i'
    )
    try:
        respond_to(child, NODE_MARKER, node_version)
        respond_to(child, TOOL_NAME_MARKER, tool_name)
        if tool_version_marker:
            respond_to(child, tool_version_marker, tool_version)
        child.expect(pexpect.EOF, timeout=60)
    finally:
        child.close()


def test_install_npm():
    """Test install.sh creates npmw with correct configuration"""
    container_name = f"ntw-test-{os.getpid()}"
    _run_install(container_name, '22.0.0', 'npm', TOOL_VERSION_MARKER_NPM, '10.0.0')
    file_contents = _run_docker_and_copy_wrapper(container_name, 'npm')

    assert file_contents is not None
    assert '#!/bin/bash' in file_contents
    assert 'selectNode v22.0.0' in file_contents
    assert 'selectTool npm 10.0.0' in file_contents
    assert 'npm "$@"' in file_contents

def test_install_yarn():
    """Test install.sh creates yarnw with correct configuration"""
    container_name = f"ntw-test-{os.getpid()}"
    _run_install(container_name, '20.0.0', 'yarn', TOOL_VERSION_MARKER_YARN, '4.0.0')
    file_contents = _run_docker_and_copy_wrapper(container_name, 'yarn')

    assert file_contents is not None
    assert '#!/bin/bash' in file_contents
    assert 'selectNode v20.0.0' in file_contents
    assert 'selectTool yarn 4.0.0' in file_contents
    assert 'yarn "$@"' in file_contents


def test_install_node():
    """Test install.sh creates nodew with correct configuration"""
    container_name = f"ntw-test-{os.getpid()}"
    _run_install(container_name, '20.0.0', 'node')
    file_contents = _run_docker_and_copy_wrapper(container_name, 'node')

    assert file_contents is not None
    assert '#!/bin/bash' in file_contents
    assert 'selectNode v20.0.0' in file_contents
    # node wrapper should not have selectTool line
    assert 'selectTool' not in file_contents
    assert 'node "$@"' in file_contents
