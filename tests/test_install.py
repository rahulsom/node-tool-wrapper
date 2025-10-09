import pytest
import pexpect
import os
import subprocess

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
    cwd = os.getcwd()
    child = pexpect.spawn(
        f'docker run --rm -it -v {cwd}:/workspace ntw-test bash',
        encoding='utf-8',
        timeout=60
    )
    child.expect('#')
    child.sendline('cd /workspace')
    child.expect('#')
    child.sendline('./npmw')
    child.expect('#', timeout=120)
    output = child.before
    assert 'npm@11.6.0' in output, f"Expected npm version 11.6.0, got: {output}"
    child.sendline('exit')
    child.close()

def test_install_npm():
    """Test install.sh creates npmw with correct configuration"""
    cwd = os.getcwd()
    container_name = f"ntw-test-{os.getpid()}"
    child = pexpect.spawn(
      f'docker run --name {container_name} -i -v {cwd}:/ntw -w /workspace ntw-test /ntw/install.sh',
      encoding='utf-8',
      timeout=60
    )
    try:
      child.expect(NODE_MARKER, timeout=30)
      child.sendline('22.0.0')
      child.expect(TOOL_NAME_MARKER, timeout=30)
      child.sendline('npm')
      child.expect(TOOL_VERSION_MARKER_NPM, timeout=30)
      child.sendline('10.0.0')
      child.expect(pexpect.EOF, timeout=60)
    finally:
      child.close()
    file_contents = _run_docker_and_copy_wrapper(container_name, 'npm')

    assert file_contents is not None
    assert '#!/bin/bash' in file_contents
    assert 'selectNode v22.0.0' in file_contents
    assert 'selectTool npm 10.0.0' in file_contents
    assert 'npm "$@"' in file_contents

def test_install_yarn():
    """Test install.sh creates yarnw with correct configuration"""
    cwd = os.getcwd()
    container_name = f"ntw-test-{os.getpid()}"
    child = pexpect.spawn(
      f'docker run --name {container_name} -i -v {cwd}:/ntw -w /workspace ntw-test /ntw/install.sh',
      encoding='utf-8',
      timeout=60
    )
    try:
      child.expect(NODE_MARKER, timeout=30)
      child.sendline('20.0.0')
      child.expect(TOOL_NAME_MARKER, timeout=30)
      child.sendline('yarn')
      child.expect(TOOL_VERSION_MARKER_YARN, timeout=30)
      child.sendline('4.0.0')
      child.expect(pexpect.EOF, timeout=60)
    finally:
      child.close()
    file_contents = _run_docker_and_copy_wrapper(container_name, 'yarn')

    assert file_contents is not None
    assert '#!/bin/bash' in file_contents
    assert 'selectNode v20.0.0' in file_contents
    assert 'selectTool yarn 4.0.0' in file_contents
    assert 'yarn "$@"' in file_contents

def test_install_node():
    """Test install.sh creates nodew with correct configuration"""
    cwd = os.getcwd()
    container_name = f"ntw-test-{os.getpid()}"
    child = pexpect.spawn(
      f'docker run --name {container_name} -i -v {cwd}:/ntw -w /workspace ntw-test /ntw/install.sh',
      encoding='utf-8',
      timeout=60
    )
    try:
      child.expect(NODE_MARKER, timeout=30)
      child.sendline('20.0.0')
      child.expect(TOOL_NAME_MARKER, timeout=30)
      child.sendline('node')
      child.expect(pexpect.EOF, timeout=60)
    finally:
      child.close()
    file_contents = _run_docker_and_copy_wrapper(container_name, 'node')

    assert file_contents is not None
    assert '#!/bin/bash' in file_contents
    assert 'selectNode v20.0.0' in file_contents
    # node wrapper should not have selectTool line
    assert 'selectTool' not in file_contents
    assert 'node "$@"' in file_contents
