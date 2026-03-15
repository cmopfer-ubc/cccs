# Camden's Computation Climate Scripts

This is a simple Python package with the `lib` subdirectory containing all the scripts it draws from. These act as sub-modules of the package. For example, you can use `from cccs import plotting` in a Python script to gain access to the `plotting.globalMap` function.

### Installation
For the foreseeable future, this code base will be frequently modified, and new sub-modules will be occasionally added. Because of this, it is recommended to clone the [GitHub repository](https://github.com/cmopfer-ubc/cccs), and install it in a way that will update when the source (the GitHub repository) is updated.

In general, this is done with `pip install -e /path/to/repo`. If you are using a Conda environment, then you must first activate your environment, run `conda install pip`, and then use pip as above. If you are using a regular virtual environment, then you can just run `pip install -e /path/to/repo` immediately, assuming your environment is active.

If you install in one of these ways, you can use `pip list` (while your environment is active) to see the version of this package. The versioning follows a YYYY.MM.DD format, so this can be a good way to check if it's time to do a `git fetch`, `git pull` and grab the most recent source.

### Contributing
If you plan to modify and commit code in this repository, then please run `git config core.hooksPath .githooks` so that your commits will automatically bump the version number of the package. Otherwise, happy coding!