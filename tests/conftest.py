import os
import subprocess

import pexpect


def respond_to(child, marker, response):
    child.expect(marker, timeout=30)
    child.sendline(response)


def spawn_container(container_name=None, mount=None, workdir='/workspace', command='bash', extra_args='-it'):
    """Spawn an ntw-test container. `mount` is a (host_path, container_path) pair.

    If `container_name` is None, the container is anonymous and removed on exit (--rm).
    """
    host_path, container_path = mount or (os.getcwd(), '/ntw')
    name_or_rm = f'--name {container_name}' if container_name else '--rm'
    return pexpect.spawn(
        f'docker run {name_or_rm} {extra_args} -v {host_path}:{container_path} '
        f'-w {workdir} ntw-test {command}',
        encoding='utf-8',
        timeout=60
    )


def cleanup_container(child, container_name=None, exit_cmd='exit'):
    if exit_cmd:
        child.sendline(exit_cmd)
    child.close()
    if container_name:
        subprocess.run(['docker', 'rm', '-f', container_name], capture_output=True, check=False)
