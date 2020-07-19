# DanbooruSpider

**An efficient crawler based on Python asynchronous, can act on multiple image websites that use [Danbooru](https://github.com/danbooru/danbooru) as the backend**

[![GitHub license](https://img.shields.io/github/license/mnixry/DanbooruSpider)](https://github.com/mnixry/DanbooruSpider/blob/master/LICENSE) [![GitHub issues ](https://img.shields.io/github/issues/mnixry/DanbooruSpider)](https://github.com/mnixry/DanbooruSpider/issues) [![GitHub stars](https://img.shields.io/github/stars/mnixry/DanbooruSpider)](https://github.com/mnixry/DanbooruSpider/stargazers) [![GitHub forks](https://img.shields.io/github/forks/mnixry/DanbooruSpider)](https://github.com/mnixry/DanbooruSpider/network) ![Python Version](https://img.shields.io/badge/Python-3.8%2B-brightgreen)

## Advantages

### General

- Currently supports the following multiple sites
    - [yande.re](http://yande.re/)
    - [konachan.com](https://konachan.com/)
    - [danbooru.donmai.us](https://danbooru.donmai.us/)
    - More support is under development
- This program considers access to other download interfaces from the beginning of the design, and only a small amount of code can add new site access

### Efficient

This program uses Python's asynchronous programming features, which can maximize resource utilization

- HTTP requests completely use [httpx](https://github.com/encode/httpx) as an asynchronous to efficiently drive the program to run
- On the author's own Visual Studio Codespace:
    - Running average download speed up to 20MiB/s in default configuration
    - The memory footprint is less than or equal to 200MiB

### Reliable

Since the project was founded, [pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) and [mypy](https://github.com/python/mypy) have been used for code type and code format checking, and [pydantic](https://github.com/samuelcolvin/pydantic) has been used as a model for dynamic type verification.

## Deployment

The deployment and use of this project is very simple:

### Ready to work

- `Python3.8` or higher

- Complete Python standard library
- Save the project code locally

### Installation dependencies

Open the project folder and execute the command line

```shell
pip insall -r requirements.txt
```

### Run

```shell
python3 main.py
```

## Configuration

For details, please see the comments in [Configuration File](./data/config.default.yml)