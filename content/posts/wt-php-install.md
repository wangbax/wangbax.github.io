---
title: PHP安装时403问题
date: '2017-04-14T18:15:07+08:00'
updated: '2017-06-08T11:03:45+08:00'
category: PHP
summary: 在PHP安装和配置过程中，遇到一个坑，当配置nginx.conf时，项目路径 root 设置为非Nginx默认路径 /usr/local/var/www ,比如 /Users/wt/Documents/workspace_php/Test 时，会一直报403 Forbidden.
permalink: /2017/04/14/wt-php-install/
---

### 简介 {#简介}

在PHP安装和配置过程中，遇到一个坑，当配置nginx.conf时，项目路径**root**设置为非Nginx默认路径`/usr/local/var/www`,比如`/Users/wt/Documents/workspace_php/Test`时，会一直报403 Forbidden.

<a id="more"></a>

### 解决方案： {#解决方案：}

1. 检查**nginx.conf**设置是否正确，并确认对应路径是否有设置的启动文件`index.html index.php`等
2. 通过 ` whoami `获取当前自己用户，` id -g -n $whoami  `获取当前自己的用户组
3. 设置**nginx.conf**中` #user nobody `为 ` user [用户] [用户组] `

### 鸣谢 {#鸣谢}

[Mac 下 Nginx、PHP、MySQL 和 PHP-fpm 的安装和配置](https://segmentfault.com/a/1190000005090828)
[getgrnam(“user”) failed in /etc/nginx/nginx.conf](https://serverfault.com/questions/742482/getgrnamuser-failed-in-etc-nginx-nginx-conf)
