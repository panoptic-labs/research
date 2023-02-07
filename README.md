<p align="center">
  <img src="banner-research.png" width="1000" title="Panoptic Banner"></img>
</p>

# Panoptic Research

Welcome to Panoptic Research's online GitHub repository. Here you will find results of our studies on DeFi, on-chain options, and other related topics. We hope that these results will be useful to other researchers, developers, and operators in the field and contribute to the advancement of knowledge in DeFi.

If you have any questions or comments about the data or analysis presented here, please feel free to open an issue or contact us directly. Thank you for visiting and we hope you find our work insightful!

## Research Bites & Notebooks

We run our Research Bites series and disseminate our findings via notebooks. You can get the notebooks from this repository.

They are located at: `_research_bites/<date>/ResearchBites-<date>-<title>.ipynb`.

We provide tutorials as well to ensure the fullest participation from the community. Please locate those under `_research_bites/tutorials/*.ipynb`.

## More on Panoptic

Panoptic is a governance-minimized options trading protocol. It enables the permissionless trading of perpetual options on top of any asset pool in the [Uniswap v3 ecosystem](https://uniswap.org/).

The Panoptic protocol is noncustodial, has no counterparty risk, offers instantaneous settlement, and is designed to remain fully-collateralized at all time.

- [Panoptic's Website](https://www.panoptic.xyz) (includes link to documentation)
- [Codebase on GitHub](https://github.com/panoptic-labs/Panoptic)
- [Twitter](https://twitter.com/Panoptic_xyz)
- [LinkedIn](https://www.linkedin.com/company/panoptic-xyz/)
- [Discord](https://discord.gg/7fE8SN9pRT)
- [Blog](https://www.panoptic.xyz/blog)

### Material on Panoptic

Panoptic has been presented at conferences and was created before the Summer of 2021 with the first blog post/article coming out mid-summer 2021:

- [Panoptic @ ETH Denver 2022](https://www.youtube.com/watch?v=mtd4JphPcuA)
- [Panoptic @ DeFi Guild](https://www.youtube.com/watch?v=vlPIFYfG0FU)
- [Panoptic's Genesis: Blog Series](https://lambert-guillaume.medium.com/)
- [Panoptic's Whitepaper v1](https://arxiv.org/abs/2204.14232)

After introducing Panoptic and providing context, it is time to provide Panoptic's take-home test for evaluating Solidity engineers:

# Panoptic Research Setup

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

## Installing Fonts

Install the HelveticaNeue fonts with:

```shell
panoptic-research/bin/python3.10 installFonts.py
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

# Author

**Axicon Labs Inc.**

* [website](https://www.panoptic.xyz/)
* [twitter](https://twitter.com/Panoptic_xyz)
* [discord](https://discord.com/invite/7fE8SN9pRT)
* [blog](https://blog.panoptic.xyz/)

### License

Created by Axicon Labs Inc.

This repository "https://github.com/panoptic-labs/research" (the "Repo") is licensed under the MIT license.
You are free to use, build upon, and distribute this Repo.
