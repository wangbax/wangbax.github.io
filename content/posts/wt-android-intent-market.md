---
title: Android 系统评分的调用及自定义
date: '2016-08-15T14:49:27+08:00'
updated: '2016-11-17T18:30:50+08:00'
category: Android
summary: 开发中遇到了设置自己应用某页面为系统商店页面。
permalink: /2016/08/15/wt-android-intent-market/
---

## 简介 {#简介}

开发中遇到了设置自己应用某页面为系统商店页面。

<a id="more"></a>

## 调用 {#调用}

### <a id="markdown-intent-market"></a>仅调用系统应用商店 {#仅调用系统应用商店}
```java
/**
 * 调用系统应用商店
 *
 * @return true: 调用成功 false: 调用失败
 */
public static boolean intent2AppMarket(Context context) {
    try {
        Intent startintent = new Intent("android.intent.action.MAIN");
        startintent.addCategory("android.intent.category.APP_MARKET");
        startintent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        context.startActivity(startintent);
        return true;
    } catch (Exception e) {
        Log.e("AppMarketAct", "e:" + e);
        return false;
    }
}
```

### <a id="markdown-intent-market-detail"></a>调用至系统应用商店对于详情页面 {#调用至系统应用商店对于详情页面}
```java
/**
 * 调用系统应用商店
 *
 * @return true: 调用成功 false: 调用失败
 */
public static boolean intent2AppMarketDetail(Context context) {
    try {
        Uri uri = Uri.parse("market://details?id=" + context.getPackageName());
        Intent intent = new Intent(Intent.ACTION_VIEW, uri);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        context.startActivity(intent);
        return true;
    } catch (Exception e) {
        Log.e("AppMarketAct", "e:" + e);
        return false;
    }
}
```

## 声明为应用商店 {#声明为应用商店}

### 通过启动类Category声明(对应[仅调用系统应用商店](#markdown-intent-market)） {#通过启动类Category声明-对应仅调用系统应用商店）}
在Manifest的启动Activity的intent-filter中添加
`<category android:name="android.intent.category.APP_MARKET" />`即可

```xml
<activity
    android:name=".BeginActivity"
    android:label="@string/app_name"
    android:theme="@style/AppTheme.NoActionBar">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />

        <category android:name="android.intent.category.LAUNCHER" />
        <category android:name="android.intent.category.APP_MARKET" />
        <category android:name="android.intent.category.DEFAULT" />
    </intent-filter>
</activity>
```

### 通过声明Scheme跳转具体详情页(对于[调用至系统应用商店对于详情页面](#markdown-intent-market-detail)) {#通过声明Scheme跳转具体详情页-对于调用至系统应用商店对于详情页面}

#### 实现原理 {#实现原理}
* 对于Android平台而言，URI是由scheme,host,port,path,queryString组成，格式为
`
scheme://host:port/path?qureyParameter=queryString
`
* 对于Android平台而言，`market://details?id=pkName`为默认的约定俗成的URI

#### 实现步骤 {#实现步骤}

* 在Manifest中为此中转类设置对应intent-filter并设置exported为true

    ```xml
    <activity
        android:name=".appmarket.LinkProxyActivity"
        android:exported="true"
        android:theme="@style/AppTheme.NoActionBar">
        <intent-filter>
            <action android:name="android.intent.action.VIEW" />

            <category android:name="android.intent.category.DEFAULT" />
            <category android:name="android.intent.category.BROWSABLE" />

            <data android:scheme="market" />
        </intent-filter>
    </activity>
    ```

* 在中转类中获取对应的id进行跳转或其他处理

    ```java
    public class ProxyActivity extends Activity{

        private static final String TAG = "ProxyActivity";

        @Override
        protected void onCreate(Bundle savedInstanceState) {
            super.onCreate(savedInstanceState);

            Intent intent = getIntent();
            Log.i(TAG, "scheme: "+intent.getScheme());
            Uri uri = intent.getData();
            Log.i(TAG, "scheme: "+uri.getScheme());
            Log.i(TAG, "host: "+uri.getHost());
            Log.i(TAG, "path: "+uri.getPath());
            Log.i(TAG, "query: "+uri.getQuery());
            Log.i(TAG, "query id: "+uri.getQueryParameter("id"));

            //FIXME 跳转或其他相关操作，并关闭此中转页面

        }
    }
    ```

* Log打印结果如下:

    ```java
    I/ProxyActivity: scheme: market
    I/ProxyActivity: scheme: market
    I/ProxyActivity: host: details
    I/ProxyActivity: path:
    I/ProxyActivity: query: id=com.jianshu.haruki
    I/ProxyActivity: query id: com.jianshu.haruki
    ```
