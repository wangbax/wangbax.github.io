---
title: Android自定义Drawable时Attempt to invoke virtual method Drawable$ConstantState.newDrawable() on a null object reference
date: '2017-06-14T18:56:09+08:00'
category: Android
summary: 开发过程中，部分用户( 华为 NXT-AL10,华为 MHA AL00 等)反馈只要弹框就会崩溃，通过反馈用户的协助，找到日志如下：
permalink: /2017/06/14/wt-android-drawable-issue/
---

## 简介 {#简介}

开发过程中，部分用户(**华为 NXT-AL10,华为 MHA AL00**等)反馈只要弹框就会崩溃，通过反馈用户的协助，找到日志如下：

```java
java.lang.NullPointerException
Attempt to invoke virtual method 'android.graphics.drawable.Drawable android.graphics.drawable.Drawable$ConstantState.newDrawable()' on a null object reference
解析原始
1 com.android.internal.policy.BackdropFrameRenderer.onResourcesLoaded(BackdropFrameRenderer.java:113)
2 com.android.internal.policy.BackdropFrameRenderer.<init>(BackdropFrameRenderer.java:85)
3 com.android.internal.policy.DecorView.onWindowDragResizeStart(DecorView.java:2107)
4 android.view.ViewRootImpl.startDragResizing(ViewRootImpl.java:7689)
5 android.view.ViewRootImpl.performTraversals(ViewRootImpl.java:2068)
6 android.view.ViewRootImpl.doTraversal(ViewRootImpl.java:1366)
7 android.view.ViewRootImpl$TraversalRunnable.run(ViewRootImpl.java:6768)
8 android.view.Choreographer$CallbackRecord.run(Choreographer.java:926)
9 android.view.Choreographer.doCallbacks(Choreographer.java:735)
10 android.view.Choreographer.doFrame(Choreographer.java:667)
11 android.view.Choreographer$FrameDisplayEventReceiver.run(Choreographer.java:912)
12 android.os.Handler.handleCallback(Handler.java:761)
13 android.os.Handler.dispatchMessage(Handler.java:98)
14 android.os.Looper.loop(Looper.java:156)
15 android.app.ActivityThread.main(ActivityThread.java:6531)
16 java.lang.reflect.Method.invoke(Native Method)
17 com.android.internal.os.ZygoteInit$MethodAndArgsCaller.run(ZygoteInit.java:941)
18 com.android.internal.os.ZygoteInit.main(ZygoteInit.java:831)
```

<a id="more"></a>

## 解决 {#解决}

