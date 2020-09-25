# Summapy

This project was created for a little experiment regarding automatic text summarization.

It's heavily inspired by Reddit's [u/autotldr](https://www.reddit.com/user/autotldr/) and [SMMRY](https://smmry.com/about).

You can read about it [here](http://www.restless-bytes.com/posts/automatic-text-summarization/) if you're interested.

**Prerequisits**

* Python 3.7+
* [poetry](https://python-poetry.org/docs/) 

**Usage**

1. Make sure that you have all dependencies installed by running:

```
$ poetry install
```

2. You can then either run the script on specific articles or on all 3 articles from the blog post mentioned above:

```
# run on specific article
$ poetry run python main.py articles/taiwan_passport_change.txt

# run on all articles
$ poetry run python main.py
```
