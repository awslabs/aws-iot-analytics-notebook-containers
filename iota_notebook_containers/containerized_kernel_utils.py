from iota_notebook_containers.constants import CONTAINERIZED_PREFIX

def remove_containerized_prefix(containerized_kernel_name):
    if containerized_kernel_name.lower().startswith(CONTAINERIZED_PREFIX):
        return containerized_kernel_name[len(CONTAINERIZED_PREFIX):]
    else:
        return containerized_kernel_name