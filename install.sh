{
    pip install --upgrade . &&
    jupyter serverextension enable --py iota_notebook_containers --sys-prefix &&
    jupyter nbextension install --py iota_notebook_containers --sys-prefix &&
    jupyter nbextension enable --py iota_notebook_containers --sys-prefix &&
    python -m iota_notebook_containers.install_kernels &&
    python -m iota_notebook_containers.extension_last_modified_manager &&
    echo "Installation successful! You will need to refresh this tab if you want to continue using the terminal." &&
    sudo pkill -f jupyter 
} || {
    echo "The containerization extension installation failed."
# We don't want the installation script to exit with an error code because failed lifecycle configurations make the notebook unrecoverable
} || true