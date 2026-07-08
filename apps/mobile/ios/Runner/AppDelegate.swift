import Flutter
import UIKit
import WechatOpenSDK

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate, WXApiDelegate {
  private let wechatPayChannel = "lingban/wechat_pay"

  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    let channel = FlutterMethodChannel(
      name: wechatPayChannel,
      binaryMessenger: engineBridge.applicationRegistrar.messenger()
    )
    channel.setMethodCallHandler { call, result in
      switch call.method {
      case "requestPayment":
        self.requestPayment(arguments: call.arguments, result: result)
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }

  override func application(
    _ app: UIApplication,
    open url: URL,
    options: [UIApplication.OpenURLOptionsKey: Any] = [:]
  ) -> Bool {
    if WXApi.handleOpen(url, delegate: self) {
      return true
    }
    return super.application(app, open: url, options: options)
  }

  override func application(
    _ application: UIApplication,
    continue userActivity: NSUserActivity,
    restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
  ) -> Bool {
    if WXApi.handleOpenUniversalLink(userActivity, delegate: self) {
      return true
    }
    return super.application(
      application,
      continue: userActivity,
      restorationHandler: restorationHandler
    )
  }

  func onReq(_ req: BaseReq) {}

  func onResp(_ resp: BaseResp) {}

  private func requestPayment(arguments: Any?, result: @escaping FlutterResult) {
    guard let params = arguments as? [String: Any] else {
      result(
        FlutterError(
          code: "wechat_pay_invalid_params",
          message: "Missing WeChat Pay params.",
          details: nil
        )
      )
      return
    }

    guard
      let appId = stringParam(params["appid"]),
      let partnerId = stringParam(params["partnerid"]),
      let prepayId = stringParam(params["prepayid"]),
      let packageValue = stringParam(params["package"]),
      let nonceStr = stringParam(params["noncestr"]),
      let timestampText = stringParam(params["timestamp"]),
      let timestamp = UInt32(timestampText),
      let sign = stringParam(params["sign"])
    else {
      result(
        FlutterError(
          code: "wechat_pay_invalid_params",
          message: "Incomplete WeChat Pay params.",
          details: nil
        )
      )
      return
    }

    let universalLink = configuredString(forInfoKey: "WechatUniversalLink")
    if !WXApi.registerApp(appId, universalLink: universalLink) {
      result(
        FlutterError(
          code: "wechat_pay_registration_failed",
          message: "Failed to register WeChat app id.",
          details: nil
        )
      )
      return
    }

    if !WXApi.isWXAppInstalled() {
      result(
        FlutterError(
          code: "wechat_not_installed",
          message: "WeChat is not installed.",
          details: nil
        )
      )
      return
    }

    let request = PayReq()
    request.partnerId = partnerId
    request.prepayId = prepayId
    request.package = packageValue
    request.nonceStr = nonceStr
    request.timeStamp = timestamp
    request.sign = sign

    if WXApi.send(request) {
      result(true)
    } else {
      result(
        FlutterError(
          code: "wechat_pay_launch_failed",
          message: "Failed to launch WeChat Pay.",
          details: nil
        )
      )
    }
  }

  private func stringParam(_ value: Any?) -> String? {
    if let string = value as? String {
      let trimmed = string.trimmingCharacters(in: .whitespacesAndNewlines)
      return trimmed.isEmpty ? nil : trimmed
    }
    if let number = value as? NSNumber {
      return number.stringValue
    }
    return nil
  }

  private func configuredString(forInfoKey key: String) -> String {
    guard let value = Bundle.main.object(forInfoDictionaryKey: key) as? String else {
      return ""
    }
    if value.contains("$(") {
      return ""
    }
    return value.trimmingCharacters(in: .whitespacesAndNewlines)
  }
}
