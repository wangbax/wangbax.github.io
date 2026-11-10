---
title: 关于AndroidStudio2.3 SDKManagerGUI隐藏问题
date: '2017-03-17T10:45:49+08:00'
updated: '2017-06-08T11:03:23+08:00'
category: Android Studio
summary: 更新了AndroidStudio2.3正式版之后，之前可以在Preferences - Android SDK中的 Launch Standalone SDK Manager 按钮被隐藏了。
permalink: /2017/03/17/wt-android-studio-show-sdkmanager/
---

## 简介 {#简介}

更新了AndroidStudio2.3正式版之后，之前可以在Preferences - Android SDK中的 **Launch Standalone SDK Manager** 按钮被隐藏了。

<a id="more"></a>

## 方案 {#方案}

Google之后，找到[这个](http://stackoverflow.com/questions/41407396/is-gui-for-android-sdk-manager-gone)，发现可以通过命令行调起GUI。

命令如下:

```armasm
sdkpath/tools/android sdk
```

如果在自己的环境变量中已把SDK的tools也添加到了Path中，则只需调用:

```armasm
android sdk
```

当然也可以全部使用命令行进行操作，[官方链接](https://developer.android.com/studio/command-line/sdkmanager.html#usage)，具体步骤如下:

1. 首先需要把sdkpath/tools/bin添加到环境变量的Path中
2. 调用 **sdkmanager --help** 即可查看所有的命令

------

更新于： 2017-03-22 11:25:33

------

以上仅针对SDK版本低于25.3.0，在之上，[android命令已被弃用](https://developer.android.com/studio/releases/sdk-tools.html?hl=zh-cn)，再调用这个，会报:

```routeros
The android command is no longer available.
For manual SDK and AVD management, please use Android Studio.
For command-line tools, use tools/bin/sdkmanager and tools/bin/avdmanager
```

So...只能使用**命令行**或者通过**AndroidStudio的更新提示框**更新。┑(￣Д ￣)┍
