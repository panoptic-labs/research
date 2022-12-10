# Panoptic Research

## Virtual Environment

We use a Python virtual environment to manage packages. Activate it with:

```shell
> ./activate.sh
```

## Installing Packages

Install new packages with:

```shell
panoptic-research/bin/pip install <pip package to install>
```

## Downloading Data

Download data by using the `DataHandler`:

```python
> from research import DataHandler
> dh = DataHandler()
> df = dh.download(pool_address="0x82c427adfdf2d245ec51d8046b41c4ee87f0d29c", all=True, force=False)
```
