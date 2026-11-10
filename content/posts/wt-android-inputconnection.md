---
title: Android重写InputConnection之后，某些设备Crash
date: '2017-04-24T11:34:52+08:00'
updated: '2017-06-07T17:16:27+08:00'
category: Android
summary: 开发过程中，查看Bugly时，发现在部分机型（酷派，说的就是你），只要点击了自定义的 InputConnection 的 WebView ，程序就会直接Crash，Bugly中崩溃日志如下：
permalink: /2017/04/24/wt-android-inputconnection/
---

### 简介 {#简介}

开发过程中，查看Bugly时，发现在部分机型（酷派，说的就是你），只要点击了自定义的`InputConnection`的`WebView`，程序就会直接Crash，Bugly中崩溃日志如下：

```java
java.lang.AbstractMethodError
abstract method not implemented
解析原始
1 com.play.taptap.richeditor.TapRichEditor$e.performYLPrivateCommand(TapRichEditor.java)
2 com.android.internal.view.IInputConnectionWrapper.executeMessage(IInputConnectionWrapper.java:444)
3 com.android.internal.view.IInputConnectionWrapper$MyHandler.handleMessage(IInputConnectionWrapper.java:81)
4 android.os.Handler.dispatchMessage(Handler.java:99)
5 android.os.Looper.loop(Looper.java:153)
6 android.app.ActivityThread.main(ActivityThread.java:5305)
7 java.lang.reflect.Method.invokeNative(Native Method)
8 java.lang.reflect.Method.invoke(Method.java:511)
9 com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:848)
10 com.android.internal.os.ZygoteInit.main(ZygoteInit.java:615)
11 dalvik.system.NativeStart.main(Native Method)
```
故名思议，得知是由于没有实现接口方法`performYLPrivateCommand`，但是实际上Android标准的`InputConnection`接口并没有这个方法。经Google，在[你要知道的N个Android适配问题](https://my.oschina.net/bugly/blog/536086)中找到了相似问题。

<a id="more"></a>

### 分析 {#分析}

既然找到了原因，是由于某些坑爹的厂商（酷派：怪我咯~）在`InputConnection`接口中新增了一个`performYLPrivateCommand `方法，那么，对于解决，只要实现这个方法就好。对于Android，只要子类定义了这个方法，那么就算是实现了，加不加Override注解不影响源码的解析。在`InputConnection`中添加如下方法：

```java
public boolean performYLPrivateCommand(String action, Bundle data) {
    return true;
}
```

经测试，失败。┑(￣Д ￣)┍

通过[Jeb](https://www.pnfsoftware.com/)反编译自己代码，并没有找到任何与`performYLPrivateCommand `相关代码，此时想到，应该是项目构建时，会把未使用的无用代码移除，不会打包进入Apk中，想到的解决方案是，自定义一个接口封装`performYLPrivateCommand`方法，同时实现`InputConnection`接口和自定的接口。代码如下：

```java
public interface IExtraInputConnection {
    boolean performYLPrivateCommand(String action, Bundle data);
}
```

```java
class TapInputConnection implements InputConnection, IExtraInputConnection {
    // ... 省略InputConnection相关实现
    @Override
    public boolean performYLPrivateCommand(String action, Bundle data) {
        return true;
    }
}
```
打包，测试，还是失败。

反编译，
![被混淆](/images/2017/20170424121603.png)

实现已经存在，只是被混淆了。此时应该防止被混淆，否则会找不到这个方法，在混淆文件中添加如下代码：

```java
-keep interface com.wangbax.IExtraInputConnection {
    public protected <methods>;
}
```

经测试，成功。

![结果](/images/2017/20170424121353.png)

### 总结 {#总结}

1. 自定义接口封装`performYLPrivateCommand`
2. 实现`InputConnection`接口的同时实现自定义的接口
3. 使自定义接口不被混淆

### 代码 {#代码}

```java
public interface IExtraInputConnection {
    boolean performYLPrivateCommand(String action, Bundle data);
}
```

```java
class TapInputConnection implements InputConnection, IExtraInputConnection {
    // ... 省略InputConnection相关实现
    @Override
    public boolean performYLPrivateCommand(String action, Bundle data) {
        return true;
    }
}
```

```java
-keep interface com.wangbax.IExtraInputConnection {
    public protected <methods>;
}
```

### 鸣谢 {#鸣谢}

* [你要知道的N个Android适配问题](https://my.oschina.net/bugly/blog/536086)
* [Bugly](https://bugly.qq.com)
* [Jeb](https://www.pnfsoftware.com/)
