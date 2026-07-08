package com.lingban.lingban_mobile.wxapi

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.os.Bundle
import com.lingban.lingban_mobile.MainActivity
import com.tencent.mm.opensdk.modelbase.BaseReq
import com.tencent.mm.opensdk.modelbase.BaseResp
import com.tencent.mm.opensdk.openapi.IWXAPIEventHandler
import com.tencent.mm.opensdk.openapi.WXAPIFactory

class WXPayEntryActivity : Activity(), IWXAPIEventHandler {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleWechatIntent(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleWechatIntent(intent)
    }

    private fun handleWechatIntent(intent: Intent?) {
        val appId = getSharedPreferences(
            MainActivity.WECHAT_PAY_PREFS,
            Context.MODE_PRIVATE
        ).getString(MainActivity.WECHAT_APP_ID_KEY, null)

        if (appId.isNullOrBlank()) {
            finish()
            return
        }

        WXAPIFactory.createWXAPI(this, appId, false).handleIntent(intent, this)
    }

    override fun onReq(req: BaseReq?) {
        finish()
    }

    override fun onResp(resp: BaseResp?) {
        finish()
    }
}