**当在自定义`Drawable`时，需要注意，如果此`Drawable`有可能会被当做背景设置为[Window](https://developer.android.com/reference/android/view/Window.html)的背景，类似于`getWindow().setBackgroundDrawable(BlankDrawable)`,则必须在除了正常的绘制逻辑之外，需要重写[Drawable#getConstantState()](https://developer.android.com/reference/android/graphics/drawable/Drawable.html#getConstantState())方法,返回一个不会空的ConstantState对象**

## 解析 {#解析}

### 从上往下 {#从上往下}

首先，根据日志，找到最后的崩溃的位置`BackdropFrameRenderer#onResourcesLoaded()`：

```java
public class BackdropFrameRenderer extends Thread implements Choreographer.FrameCallback {
     // ...
     public BackdropFrameRenderer(DecorView decorView, ThreadedRenderer renderer, Rect initialBounds,
            Drawable resizingBackgroundDrawable, Drawable captionBackgroundDrawable,
            Drawable userCaptionBackgroundDrawable, int statusBarColor, int navigationBarColor,
            boolean fullscreen, Rect systemInsets, Rect stableInsets, int resizeMode) {
        setName("ResizeFrame");

        mRenderer = renderer;
        // 唯一调用的地方
        onResourcesLoaded(decorView, resizingBackgroundDrawable, captionBackgroundDrawable,
                userCaptionBackgroundDrawable, statusBarColor, navigationBarColor);

        // ...
    }

  void onResourcesLoaded(DecorView decorView, Drawable resizingBackgroundDrawable,
            Drawable captionBackgroundDrawableDrawable, Drawable userCaptionBackgroundDrawable,
            int statusBarColor, int navigationBarColor) {
        mDecorView = decorView;
        // 实际崩溃的位置
        mResizingBackgroundDrawable = resizingBackgroundDrawable != null
                ? resizingBackgroundDrawable.getConstantState().newDrawable()
                : null;
        mCaptionBackgroundDrawable = captionBackgroundDrawableDrawable != null
                ? captionBackgroundDrawableDrawable.getConstantState().newDrawable()
                : null;
        mUserCaptionBackgroundDrawable = userCaptionBackgroundDrawable != null
                ? userCaptionBackgroundDrawable.getConstantState().newDrawable()
                : null;
       // ...
    }
}
```

再往上查`DecorView#onWindowDragResizeStart()`:

```java
@Override
public void onWindowDragResizeStart(Rect initialBounds, boolean fullscreen, Rect systemInsets,
        Rect stableInsets, int resizeMode) {
    if (mWindow.isDestroyed()) {
        // If the owner's window is gone, we should not be able to come here anymore.
        releaseThreadedRenderer();
        return;
    }
    if (mBackdropFrameRenderer != null) {
        return;
    }
    final ThreadedRenderer renderer = getHardwareRenderer();
    if (renderer != null) {
        loadBackgroundDrawablesIfNeeded();
        // BackdropFrameRenderer初始化的地方
        mBackdropFrameRenderer = new BackdropFrameRenderer(this, renderer,
                initialBounds, mResizingBackgroundDrawable, mCaptionBackgroundDrawable,
                mUserCaptionBackgroundDrawable, getCurrentColor(mStatusColorViewState),
                getCurrentColor(mNavigationColorViewState), fullscreen, systemInsets,
                stableInsets, resizeMode);

        // ...
}
```

可以发现传递到`BackdropFrameRenderer`中的`resizingBackgroundDrawable`实际是一个`DecorView`中的局部变量`mResizingBackgroundDrawable`,此时，查找这个局部变量的来源，包括了两个地方：

```java
public void setWindowBackground(Drawable drawable) {
    if (getBackground() != drawable) {
        setBackgroundDrawable(drawable);
        if (drawable != null) {
            mResizingBackgroundDrawable = enforceNonTranslucentBackground(drawable,
                    mWindow.isTranslucent() || mWindow.isShowingWallpaper());
        } else {
            mResizingBackgroundDrawable = getResizingBackgroundDrawable(
                    getContext(), 0, mWindow.mBackgroundFallbackResource,
                    mWindow.isTranslucent() || mWindow.isShowingWallpaper());
        }
        if (mResizingBackgroundDrawable != null) {
            mResizingBackgroundDrawable.getPadding(mBackgroundPadding);
        } else {
            mBackgroundPadding.setEmpty();
        }
        drawableChanged();
    }
}

private void loadBackgroundDrawablesIfNeeded() {
    if (mResizingBackgroundDrawable == null) {
        mResizingBackgroundDrawable = getResizingBackgroundDrawable(getContext(),
                mWindow.mBackgroundResource, mWindow.mBackgroundFallbackResource,
                mWindow.isTranslucent() || mWindow.isShowingWallpaper());
        if (mResizingBackgroundDrawable == null) {
            // We shouldn't really get here as the background fallback should be always
            // available since it is defaulted by the system.
            Log.w(mLogTag, "Failed to find background drawable for PhoneWindow=" + mWindow);
        }
    }
    if (mCaptionBackgroundDrawable == null) {
        mCaptionBackgroundDrawable = getContext().getDrawable(
                R.drawable.decor_caption_title_focused);
    }
    if (mResizingBackgroundDrawable != null) {
        mLastBackgroundDrawableCb = mResizingBackgroundDrawable.getCallback();
        mResizingBackgroundDrawable.setCallback(null);
    }
}
```

OK，从最终崩溃向上已经到头了，因为无法确定，到底哪里地方会调用`public`方法，所以，从触发的地方查查看。

### 从下而上 {#从下而上}

由于触发地方是项目自定义的一个`BottomSheetDialog`，初始化代码：

```java
public BottomSheetDialog(Context context, int style) {
    super(context, style);

    //Override style to ensure not show window's title or background.
    //TODO: find a way to ensure windowIsFloating attribute is false.
    requestWindowFeature(Window.FEATURE_NO_TITLE);
    getWindow().setBackgroundDrawable(BlankDrawable.getInstance());
    WindowManager.LayoutParams layout = getWindow().getAttributes();
    layout.width = ViewGroup.LayoutParams.MATCH_PARENT;
    layout.height = ViewGroup.LayoutParams.MATCH_PARENT;
    layout.windowAnimations = R.style.DialogNoAnimation;
    getWindow().setAttributes(layout);

    init(context, style);
}
```

通过`getWindow().setBackgroundDrawable(BlankDrawable.getInstance())`往下跟，发现会调用到`PhoneWindow`的`setBackgroundDrawable(drawable)`方法：

```java
@Override
public final void setBackgroundDrawable(Drawable drawable) {
    if (drawable != mBackgroundDrawable || mBackgroundResource != 0) {
        mBackgroundResource = 0;
        mBackgroundDrawable = drawable;
        if (mDecor != null) {
            mDecor.setWindowBackground(drawable);
        }
        if (mBackgroundFallbackResource != 0) {
            mDecor.setBackgroundFallback(drawable != null ? 0 : mBackgroundFallbackResource);
        }
    }
}
```

而在这个方法中会把这个`drawable`设置给`DecorView`。OK，对上了。

这个时候，查看下之前使用自定义的`Drawable`代码：

```java
/**
 * A drawable that draw nothing.
 * @author Rey
 *
 */
public class BlankDrawable extends Drawable {

    private static BlankDrawable mInstance;

    private ColorState mColorState;

    public static BlankDrawable getInstance(){
        if(mInstance == null)
            synchronized (BlankDrawable.class) {
                if(mInstance == null)
                    mInstance = new BlankDrawable();
            }

        return mInstance;
    }

    private BlankDrawable() {
        mColorState = new ColorState();
    }

    @Override
    public void draw(Canvas canvas) {}

    @Override
    public void setAlpha(int alpha) {}

    @Override
    public void setColorFilter(ColorFilter cf) {}

}
```

此方法并没有`getConstantState()`方法，在起父类`Drawable`中：

```java
/**
 * Return a {@link ConstantState} instance that holds the shared state of this Drawable.
 *
 * @return The ConstantState associated to that Drawable.
 * @see ConstantState
 * @see Drawable#mutate()
 */
public ConstantState getConstantState() {
    return null;
}
```

查看默认为null。

**总结一下，就是在某些特殊情况，特殊机型（问我怎么特殊？我怎么知道，问华为去，┑(￣Д ￣)┍），会在某些情况触发了分屏的机制，导致调用到`startDragResizing()`从而触发了`BackdropFrameRenderer`中的`onResourcesLoaded()`而由于自定义的`BlankDrawable`并没有重写父类`getConstantState()`方法，导致了`NPE`**

综上，修复代码可简单自定义一个内部类实现`ConstantState`:

```java
/**
 * A drawable that draw nothing.
 * @author Rey
 *
 */
public class BlankDrawable extends Drawable {

    private static BlankDrawable mInstance;

    private ColorState mColorState;

    public static BlankDrawable getInstance(){
        if(mInstance == null)
            synchronized (BlankDrawable.class) {
                if(mInstance == null)
                    mInstance = new BlankDrawable();
            }

        return mInstance;
    }

    private BlankDrawable() {
        mColorState = new ColorState();
    }

    @Override
    public void draw(Canvas canvas) {}

    @Override
    public void setAlpha(int alpha) {}

    @Override
    public void setColorFilter(ColorFilter cf) {}

    @Override
    public int getOpacity() {
        return PixelFormat.TRANSPARENT;
    }

    // fix bugly: #441332
    // 如果自定义Drawable会当做window的背景（getWindow().setBackgroundDrawable(BlankDrawable.getInstance());），
    // 需要重写此方法，否则在部分机型（华为 NXT-AL10，华为 MHA AL00等）上，在某些情况，调用到BackdropFrameRenderer#onResourcesLoaded中
    // 会导致getConstantState().newDrawable()报NPE。
    @Nullable
    @Override
    public ConstantState getConstantState() {
        return mColorState;
    }

    final static class ColorState extends ConstantState {

        @NonNull
        @Override
        public Drawable newDrawable() {
            return BlankDrawable.getInstance();
        }

        @Override
        public int getChangingConfigurations() {
            return 0;
        }
    }
}
```
