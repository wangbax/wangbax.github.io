---
title: 关于ViewPager切换页面时调用requestLayout阻塞问题
date: '2017-03-28T11:38:59+08:00'
updated: '2017-06-08T11:03:52+08:00'
category: Android
summary: 在实际开发过程中，使用到 ViewPager + Fragment 的方式进行显示布局。由于存在需求缓存已加载的 Fragment ，故自定义了 FragmentAdapter ，不 destoryItem ，仅仅注释了 destroyItem 方法里的操作，代码 NoDestr
permalink: /2017/03/28/wt-viewpager-requestlayout/
---

## 简介 {#简介}

在实际开发过程中，使用到`ViewPager`+`Fragment`的方式进行显示布局。由于存在需求缓存已加载的`Fragment`，故自定义了`FragmentAdapter`，不`destoryItem`，仅仅注释了`destroyItem`方法里的操作，代码[NoDestroyItemFragmentAdapter](#wt-name-adapter)。

至于为什么不设置[ViewPager.setOffscreenPageLimit(int limit)](https://developer.android.com/reference/android/support/v4/view/ViewPager.html#setOffscreenPageLimit(int))方法，是由于如果设置了此方法，会导致所有的页面同时加载，增加了缓存布局数量。

<a id="more"></a>

## BUG {#BUG}

### 描述 {#描述}

此时，导致了一个问题：当有非当前展示的页面需要刷新时，调用的`requestLayout()`无法执行到`onLayout()`方法。对应项目中的现象就是：调用`notifyDataChanged()`无法刷新列表。

### 解决 {#解决}

在`Fragment`的`setMenuVisibility`中调用一次`requestLayout()`。保证当前View的`PFLAG_FORCE_LAYOUT`被消费掉。

```java
@Override
public void setMenuVisibility(boolean menuVisible) {
    super.setMenuVisibility(menuVisible);

    //解决当非当前页面刷新了此页面时,requestLayout无限阻塞问题
    if (menuVisible && null != getView()){
        getView().postDelayed(new Runnable() {
            @Override
            public void run() {
                if (null == getView()) {
                    return;
                }
                getView().requestLayout();
            }
        }, 200);
    }
}
```

### 分析 {#分析}

查看[RecyclerView](https://developer.android.com/reference/android/support/v7/widget/RecyclerView.html)源码，查看`RecyclerViewDataObserver`的`onChanged`方法

```java

@Override
public void onChanged() {
    assertNotInLayoutOrScroll(null);
    if (mAdapter.hasStableIds()) {
    // TODO Determine what actually changed.
    // This is more important to implement now since this callback will disable all
    // animations because we cannot rely on positions.
        mState.mStructureChanged = true;
        setDataSetChangedAfterLayout();
    } else {
        mState.mStructureChanged = true;
        setDataSetChangedAfterLayout();
    }
    if (!mAdapterHelper.hasPendingUpdates()) {
        requestLayout();
    }
}
```
继续查看`requestLayout()`和`onLayout()`方法;

```java

@Override
protected void onLayout(boolean changed, int l, int t, int r, int b) {
    TraceCompat.beginSection(TRACE_ON_LAYOUT_TAG);
    dispatchLayout();
    TraceCompat.endSection();
    mFirstLayoutComplete = true;
}

@Override
public void requestLayout() {
    if (mEatRequestLayout == 0 && !mLayoutFrozen) {
        super.requestLayout();
    } else {
        mLayoutRequestEaten = true;
    }
}
```
其中`dispatchLayout()`即为`RecyclerView`页面布局。

查看`View.requestLayout()`方法

```java
@CallSuper
public void requestLayout() {
    if (mMeasureCache != null) mMeasureCache.clear();

    if (mAttachInfo != null && mAttachInfo.mViewRequestingLayout == null) {
        // Only trigger request-during-layout logic if this is the view requesting it,
        // not the views in its parent hierarchy
        ViewRootImpl viewRoot = getViewRootImpl();
        if (viewRoot != null && viewRoot.isInLayout()) {
            if (!viewRoot.requestLayoutDuringLayout(this)) {
                return;
            }
        }
        mAttachInfo.mViewRequestingLayout = this;
    }

    mPrivateFlags |= PFLAG_FORCE_LAYOUT;
    mPrivateFlags |= PFLAG_INVALIDATED;

    if (mParent != null && !mParent.isLayoutRequested()) {
        mParent.requestLayout();
    }
    if (mAttachInfo != null && mAttachInfo.mViewRequestingLayout == this) {
        mAttachInfo.mViewRequestingLayout = null;
    }
}
```

当断点到`mParent.isLayoutRequested()`时发现，此时其`mParent`的`mPrivateFlags`存在标志位`PFLAG_FORCE_LAYOUT`即`mParent.isLayoutRequested()`返回的是**true**

而对于标志位`PFLAG_FORCE_LAYOUT`是在`forceLayout()`和`requestLayout()`时设置,layout结束时清空：

```java
public void layout(int l, int t, int r, int b) {
    if ((mPrivateFlags3 & PFLAG3_MEASURE_NEEDED_BEFORE_LAYOUT) != 0) {
        onMeasure(mOldWidthMeasureSpec, mOldHeightMeasureSpec);
        mPrivateFlags3 &= ~PFLAG3_MEASURE_NEEDED_BEFORE_LAYOUT;
    }

    int oldL = mLeft;
    int oldT = mTop;
    int oldB = mBottom;
    int oldR = mRight;

    boolean changed = isLayoutModeOptical(mParent) ?
            setOpticalFrame(l, t, r, b) : setFrame(l, t, r, b);

    if (changed || (mPrivateFlags & PFLAG_LAYOUT_REQUIRED) == PFLAG_LAYOUT_REQUIRED) {
        // onLayout
    }

    mPrivateFlags &= ~PFLAG_FORCE_LAYOUT;
    mPrivateFlags3 |= PFLAG3_IS_LAID_OUT;
}
```

此时，想到会不会是因为布局的父类只被requestLayout()而没有执行layout方法。对应的父类就是ViewPager，此时查看ViewPager的onLayout方法：

```java
@Override
   protected void onLayout(boolean changed, int l, int t, int r, int b) {
       final int count = getChildCount();
       int width = r - l;
       int height = b - t;
       int paddingLeft = getPaddingLeft();
       int paddingTop = getPaddingTop();
       int paddingRight = getPaddingRight();
       int paddingBottom = getPaddingBottom();
       final int scrollX = getScrollX();

       int decorCount = 0;

       // First pass - decor views. We need to do this in two passes so that
       // we have the proper offsets for non-decor views later.
       //省略第一步的代码，此段代码只对应layout DecorView

       //如下代码计算子布局
       final int childWidth = width - paddingLeft - paddingRight;
       // Page views. Do this once we have the right padding offsets from above.
       for (int i = 0; i < count; i++) {
           final View child = getChildAt(i);
           if (child.getVisibility() != GONE) {
               final LayoutParams lp = (LayoutParams) child.getLayoutParams();
               ItemInfo ii;
               // 查看是否为DectorView并且当前子布局在缓存的列表中存在。坑就在这里
               if (!lp.isDecor && (ii = infoForChild(child)) != null) {
                   int loff = (int) (childWidth * ii.offset);
                   int childLeft = paddingLeft + loff;
                   int childTop = paddingTop;
                   if (lp.needsMeasure) {
                       // This was added during layout and needs measurement.
                       // Do it now that we know what we're working with.
                       lp.needsMeasure = false;
                       final int widthSpec = MeasureSpec.makeMeasureSpec(
                               (int) (childWidth * lp.widthFactor),
                               MeasureSpec.EXACTLY);
                       final int heightSpec = MeasureSpec.makeMeasureSpec(
                               (int) (height - paddingTop - paddingBottom),
                               MeasureSpec.EXACTLY);
                       child.measure(widthSpec, heightSpec);
                   }
                   if (DEBUG) Log.v(TAG, "Positioning #" + i + " " + child + " f=" + ii.object
                           + ":" + childLeft + "," + childTop + " " + child.getMeasuredWidth()
                           + "x" + child.getMeasuredHeight());
                   child.layout(childLeft, childTop,
                           childLeft + child.getMeasuredWidth(),
                           childTop + child.getMeasuredHeight());
               }
           }
       }
       mTopPageBounds = paddingTop;
       mBottomPageBounds = height - paddingBottom;
       mDecorChildCount = decorCount;

       if (mFirstLayout) {
           scrollToItem(mCurItem, false, 0, false);
       }
       mFirstLayout = false;
   }
```

在上面的判断中会判断是否存在`ViewPager`缓存的列表中，而这个列表维护是在起当有元素新增时添加，当元素移除时删除。坑就在这里。

**在当前项目，由于没有设置默认绘制的数量，使用了其默认数量即当前+1+1（一前一后），此时如果当切换的Item超过了这个数量，布局的里面的列表item就不会包括切换前的那个布局，就导致切换前的那个布局无法`layout()`。从而导致了后面的一系列问题（子View的`requestLayout()`无法响应）**。

### 总结 {#总结}

1. 当自定义了如下adapter之后，可通过再次调用`requestLayout()`来解决
2. 可通过`ViewPager`的`ViewPager.setOffscreenPageLimit(int limit)`进行控制

## 代码区 {#代码区}

#### <a id="wt-name-adapter"></a>NoDestroyItemFragmentAdapter {#NoDestroyItemFragmentAdapter}

```java

/*
 * Copyright (C) 2011 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


import android.os.Bundle;
import android.os.Parcelable;
import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentManager;
import android.support.v4.app.FragmentTransaction;
import android.support.v4.view.PagerAdapter;
import android.util.Log;
import android.view.View;
import android.view.ViewGroup;

import java.util.ArrayList;


public abstract class NoDestroyItemFragmentAdapter extends PagerAdapter {
    private static final String TAG = "taptapada";
    private static final boolean DEBUG = false;

    private final FragmentManager mFragmentManager;
    private FragmentTransaction mCurTransaction = null;

    private ArrayList<Fragment.SavedState> mSavedState = new ArrayList<Fragment.SavedState>();
    private ArrayList<Fragment> mFragments = new ArrayList<Fragment>();
    private Fragment mCurrentPrimaryItem = null;

    public NoDestroyItemFragmentAdapter(FragmentManager fm) {
        mFragmentManager = fm;
    }

    /**
     * Return the Fragment associated with a specified position.
     */
    public abstract Fragment getItem(int position);

    @Override
    public void startUpdate(ViewGroup container) {
    }

    @Override
    public Object instantiateItem(ViewGroup container, int position) {
        // If we already have this item instantiated, there is nothing
        // to do.  This can happen when we are restoring the entire pager
        // from its saved state, where the fragment manager has already
        // taken care of restoring the fragments we previously had instantiated.
        if (mFragments.size() > position) {
            Fragment f = mFragments.get(position);
            if (f != null) {
                return f;
            }
        }

        if (mCurTransaction == null) {
            mCurTransaction = mFragmentManager.beginTransaction();
        }

        Fragment fragment = getItem(position);
        if (mSavedState.size() > position) {
            Fragment.SavedState fss = mSavedState.get(position);
            if (fss != null) {
                fragment.setInitialSavedState(fss);
            }
        }
        while (mFragments.size() <= position) {
            mFragments.add(null);
        }
        fragment.setMenuVisibility(false);
        fragment.setUserVisibleHint(false);
        mFragments.set(position, fragment);
        mCurTransaction.add(container.getId(), fragment);

        return fragment;
    }

    @Override
    public void destroyItem(ViewGroup container, int position, Object object) {
//        Fragment fragment = (Fragment) object;
//
//        if (mCurTransaction == null) {
//            mCurTransaction = mFragmentManager.beginTransaction();
//        }
//        if (DEBUG) Log.v(TAG, "Removing item #" + position + ": f=" + object
//                + " v=" + ((Fragment)object).getView());
//        while (mSavedState.size() <= position) {
//            mSavedState.add(null);
//        }
//        mSavedState.set(position, fragment.isAdded()
//                ? mFragmentManager.saveFragmentInstanceState(fragment) : null);
//        mFragments.set(position, null);
//
//        mCurTransaction.remove(fragment);
    }

    @Override
    public void setPrimaryItem(ViewGroup container, int position, Object object) {
        Fragment fragment = (Fragment)object;
        if (fragment != mCurrentPrimaryItem) {
            if (mCurrentPrimaryItem != null) {
                mCurrentPrimaryItem.setMenuVisibility(false);
                mCurrentPrimaryItem.setUserVisibleHint(false);
            }
            if (fragment != null) {
                fragment.setMenuVisibility(true);
                fragment.setUserVisibleHint(true);
            }
            mCurrentPrimaryItem = fragment;
        }
    }

    @Override
    public void finishUpdate(ViewGroup container) {
//        if (mCurTransaction == null) {
//            mCurTransaction = mFragmentManager.beginTransaction();
//        }
        if (mCurTransaction != null) {
            mCurTransaction.commitAllowingStateLoss();
            mCurTransaction = null;
            mFragmentManager.executePendingTransactions();
        }
    }

    @Override
    public boolean isViewFromObject(View view, Object object) {
        return ((Fragment)object).getView() == view;
    }

    @Override
    public Parcelable saveState() {
        Bundle state = null;
        if (mSavedState.size() > 0) {
            state = new Bundle();
            Fragment.SavedState[] fss = new Fragment.SavedState[mSavedState.size()];
            mSavedState.toArray(fss);
            state.putParcelableArray("states", fss);
        }
        for (int i=0; i<mFragments.size(); i++) {
            Fragment f = mFragments.get(i);
            if (f != null && f.isAdded()) {
                if (state == null) {
                    state = new Bundle();
                }
                String key = "f" + i;
                mFragmentManager.putFragment(state, key, f);
            }
        }
        return state;
    }

    @Override
    public void restoreState(Parcelable state, ClassLoader loader) {
        if (state != null) {
            Bundle bundle = (Bundle)state;
            bundle.setClassLoader(loader);
            Parcelable[] fss = bundle.getParcelableArray("states");
            mSavedState.clear();
            mFragments.clear();
            if (fss != null) {
                for (int i=0; i<fss.length; i++) {
                    mSavedState.add((Fragment.SavedState)fss[i]);
                }
            }
            Iterable<String> keys = bundle.keySet();
            for (String key: keys) {
                if (key.startsWith("f")) {
                    int index = Integer.parseInt(key.substring(1));
                    Fragment f = mFragmentManager.getFragment(bundle, key);
                    if (f != null) {
                        while (mFragments.size() <= index) {
                            mFragments.add(null);
                        }
                        f.setMenuVisibility(false);
                        mFragments.set(index, f);
                    } else {
                        Log.w(TAG, "Bad fragment at key " + key);
                    }
                }
            }
        }
    }
}
```
