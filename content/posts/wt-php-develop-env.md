---
title: PHP开发环境搭建
date: '2017-04-19T15:12:13+08:00'
category: PHP
summary: 根据自身情况直接装 mac 开发环境，或选用Valet或者Docker搭建
permalink: /2017/04/19/wt-php-develop-env/
---

## 开发环境搭建 {#开发环境搭建}

根据自身情况直接装 mac 开发环境，或选用Valet或者Docker搭建

* [直接装Mac开发环境,注意教程里的php版本比较旧](https://blog.frd.mn/install-nginx-php-fpm-mysql-and-phpmyadmin-on-os-x-mavericks-using-homebrew/) ->  [进阶教程](https://github.com/OzzyCzech/dotfiles/blob/master/how-to-install-mac.md)
* [Valet](#valet)
* [Docker](#docker)

<a id="more"></a>

### <a id="valet"></a>使用Valet {#使用Valet}

#### 安装 {#安装}
1. [Homebrew](http://brew.sh/index_zh-cn.html), run `ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"`
2. [Composer](https://getcomposer.org/), run `brew install composer`
3. [Xcode](https://itunes.apple.com/cn/app/xcode/id497799835?mt=12) Download from App Store
4. run `xcode-select --install`
5. run `brew install homebrew/php/php70`
6. run `brew install --HEAD homebrew/php/php70-memcached`
7. [Valet](https://laravel.com/docs/5.3/valet), run `composer global require laravel/valet`, add `~/.composer/vendor/bin` to $PATH, run `valet install`
8. (optional if using local db) `mariadb` run `brew install mariadb`

#### 配置 {#配置}
1. `mkdir ~/Sites && cd ~/Site && valet park`
2. `valet domain app` or `valet domain your-sub-domain.xmxdev.com`
2. `git clone https://github.com/wt1098078873/Blog_Hexo.git web`
3. `cd web`
4. `cp .env.example .env` 配置`.env`
5. `composer install --no-scripts` 安装PHP依赖库
6. `npm install` 安装前端编译组件

#### 运行 {#运行}

1. (optional if using local db) run `brew services start mariadb`
2. 打开 `http://web.dev` 来查看网站

### <a id="docker"></a>使用Docker {#使用Docker}

1. [Docker](https://docs.docker.com/docker-for-mac/)
2. [LaraDock](https://github.com/LaraDock/laradock)
3. 参考Valet方式配置&运行

## 相关资料 {#相关资料}

* [Homestead](http://laravel.com/docs/5.1/homestead)
* [Laravel Tutorial](http://laravel.com/docs/5.1/quickstart-intermediate)
* [Fractal](https://github.com/spatie/laravel-fractal)
* [Packagist](https://packagist.org/)
* [Setup a Mac Dev Machine From Scratch](https://laracasts.com/series/setup-a-mac-dev-machine-from-scratch)
