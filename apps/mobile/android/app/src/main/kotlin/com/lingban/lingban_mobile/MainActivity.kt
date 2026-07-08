package com.lingban.lingban_mobile

import android.content.Context
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import com.tencent.mm.opensdk.constants.Build
import com.tencent.mm.opensdk.modelpay.PayReq
import com.tencent.mm.opensdk.openapi.WXAPIFactory

class MainActivity : FlutterActivity() {
    private val wechatPayChannel = "lingban/wechat_pay"

    companion object {
        const val WECHAT_PAY_PREFS = "lingban_wechat_pay"
        const val WECHAT_APP_ID_KEY = "wechat_app_id"
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(
            flutterEngine.dartExecutor.binaryMessenger,
            wechatPayChannel
        ).setMethodCallHandler { call, result ->
            when (call.method) {
                "requestPayment" -> requestPayment(call.arguments, result)
                else -> result.notImplemented()
            }
        }
    }

    private fun requestPayment(arguments: Any?, result: MethodChannel.Result) {
        val params = arguments as? Map<*, *>
        if (params == null) {
            result.error("wechat_pay_invalid_params", "Missing WeChat Pay params.", null)
            return
        }

        val appId = stringParam(params, "appid")
        val partnerId = stringParam(params, "partnerid")
        val prepayId = stringParam(params, "prepayid")
        val packageValue = stringParam(params, "package")
        val nonceStr = stringParam(params, "noncestr")
        val timestamp = stringParam(params, "timestamp")
        val sign = stringParam(params, "sign")

        if (
            appId == null ||
            partnerId == null ||
            prepayId == null ||
            packageValue == null ||
            nonceStr == null ||
            timestamp == null ||
            sign == null
        ) {
            result.error("wechat_pay_invalid_params", "Incomplete WeChat Pay params.", null)
            return
        }

        val api = WXAPIFactory.createWXAPI(this, appId, true)
        api.registerApp(appId)
        getSharedPreferences(WECHAT_PAY_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(WECHAT_APP_ID_KEY, appId)
            .apply()

        if (!api.isWXAppInstalled) {
            result.error("wechat_not_installed", "WeChat is not installed.", null)
            return
        }
        if (api.wxAppSupportAPI < Build.PAY_SUPPORTED_SDK_INT) {
            result.error("wechat_pay_not_supported", "WeChat Pay is not supported.", null)
            return
        }

        val request = PayReq().apply {
            this.appId = appId
            this.partnerId = partnerId
            this.prepayId = prepayId
            this.packageValue = packageValue
            this.nonceStr = nonceStr
            this.timeStamp = timestamp
            this.sign = sign
            this.signType = stringParam(params, "sign_type") ?: "RSA"
        }

        if (api.sendReq(request)) {
            result.success(true)
        } else {
            result.error("wechat_pay_launch_failed", "Failed to launch WeChat Pay.", null)
        }
    }

    private fun stringParam(params: Map<*, *>, key: String): String? {
        val value = params[key] ?: return null
        return value.toString().takeIf { it.isNotBlank() }
    }
}
