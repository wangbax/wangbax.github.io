---
title: Android 收藏方法
date: '2016-08-08T11:49:29+08:00'
updated: '2016-08-15T16:31:27+08:00'
category: Android
summary: 保存平时收集到的常用方法，以便以后调用。
permalink: /2016/08/08/wt-android-methods/
---

## 简介 {#简介}

保存平时收集到的常用方法，以便以后调用。

## 目录 {#目录}

* [获取手机验证码](#markdown-smsobserver)
* [图片旋转](#markdown-rotateBitmap)
* [获取设备所有的存储路径](#markdown-getStoragePaths)
* [获取应用进程信息](#markdown-getRunningAppProcesses)
* [获取已安装软件的大小](#markdown-queryPacakgeSize)
* [生成带倒影的Bitmap图像](#markdown-createReflectedImage)
* [ImageLoader加载本地图片工具类](#markdown-imageloaderlocal)

<a id="more"></a>

### <a id="markdown-smsobserver"></a>获取手机验证码 {#获取手机验证码}
```java
SmsObservermSObserver = new SmsObserver(mContext, new Handler());
mContext.getContentResolver().registerContentObserver(SMS_INBOX, true, mSObserver);

private Uri SMS_INBOX = Uri.parse("content://sms/");
private class SmsObserver extends ContentObserver {

private Cursor cursor = null;

public SmsObserver(Context context, Handler handler) {
    super(handler);
}

@Override
public void onChange(boolean selfChange) {
    super.onChange(selfChange);
    getSmsFromPhone();
}

private void getSmsFromPhone() {
    ContentResolver cr = mContext.getContentResolver();
    String[] projection = new String[] { "body" };
    // 10655198881
    String where = " address = '10655198881' AND date >  " + (System.currentTimeMillis() - 1 * 60 * 1000);
    Cursor cur = cr.query(SMS_INBOX, projection, where, null, "date desc");
    if (null == cur)
        return;
    if (cur.moveToNext()) {
        String body = cur.getString(cur.getColumnIndex("body"));
        Pattern pattern = Pattern.compile("[0-9]{6}");
        Matcher matcher = pattern.matcher(body);
        if (matcher.find()) {
            String res = matcher.group().substring(1, 7);
            //设置code
            mCodeEdit.setText(res);
            return;
            }
        }
    }
}
```


#### <a id="markdown-rotateBitmap"></a>图片旋转 {#图片旋转}
```java
public static Bitmap rotateBitmap(int degree, Bitmap bitmap) {
    Matrix matrix = new Matrix();
    matrix.postRotate(degree);

    return Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), matrix, true);
}
```



### <a id="markdown-getStoragePaths"></a>获取设备所有的存储路径 {#获取设备所有的存储路径}
有2种方法，方法1为调用系统方法getVolumePaths获取，方法2为自己解析/proc/mounts文件下的路径

#### 方法1 {#方法1}
```java
public static String[] getVolumePaths(Context context) {
    try {
        StorageManager sm = (StorageManager) context.getSystemService(Context.STORAGE_SERVICE);
        String[] paths = (String[]) StorageManager.class.getMethod("getVolumePaths").invoke(sm);
        List<String> ps = new ArrayList<String>();
        for (String path : paths) {
            String status = (String) StorageManager.class.getMethod("getVolumeState", String.class).invoke(sm, path);
            if (status.equals(android.os.Environment.MEDIA_MOUNTED)) {
                ps.add(path);
            }
        }
        return ps.toArray(new String[ps.size()]);
    } catch (Exception e) {
        e.printStackTrace();
    }

    return null;
}
```

#### 方法2 {#方法2}
```java
public static String[] getExternalStoragePaths() {
    BufferedReader in = null;
    try {
        in = new BufferedReader(new InputStreamReader(new FileInputStream("/proc/mounts")));
        List<String> ps = new ArrayList<String>();
        try {
            for (String l; (l = in.readLine()) != null; ) {
                if (contains(l, KW_BLACK) || !contains(l, KW_WHITE)) {
                    continue;
                }

                String[] elements = l.split(" ");
                if (elements.length > 1 && elements[1] != null) {
                    ps.add(elements[1]);
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return ps.toArray(new String[ps.size()]);
    } catch (FileNotFoundException e) {
        e.printStackTrace();
    } finally {
        if (in != null) {
        try {
            in.close();
        } catch (IOException e) {}
        }
    }
    return null;
}

private static boolean contains(String src, String[] kws) {
    if (src != null && kws != null) {
        for (String kw : kws) {
            if (src.contains(kw)) {
                return true;
            }
        }
    }
    return false;
}

 private static final String[] KW_BLACK = {
           "secure",
           "asec",
           "legacy",
           "shell",
           "private",
           "obb",
           "media",
           "smb",
           "Bootloader",
           "Reserve",
           "on",
   };

   private static final String[] KW_WHITE = {
           "fat",
   };
```



### <a id="markdown-getRunningAppProcesses"></a>获取应用进程信息 {#获取应用进程信息}
根据系统提供的方法`ActivityManager.getRunningAppProcesses `可以获取到，但是在`API >= 22 `的设备上获取的信息是不完整的，此时可以通过获取`/proc`下文件夹进行比对（在开启应用时，在此路径下都会加载一个文件夹用于保存进程信息）,方法来源于[GitHub](https://github.com/jaredrummler/AndroidProcesses/blob/master/library/src/main/java/com/jaredrummler/android/processes/ProcessManager.java)。

#### 部分代码展示 {#部分代码展示}
```java
public static List<AndroidAppProcess> getRunningForegroundApps(Context ctx) {
    List<AndroidAppProcess> processes = new ArrayList<>();
    File[] files = new File("/proc").listFiles();
    PackageManager pm = ctx.getPackageManager();
    for (File file : files) {
        if (file.isDirectory()) {
            int pid;
            try {
                pid = Integer.parseInt(file.getName());
            } catch (NumberFormatException e) {
                continue;
            }

            try {
                AndroidAppProcess process = new AndroidAppProcess(pid);
                if (process.foreground
                    // ignore system processes. First app user starts at 10000.
                    && (process.uid < 1000 || process.uid > 9999)
                    // ignore processes that are not running in the default app process.
                    && !process.name.contains(":")
                    // Ignore processes that the user cannot launch.
                    && pm.getLaunchIntentForPackage(process.getPackageName()) != null) {
                        processes.add(process);
                    }
            } catch (AndroidAppProcess.NotAndroidAppProcessException ignored) {
            } catch (IOException e) {
                log(e, "Error reading from /proc/%d.", pid);
                // System apps will not be readable on Android 5.0+ if SELinux is enforcing.
                // You will need root access or an elevated SELinux context to read all files under /proc.
            }
        }
    }
    return processes;
}
```


### <a id="markdown-queryPacakgeSize"></a>获取已安装软件的大小 {#获取已安装软件的大小}
```java
public void queryPacakgeSize(AppInfo info) throws Exception {
    if (info != null && info.packageName != null) {
        // 使用放射机制得到PackageManager类的隐藏函数getPackageSizeInfo
        try {
            int sdkcode = getAndroidSDKVersion();
            if (sdkcode > 16) {
                Method getPackageSizeInfo = mPackageManager.getClass()
                           .getDeclaredMethod("getPackageSizeInfo",
                                   String.class, int.class,
                                   IPackageStatsObserver.class);
               // 调用该函数，并且给其分配参数 ，待调用流程完成后会回调PkgSizeObserver类的函数
               getPackageSizeInfo.invoke(mPackageManager,
                           info.packageName,
                           android.os.Process.myUid() / 100000,
                           new PkgSizeObserver(info));
            } else {
                    // 通过反射机制获得该隐藏函数
                    Method getPackageSizeInfo = mPackageManager.getClass()
                           .getDeclaredMethod("getPackageSizeInfo",
                                   String.class, IPackageStatsObserver.class);
                // 调用该函数，并且给其分配参数 ，待调用流程完成后会回调PkgSizeObserver类的函数
                getPackageSizeInfo.invoke(mPackageManager,
                           info.packageName, new PkgSizeObserver(info));
           }
         } catch (Exception ex) {
            ex.printStackTrace();
            throw ex; // 抛出异常
         }
       }
   }
```


### <a id="markdown-createReflectedImage"></a>生成带倒影的Bitmap图像 {#生成带倒影的Bitmap图像}
```java
public static Bitmap createReflectedImage(Bitmap originalImage,
                                          float reflectionHeightScale, int width, int height, int space) {
    if (null == originalImage) {
        throw new IllegalArgumentException("src can not be null");
    }

    if (reflectionHeightScale <= 0 || reflectionHeightScale > 1) {
        throw new IllegalArgumentException(
                "reflectionHeightScale must be during 0 ~ 1");
    }

    int reflectionHeight = (int) (height * reflectionHeightScale);

    Matrix matrix = new Matrix();
    // 实现图片翻转90度
    matrix.preScale(1, -1);
    // 创建倒影图片
    Bitmap reflectionImage = Bitmap.createBitmap(originalImage, 0, height
            - reflectionHeight, width, reflectionHeight, matrix, false);
    // 创建总图片（原图片 + 倒影图片）
    Bitmap finalReflection = Bitmap.createBitmap(width,
            (height + reflectionHeight) + space, Config.ARGB_8888);
    // 创建画布
    Canvas canvas = new Canvas(finalReflection);
    canvas.drawBitmap(originalImage, 0, 0, null);
    // 把倒影图片画到画布上
    canvas.drawBitmap(reflectionImage, 0, height + 1 + space, null);
    Paint shaderPaint = new Paint();
    // 创建线性渐变LinearGradient对象
    LinearGradient shader = new LinearGradient(0,
            originalImage.getHeight(), 0, finalReflection.getHeight() + 1,
            0x70ffffff, 0x00ffffff, TileMode.MIRROR);
    shaderPaint.setShader(shader);
    shaderPaint.setXfermode(new PorterDuffXfermode(Mode.DST_IN));
    // 画布画出反转图片大小区域，然后把渐变效果加到其中，就出现了图片的倒影效果。
    canvas.drawRect(0, height + 1, width, finalReflection.getHeight(),
            shaderPaint);
    return finalReflection;
}
```

### <a id="markdown-imageloaderlocal"></a>ImageLoader加载本地图片工具类 {#ImageLoader加载本地图片工具类}
```java
import android.widget.ImageView;

import com.nostra13.universalimageloader.core.ImageLoader;

/**
 * 异步加载本地图片工具类
 *
 * @author tony
 *
 */
public class LoadLocalImageUtil {
    private LoadLocalImageUtil() {
    }

    private static LoadLocalImageUtil instance = null;

    public static synchronized LoadLocalImageUtil getInstance() {
        if (instance == null) {
            instance = new LoadLocalImageUtil();
        }
        return instance;
    }

    /**
     * 从内存卡中异步加载本地图片
     *
     * @param uri
     * @param imageView
     */
    public void displayFromSDCard(String uri, ImageView imageView) {
        // String imageUri = "file:///mnt/sdcard/image.png"; // from SD card
        ImageLoader.getInstance().displayImage("file://" + uri, imageView);
    }

    /**
     * 从assets文件夹中异步加载图片
     *
     * @param imageName
     *            图片名称，带后缀的，例如：1.png
     * @param imageView
     */
    public void dispalyFromAssets(String imageName, ImageView imageView) {
        // String imageUri = "assets://image.png"; // from assets
        ImageLoader.getInstance().displayImage("assets://" + imageName,
                imageView);
    }

    /**
     * 从drawable中异步加载本地图片
     *
     * @param imageId
     * @param imageView
     */
    public void displayFromDrawable(int imageId, ImageView imageView) {
        // String imageUri = "drawable://" + R.drawable.image; // from drawables
        // (only images, non-9patch)
        ImageLoader.getInstance().displayImage("drawable://" + imageId,
                imageView);
    }

    /**
     * 从内容提提供者中抓取图片
     */
    public void displayFromContent(String uri, ImageView imageView) {
        // String imageUri = "content://media/external/audio/albumart/13"; //
        // from content provider
        ImageLoader.getInstance().displayImage("content://" + uri, imageView);
    }

}
```
