import docker
import logging
import os
import signal
import sys
from environment_kernels import EnvironmentKernelSpecManager

logger = logging.getLogger(__name__)

class ContainerizedKernelRunner(object):

    def __init__(self, kernel_name, connection_file):
        self._kernel_name = kernel_name
        kernel_argv = EnvironmentKernelSpecManager().get_kernel_spec(self._kernel_name).argv
        self._kernel_command = ' '.join(kernel_argv).format(connection_file=connection_file)
        self._container = docker.from_env().containers.get('containerized_kernels')

    def _set_up_signal_handlers(self):
        for signum in (signal.SIGTERM, signal.SIGQUIT):
            signal.signal(signum, lambda *_: exit(1))
        signal.signal(signal.SIGINT, lambda *_: self._send_kill_signal_to_kernel(signal.SIGINT))

    def _send_kill_signal_to_kernel(self, signum):
        kill_kernel_command = f'''sh -c "kill -s {signum} $(ps --no-heading --width 1024 -eo pid,command | grep -P '(\d)+(\s)+{self._kernel_command}' | awk '{{print $1}}')"'''
        _, kill_kernel_output = self._container.exec_run(kill_kernel_command)
        logger.info(f'Tried sending signal {signum} to kernel started with {self._kernel_command}: ' + str(kill_kernel_output))

    def run(self):
        self._set_up_signal_handlers()
        self._container.start()
        logger.info(f'Running kernel: {self._kernel_command} from {os.getcwd()}')
        try:
            _, kernel_output = self._container.exec_run(self._kernel_command, environment=dict(os.environ), workdir=os.getcwd())
            logger.info(f'Kernel output: {str(kernel_output)}')
        finally:
            self._send_kill_signal_to_kernel(signal.SIGTERM)

if __name__ == '__main__':
    try:
        ContainerizedKernelRunner(kernel_name=sys.argv[1], connection_file=sys.argv[2]).run()
    except:
        logger.exception('Caught unhandled exception: ')
        raise