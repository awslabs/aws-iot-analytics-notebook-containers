import docker
import json
import logging
import os
import sys

from . import constants
from environment_kernels import EnvironmentKernelSpecManager
from io import BytesIO
from IPython.utils.tempdir import TemporaryDirectory

logger = logging.getLogger(__name__)

class KernelContainerCreator(object):
    def __init__(self, name):
        self._docker_client = docker.from_env()
        self._name = name

    def recreate(self):
        self._remove()
        self._create()

    def _create(self):
        dockerfile = '''
        FROM amazonlinux:latest
        RUN yum install -y procps
        '''
        mounted_volumes = {
            '/home/ec2-user/anaconda3/': {
                'bind': '/home/ec2-user/anaconda3/',
                'mode': 'rw'
            },
            '/home/ec2-user/.local/share/jupyter/runtime/': {
                'bind': '/home/ec2-user/.local/share/jupyter/runtime/',
                'mode': 'rw'
            },
            '/home/ec2-user/SageMaker/': {
                'bind': '/home/ec2-user/SageMaker/',
                'mode': 'rw'
            },
            '/home/ec2-user/.aws/': {
                'bind': '/home/ec2-user/.aws/',
                'mode': 'rw'
            }
        }
        self._docker_client.images.build(fileobj=BytesIO(dockerfile.encode('utf-8')), tag=self._name)
        logger.info('Built kernel container image: ' + self._name)
        self._docker_client.containers.create(self._name, stdin_open=True, detach=True, name=self._name, volumes=mounted_volumes, network_mode='host')
        logger.info('Created kernel container: ' + self._name)

    def _remove(self):
        try:
            containerized_kernels = self._docker_client.containers.get(self._name)
        except docker.errors.NotFound:
            return
        containerized_kernels.remove(force=True, v=True)

class ContainerizedKernelInstaller(object):
    def __init__(self):
        self._kernel_spec_manager = EnvironmentKernelSpecManager()

    def install(self):
        with TemporaryDirectory() as td:
            allow_all_rx = 0o755
            os.chmod(td, allow_all_rx)
            for kernel_name in self._kernel_spec_manager.find_kernel_specs():
                if not self._should_containerize_kernel(kernel_name):
                    continue
                kernel_display_name = 'Containerized ' + kernel_name
                with open(os.path.join(td, 'kernel.json'), 'w') as f:
                    kernel_json = self._get_kernel_json(kernel_name, kernel_display_name)
                    logger.debug("Installing kernel with definition: " + str(kernel_json))
                    json.dump(kernel_json, f, sort_keys=True)
                safe_name = kernel_display_name.replace(' ', '_')
                self._kernel_spec_manager.install_kernel_spec(td, safe_name, prefix=sys.prefix, replace=True)
                logger.info('Installed kernel: ' + safe_name)

    def _get_kernel_json(self, original_kernel_name, kernel_display_name):
        env_var = self._kernel_spec_manager.get_kernel_spec(original_kernel_name).env
        env_var.pop('LD_PRELOAD', None)
        return {
            'argv':[
                sys.executable,
                '-m',
                'iota_notebook_containers.run',
                original_kernel_name,
                '{connection_file}'
            ],
            'display_name': kernel_display_name,
            'language': 'python',
            'env': env_var
        }

    def _should_containerize_kernel(self, kernel_name):
        return kernel_name.startswith('conda_') and kernel_name not in ['conda_jupytersystemenv', 'conda_anaconda3']

if __name__ == '__main__':
    try:
        KernelContainerCreator(constants.CONTAINER_NAME).recreate()
        ContainerizedKernelInstaller().install()
    except:
        logger.exception("Caught unhandled exception while installing kernels.")
        raise
    logger.info('Installed containerized kernels')
