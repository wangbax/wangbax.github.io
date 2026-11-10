---
title: Gson使用时toJson报IllegalArgumentException
date: '2017-04-19T14:31:44+08:00'
updated: '2017-06-07T17:05:42+08:00'
category: Android
summary: 使用Gson过程中，在调用其 Gson.toJson(Object src) 时，一直报 java.lang.IllegalArgumentException ，异常代码如下：
permalink: /2017/04/19/wt-android-gson-tojson/
---

### 简介 {#简介}

使用Gson过程中，在调用其`Gson.toJson(Object src)`时，一直报
`java.lang.IllegalArgumentException`，异常代码如下：

<a id="more"></a>

```java
java.lang.IllegalArgumentException: Infinity is not a valid double value as per JSON specification. To override this behavior, use GsonBuilder.serializeSpecialFloatingPointValues() method.

    at com.google.gson.Gson.checkValidFloatingPoint(Gson.java:324)
    at com.google.gson.Gson$3.write(Gson.java:316)
    at com.google.gson.Gson$3.write(Gson.java:302)
    at com.google.gson.internal.bind.TypeAdapterRuntimeTypeWrapper.write(TypeAdapterRuntimeTypeWrapper.java:69)
    at com.google.gson.internal.bind.ReflectiveTypeAdapterFactory$1.write(ReflectiveTypeAdapterFactory.java:125)
    at com.google.gson.internal.bind.ReflectiveTypeAdapterFactory$Adapter.write(ReflectiveTypeAdapterFactory.java:243)
    at com.google.gson.Gson.toJson(Gson.java:669)
    at com.google.gson.Gson.toJson(Gson.java:648)
    at com.google.gson.Gson.toJson(Gson.java:603)
```

查看代码得知，是由于double的值为NaN导致，实际上Json按照规范是不支持特殊的double值（NaN，Infinity，-Infinity）的。

但是坑来了，一般来说，并不会为double初始化为NaN，都是0d的。就猜测是是不是后来被设置的，在项目中，由于使用的网络数据，会调用到Json的解析，手动解析的话，为保证字段的不存在，使用的是JsonObject的`optDouble(String name)`方法，这个方法代码如下：

```applescript
/**
* Returns the value mapped by {@code name} if it exists and is a double or
* can be coerced to a double, or {@code NaN} otherwise.
*/
public double optDouble(String name) {
    return optDouble(name, Double.NaN);
}
```
![懵逼](/images/2017/20170419144912.jpeg)

好吧，把默认值手动设置0。 FIX.

### 鸣谢 {#鸣谢}

[Gson Builder — 特殊类型 Floats & Doubles](http://www.jianshu.com/p/83eb1b2bc119)
