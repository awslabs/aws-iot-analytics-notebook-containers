## AWS IoT Analytics Notebook Containers

An extension for Jupyter notebooks that allows running notebooks insider a Docker container and converting them to executable Docker images.

## Features

* Special Jupyter kernels that execute cells inside a Docker container
* Simple wizard UI for converting the container to an executable Docker image
* Parameterized execution of notebooks with a variable replacement mechanism (read more in the **Notebook parameterization** section below)

## Jupyter Compatibility

The extension relies on certain configurations specific to Jupyter notebooks offered by [Amazon SageMaker service](https://docs.aws.amazon.com/sagemaker/latest/dg/nbi.html). In particular, it assumes that Docker is installed, relies on [Environment Kernels plugin](https://github.com/Cadair/jupyter_environment_kernels) and specific kernel name prefix to create matching containerized kernels. It also expects certain directories to be present (in order to mount them to the container) and puts the notebook output to a specific S3 location.

With that said, the core functionality of the extension should be compatible with most Jupyter installations.

## Installation

The extension is automatically installed in Jupyter notebooks provisioned via the AWS IoT Analytics Console.

To install the extension manually, run the `install.sh` script.

Run the following commands in a Jupyter Terminal to download and install the most recent version of the extension:

```
cd /tmp
aws s3 cp s3://iotanalytics-notebook-containers/iota_notebook_containers.zip /tmp
unzip iota_notebook_containers.zip
cd iota_notebook_containers
chmod u+x install.sh
./install.sh
```

## Notebook parameterization

The executable Docker images produced by this extension can accept input parameters. Those parameters are then inserted into notebooks via variable replacement.

Specifically, the image entry script (`iota_run_nb.py`) finds the first occurrence of each variables’ assignment in the notebook code cells and replaces the assigned value with the corresponding input value (if provided, otherwise it keeps the original assignment). It then runs the resulting notebook.

The input variables are read from a file inside the container located at `/opt/ml/input/data/iotanalytics/params`. That means you should either mount or copy the `params` file into the container prior to running it.

Below is an example of the input `params` file showing how to use variables of different types:

```JSON
{
   "Context": {
       "OutputUris": {
           "html": "s3://aws-iot-analytics-dataset-xxxxxxx/notebook/results/iotanalytics-xxxxxxx/output.html",
           "ipynb": "s3://aws-iot-analytics-dataset-xxxxxxx/notebook/results/iotanalytics-xxxxxxx/output.ipynb"
       }
   },
   "Variables": {
       "example_string_var": "hello world!",
       "example_numeric_var": 5
   }
}
```

## License

This library is licensed under the Apache 2.0 License.
