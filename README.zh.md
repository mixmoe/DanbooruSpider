# DanbooruSpider

**一个基于Python异步的高效爬虫，可以作用于多个使用[Danbooru](https://github.com/danbooru/danbooru)作为后端的图片网站**

[![GitHub license](https://img.shields.io/github/license/mnixry/DanbooruSpider)](https://github.com/mnixry/DanbooruSpider/blob/master/LICENSE) [![GitHub issues](https://img.shields.io/github/issues/mnixry/DanbooruSpider)](https://github.com/mnixry/DanbooruSpider/issues) [![GitHub stars](https://img.shields.io/github/stars/mnixry/DanbooruSpider)](https://github.com/mnixry/DanbooruSpider/stargazers) [![GitHub forks](https://img.shields.io/github/forks/mnixry/DanbooruSpider)](https://github.com/mnixry/DanbooruSpider/network) ![Python Version](https://img.shields.io/badge/Python-3.8%2B-brightgreen)

## 优势

### 通用

- 目前支持以下多个站点
    - [yande.re](http://yande.re/)
    - [konachan.com](https://konachan.com/)
    - [danbooru.donmai.us](https://danbooru.donmai.us/)
    - 更多支持正在开发中
- 本程序从设计之初就考虑的接入其他下载接口的情况，只需少量代码即可添加新的站点接入

### 高效

本程序采用Python新兴的异步编程特性，能够将资源利用发挥到极致

- HTTP请求完全使用[httpx](https://github.com/encode/httpx)作为异步高效地驱动程序运行
- 在作者本人的Visual Studio Codespace上：
    - 以默认配置运行平均下载速度高达20MiB/s
    - 内存占用小于等于200MiB

### 可靠

本项目从创立起就采用[pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance)和[mypy](https://github.com/python/mypy)进行代码类型和代码格式检查，同时采用[pydantic](https://github.com/samuelcolvin/pydantic)作为读写模型来进行动态的类型验证

## 部署

本项目的部署和使用十分简单

### 准备工作

- `Python3.8`或更高版本

- 齐全的Python标准库
- 将本项目代码保存到本地

### 安装依赖

打开本项目文件夹，命令行执行

```shell
pip insall -r requirements.txt
```

即可

### 运行

```shell
python3 main.py
```

## 配置

详情请见[配置文件](./data/config.default.yml)中的注释