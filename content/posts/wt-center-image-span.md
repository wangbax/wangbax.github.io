---
title: Android TextView头尾展示标签图片，并且尾部标签不被挤出
date: '2016-08-03T14:39:22+08:00'
updated: '2017-06-07T17:04:32+08:00'
category: Android
summary: 开发中需要为TextView头尾添加标签图片，并且 尾部标签不被挤出 ，考虑了几种可能的方案：
permalink: /2016/08/03/wt-center-image-span/
---

## 简介 {#简介}

开发中需要为TextView头尾添加标签图片，并且**尾部标签不被挤出**，考虑了几种可能的方案：

1. 动态计算TextView的文本长度和每行的宽度
2. 使用TextView的Span
3. 自定义一个View，自己绘制文本和标签图片

<a id="more"></a>

### 对比 {#对比}

* 第一种由于Android的碎片化极其严重，各种机型，各种字体等等，更重要的是TextView并没有对应的API可以进行回去绘制。PASS。
* 第二种可行性还是不错的，Android原生支持了很多类型的Span。但是有一个问题就是没有可以当图片和文本居中的Span可以使用。如果使用就必须自定义一个Span。查看[DynamicDrawableSpan](https://developer.android.com/reference/android/graphics/Paint.FontMetrics.html?q=DynamicDrawableSpan),[ImageSpan](https://developer.android.com/reference/android/graphics/Paint.FontMetrics.html?q=ImageSpan)等Span的源码，发现自定义的话是可以满足的。待定。
* 第三种自己可以定制自己想实现的各种效果。但是适配性比较难保证。待定

最后综合考虑，实验第二种是否能满足，如果不能满足，则使用第三种。

### 方案二 {#方案二}

#### 自定义Span {#自定义Span}

涉及到的类：`Paint.FontMetrics`，它表示绘制字体时的度量标准。[Google的官方api文档](https://developer.android.com/reference/android/graphics/Paint.FontMetrics.html)对它的字段说明如下：
![android imagespan fontmetrics](/images/2016/20160803143922-1.png)

* ascent: 字体最上端到基线的距离，为负值。
* descent：字体最下端到基线的距离，为正值。
* bottom: 最下字符到baseline的距离。即为descent的最大值
* top: 最高字符到baseline的距离。即为ascent的最大值
* leading: 上一行字符的descent到下一行字符ascent的距离

回到主题，我们要让图片与`Textview`对齐，只需把图片放到descent线和ascent线之间的中间位置就可以了。实现方式为仿照[DynamicDrawableSpan](https://developer.android.com/reference/android/graphics/Paint.FontMetrics.html?q=DynamicDrawableSpan)，重写[DynamicDrawableSpan](https://developer.android.com/reference/android/graphics/Paint.FontMetrics.html?q=DynamicDrawableSpan)类的draw方法。最终实现如下：

```java
/**
 * TagTitleViewSpan
 * <p>
 * 仿照{@link android.text.style.DynamicDrawableSpan}
 * <p>
 * Created by wt on 17/3/10.
 */
class TagTitleViewSpan extends ReplacementSpan {

    // ...省略构造参数

    // 绘制实现类
    private TagViewInner mTagInner;

    @Override
    public int getSize(@NonNull Paint paint, CharSequence text, @IntRange(from = 0) int start, @IntRange(from = 0) int end, @Nullable Paint.FontMetricsInt fm) {
        if (null == mTagInner || !mTagInner.isValid()) {
            return 0;
        }
        Rect rect = mTagInner.getRect();
        if (fm != null) {
            // 保证当文字高度低于图片时，文字居中
            Paint.FontMetricsInt fmPaint = paint.getFontMetricsInt();
            int fontHeight = fmPaint.bottom - fmPaint.top;
            int drHeight = rect.bottom - rect.top;

            int top = drHeight / 2 - fontHeight / 4;
            int bottom = drHeight / 2 + fontHeight / 4;

            fm.ascent = -bottom;
            fm.top = -bottom;
            fm.bottom = top;
            fm.descent = top;
        }
        return rect.width() < 0 ? 0 : rect.width();
    }

    @Override
    public void draw(@NonNull Canvas canvas, CharSequence text, @IntRange(from = 0) int start, @IntRange(from = 0) int end, float x, int top, int y, int bottom, @NonNull Paint paint) {
        if (null == mTagInner || !mTagInner.isValid()) {
            return;
        }
        Rect rect = mTagInner.getRect();

        int transY = 0;
        switch (mVerticalAlignment) {
            case ALIGN_BASELINE:
                transY = bottom - rect.bottom - paint.getFontMetricsInt().descent;
                break;
            case ALIGN_TEXT_BOTTOM:
                Paint.FontMetricsInt fm1 = paint.getFontMetricsInt();
                transY = y + fm1.descent / 2 - rect.bottom;
                break;
            case ALIGN_TEXT_CENTER:
                // 图片居中计算
                Paint.FontMetricsInt fm = paint.getFontMetricsInt();
                transY = (y + fm.descent + y + fm.ascent) / 2
                        - rect.bottom / 2;
                if (transY < 0) {
                    transY = 0;
                }
                break;
            default:
                transY = bottom - rect.bottom;
                break;
        }

        canvas.save();
        // 绘制图片
        canvas.translate(x, transY);
        mTagInner.draw(context, canvas);
        canvas.restore();
    }

}
```

#### 文本长度问题 {#文本长度问题}

既然**图片插入**和**居中**没有问题，那么最后一个问题就是如何保证**尾部标签不被挤出**呢。搜索到[[Android]TextUtils.ellipsize()截取指定长度字符串(附图文混排)](http://blog.csdn.net/sodino/article/details/8778761)，让我注意到[TextUtils.html.ellipsize(text, p, avail, where)](https://developer.android.com/reference/android/text/TextUtils.html#ellipsize)这个方法。其中`avail`字段代表的是有效长度，`text` 代码需要截取的字段。这个方法是TextView截取的静态方法。经测试，可用。

`avail`字段必须是**精确**长度，意思就是说，他会按照你传入的长度对`text`截取。一开始，我是计算长度是按照：

`View的长度 * MaxLines - 图片已占用的长度 - padding(l,t,r,b)`

![但是](/images/2017/20170607163800.jpg)

当把截取后的文本设为`TextView`时，`TextView`会根据自身的属性进行布局，当文本文本换行时，如果遇到当前行空出部分字符的情况，就会导致实际的**精确**长度比我计算时的要短，最后的标签图片还是会截。无奈，经调试确认方案是：在计算时，每行减去`textsize / 3`，即：

`View的长度 * maxLines - 图片已占用的长度 - padding(l,t,r,b) - textsize / 3 * (maxLines - 1)`

最后计算的代码如下：

```java
/**
 * 截取传入的字符串
 *
 * @param old       传入的字符串
 * @param usedWidth 已被占用的宽度
 * @return 截取好的字符串
 */
private String measureText(String old, int usedWidth) {
    if (TextUtils.isEmpty(old)) {
        return null;
    }
    int maxLines = TextViewCompat.getMaxLines(this);
    if (maxLines == Integer.MAX_VALUE) {
        return old;
    }
    if (maxLines < 0) {
        maxLines = 0;
    }
    //有效文本展示区域
    int availableWidth = maxLines * (getWidth() -
            getPaddingLeft() - getPaddingRight())
            - usedWidth - (int) getTextSize() / 3 * (maxLines - 1);
    return (String) TextUtils.ellipsize(old, getPaint(), availableWidth, TextUtils.TruncateAt.END);
}
```

#### 效果 {#效果}

![效果图](/images/2016/20160803143922-3.png)

### 方案三 {#方案三}

*TODO*

## 鸣谢 {#鸣谢}

* [TextUtils.ellipsize()截取指定长度字符串(附图文混排)](http://blog.csdn.net/sodino/article/details/8778761)
* [Android ImageSpan与TextView中的text居中对齐问题解决（无论TextView设置行距与否）](http://www.cnblogs.com/withwind318/p/5541267.html)
* [Android字符串进阶之三：字体属性及测量（FontMetrics）](http://mikewang.blog.51cto.com/3826268/871765)
* [Android ImageSpan的图文居中对齐](http://blog.csdn.net/gaoyucindy/article/details/39473135)
