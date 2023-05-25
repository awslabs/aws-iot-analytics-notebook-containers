from setuptools import setup, find_packages

setup(
    name="iota_notebook_containers",
    version="1.0",
    author="Amazon Web Services",
    packages=find_packages(where=".", exclude=("test",)),
    install_requires=[
        # we don't specify a version because we want to use whichever versions
        # SageMaker pre-installs
        "boto3",
        "docker==3.3.0",
        "environment-kernels==1.1.1",
        "hurry.filesize==0.9",
        "jupyter==1.0.0",
        "tornado==6.3.2",
    ],
    tests_require = [
        "moto",
        "asttokens==1.1.10",
        "freezegun==0.3.10",
        "selenium==3.12.0",
    ],
    include_package_data=True,
    description="Containerize Jupyter notebook and upload to AWS ECR",
    root_script_source_version="python3.4",
    default_python="python3.4",
)
