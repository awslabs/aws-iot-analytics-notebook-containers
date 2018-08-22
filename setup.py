from setuptools import setup, find_packages

setup(
    name="iota_notebook_containers",
    version="1.0",
    url="",
    author="Amazon Web Services",
    packages=find_packages(where=".", exclude=("test",)),
    install_requires=[
        "boto3==1.7.15",
        "docker==3.3.0",
        "environment-kernels==1.1.1",
        "jupyter==1",
        "tornado==5.0.2"
    ],
    tests_require = [
        "freezegun==0.3.10",
        "moto==1.3.3",
        "selenium==3.12.0",
    ],
    include_package_data=True,
    description="Output Jupyter notebook to docker and upload to ECR",
    options={
        # make sure the right shebang is set for the scripts - use the
        # environment default Python
        'build_scripts': {
            'executable': '/apollo/sbin/envroot "$ENVROOT/bin/python"',
        },
    },
    root_script_source_version="python3.4",
    default_python="python3.4",
    test_command='brazilpython_pytest',
    doc_command='amazon_doc_utils_build_sphinx'
)
