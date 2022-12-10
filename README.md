# Panoptic Research

## Virtual Environment

We use a Python virtual environment to manage packages. Activate it with:

```shell
> ./activate.sh
```

Make sure that the environment `panoptic-research` is used by checking the path to the Python executable being used:

```shell
> which python
<your base path - varies between computers>/research/panoptic-research/bin/python
```

We see the path makes sense - it is the `panoptic-research/bin/python` file.

This also means that you can run any python file with:

```shell
> python <filename>.py
```

Then install all existing Python packages with:

```shell
> panoptic-research/bin/pip install -r requirements.txt
```

## Installing New Packages

Install new packages with:

```shell
panoptic-research/bin/pip install <pip package to install>
```

### Update Python Requirements

After installing new packages - and assuming you want to keep them - please update the requirements file:

```shell
> panoptic-research/bin/pip freeze > requirements.txt
```

and push as part of your PR.

## Downloading Data

Download data by using the `DataHandler`:

```python
> from research import DataHandler
> dh = DataHandler()
> df = dh.download(pool_address="0x82c427adfdf2d245ec51d8046b41c4ee87f0d29c", all=True, force=False)
```

## Run Code

To run code, e.g., to sync data:

```shell
> python syncData.py
```
