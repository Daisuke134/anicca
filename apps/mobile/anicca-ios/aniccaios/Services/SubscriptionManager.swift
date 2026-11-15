import RevenueCat
import Foundation
import AdSupport
import StoreKit

@MainActor
final class SubscriptionManager: NSObject {
    static let shared = SubscriptionManager()
    private static let aniccaFallbackOfferingIdentifier = "anicca_variant_b"
    private var offerings: Offerings?
    private var offeringsRefreshGeneration = 0
    private(set) var isConfigured = false
    private var customerInfoTask: Task<Void, Never>?
    private var syncInFlight = false
    private var backendSyncInFlight = false
    private var identityTask: Task<Void, Never>?
    private var pendingPromotedPurchases: [(StoreProduct, StartPurchaseBlock)] = []

    private var identityMatchesSession: Bool {
        guard isConfigured else { return false }
        if let userID = AppState.shared.authStatus.userId {
            return Purchases.shared.appUserID == userID
        }
        return Purchases.shared.isAnonymous
    }


    private override init() {
        super.init()
    }

    func configure() {
        guard !isConfigured else { return }
        // UIテストモード時はRevenueCat初期化をスキップ（CIシミュレータでApple IDダイアログを防止）
        let launchArguments = ProcessInfo.processInfo.arguments
        if launchArguments.contains("UITESTING") || launchArguments.contains("-UITESTING") {
            print("[RevenueCat] Skipped - UI testing mode")
            return
        }

        Purchases.logLevel = .info // .debugから変更（JWS tokenの長いログを抑制）
        let apiKey = AppConfig.revenueCatAPIKey
        
        // V2/StoreKit 2対応のシンプル構成
        // entitlementVerificationMode: .informational は推奨設定（検証結果を情報として提供）
        // 言語設定は自動検出されるため明示的な設定は不要
        Purchases.configure(
            with: Configuration.Builder(withAPIKey: apiKey)
                .with(appUserID: AppState.shared.authStatus.userId)
                .with(purchasesAreCompletedBy: .revenueCat, storeKitVersion: .storeKit2)
                .with(showStoreMessagesAutomatically: true)
                .with(entitlementVerificationMode: .informational)
                .build()
        )
        
        Purchases.shared.delegate = self

        // RevenueCat → Singular 連携に必須
        // $idfa（ATT なしの場合は all-zeros）と $idfv を RevenueCat に渡す
        // これがないと RevenueCat → Singular にイベントが送信されない
        Purchases.shared.attribution.collectDeviceIdentifiers()

        // 起動直後にSDKキャッシュのOfferingをAppStateへプリロード
        if let cached = Purchases.shared.cachedOfferings,
           let preloaded = Self.resolveAniccaOffering(from: cached) {
            print("[SubscriptionManager] Pre-loading cached Anicca offering: \(preloaded.identifier)")
            AppState.shared.updateOffering(preloaded)
        }
        
        isConfigured = true

        // RevenueCat owns the transaction listener and finishing after receipt delivery.
        // Keep the entitlement listener alive regardless of onboarding or paywall visibility.
        customerInfoTask = Task { await listenCustomerInfo() }
        Task {
            _ = await refreshOfferings()
            await syncNow()
        }
    }

    private func listenCustomerInfo() async {
        for await info in Purchases.shared.customerInfoStream {
            guard identityMatchesSession else { continue }
            AppState.shared.updateSubscriptionInfo(SubscriptionInfo(info: info))
        }
    }

    private func syncUsageInfo(_ subscription: inout SubscriptionInfo) async {
        // v0.5.1: 匿名ユーザーでも利用量情報を同期
        let deviceId = AppState.shared.resolveDeviceId()
        let userId: String
        if case .signedIn(let credentials) = AppState.shared.authStatus {
            userId = credentials.userId
        } else {
            userId = deviceId
        }
        
        var request = URLRequest(url: AppConfig.entitlementSyncURL)
        request.httpMethod = "GET"
        request.setValue(deviceId, forHTTPHeaderField: "device-id")
        request.setValue(userId, forHTTPHeaderField: "user-id")
        
        do {
            let (data, response) = try await NetworkSessionManager.shared.session.data(for: request)
            
            guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                print("[SubscriptionManager] Server sync failed (status \( (response as? HTTPURLResponse)?.statusCode ?? 0 )), proceeding with RC data.")
                return
            }
            
            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let entitlement = json["entitlement"] as? [String: Any] {
                // 重要: 利用量情報のみを更新し、エンタイトルメント状態（plan, status）は上書きしない
                subscription.monthlyUsageLimit = entitlement["monthly_usage_limit"] as? Int
                subscription.monthlyUsageRemaining = entitlement["monthly_usage_remaining"] as? Int
                subscription.monthlyUsageCount = entitlement["monthly_usage_count"] as? Int
                
                print("[SubscriptionManager] Synced usage info only (plan/status unchanged): limit=\(subscription.monthlyUsageLimit ?? -1)")
            }
        } catch {
            print("[SubscriptionManager] Sync error: \(error). Using RC entitlement only.")
        }
    }
    
    func handleLogin(appUserId: String) async {
        await updateIdentity(appUserId: appUserId)
        startPendingPromotedPurchases()
    }

    func handleLogout() async {
        await updateIdentity(appUserId: nil)
        startPendingPromotedPurchases()
    }

    private func updateIdentity(appUserId: String?) async {
        guard isConfigured else { return }
        let previous = identityTask
        let task = Task { @MainActor in
            await previous?.value
            guard AppState.shared.authStatus.userId == appUserId else { return }
            do {
                let info: CustomerInfo
                if let appUserId {
                    if Purchases.shared.appUserID == appUserId { return }
                    info = try await Purchases.shared.logIn(appUserId).customerInfo
                } else {
                    guard !Purchases.shared.isAnonymous else { return }
                    info = try await Purchases.shared.logOut()
                }
                guard AppState.shared.authStatus.userId == appUserId else { return }
                AppState.shared.updateSubscriptionInfo(SubscriptionInfo(info: info))
            } catch {
                // Retry on foreground; never discard the anonymous purchase identity.
                print("[RevenueCat] Identity update failed")
            }
        }
        identityTask = task
        await task.value
    }

    private static func resolveAniccaOffering(from offerings: Offerings) -> Offering? {
        PaywallOfferingSelection.resolve(
            current: offerings.current,
            all: offerings.all,
            fallbackIdentifier: aniccaFallbackOfferingIdentifier,
            isUsableForAnicca: { offering in
                let packages = offering.availablePackages
                return PaywallOfferingSelection.isUsableAnicca(
                    productIdentifiers: packages.map { $0.storeProduct.productIdentifier },
                    hasAnnualOrMonthlyPackage: packages.contains { $0.packageType == .annual || $0.packageType == .monthly }
                )
            },
            identifier: { offering in offering.identifier }
        )
    }

    @discardableResult
    func refreshOfferings() async -> Bool {
        guard isConfigured else { return false }
        offeringsRefreshGeneration += 1
        let requestID = offeringsRefreshGeneration
        AppState.shared.updateOffering(AppState.shared.cachedOffering)
        let requestStorefrontCountryCode = (await Storefront.current)?.countryCode
        AppState.shared.recordStorefrontCountryCode(requestStorefrontCountryCode)
        let requestStorefrontRevision = AppState.shared.storefrontRevision
        do {
            let result = try await Purchases.shared.offerings()
            let latestStorefrontCountryCode = (await Storefront.current)?.countryCode
            AppState.shared.recordStorefrontCountryCode(latestStorefrontCountryCode)
            guard PaywallOfferingSelection.isLatestRefresh(
                requestID: requestID,
                currentRequestID: offeringsRefreshGeneration
            ) else { return false }
            guard PaywallOfferingSelection.isUnchangedStorefrontRevision(
                startingRevision: requestStorefrontRevision,
                currentRevision: AppState.shared.storefrontRevision
            ) else { return false }
            guard PaywallStorefrontEligibility.sameStorefront(
                first: requestStorefrontCountryCode,
                second: latestStorefrontCountryCode
            ) else { return false }

            let aniccaOffering = Self.resolveAniccaOffering(from: result)
            print("[SubscriptionManager] Offerings loaded: current=\(result.current?.identifier ?? "nil"), selected=\(aniccaOffering?.identifier ?? "nil"), all=\(result.all.keys.joined(separator: ", "))")
            offerings = result
            AppState.shared.updateOffering(aniccaOffering, storefrontCountryCode: aniccaOffering == nil ? nil : requestStorefrontCountryCode)
            return aniccaOffering != nil
        } catch {
            guard PaywallOfferingSelection.isLatestRefresh(
                requestID: requestID,
                currentRequestID: offeringsRefreshGeneration
            ) else { return false }
            // Keep existing cached offering on error, but its storefront remains unverified.
            if AppState.shared.cachedOffering == nil {
                AppState.shared.updateOffering(nil)
            }
            return false
        }
    }

    func refreshCustomerInfo() async -> Bool? {
        guard isConfigured else { return nil }
        do {
            let userID = Purchases.shared.appUserID
            let customerInfo = try await Purchases.shared.customerInfo(fetchPolicy: .fetchCurrent)
            guard identityMatchesSession, Purchases.shared.appUserID == userID else { return nil }
            let subscription = SubscriptionInfo(info: customerInfo)
            AppState.shared.updateSubscriptionInfo(subscription)
            return subscription.isEntitled
        } catch {
            print("[SubscriptionManager] CustomerInfo refresh failed")
            return nil
        }
    }
    
    func syncNow() async {
        guard isConfigured, !syncInFlight else { return }
        syncInFlight = true
        defer { syncInFlight = false }
        await updateIdentity(appUserId: AppState.shared.authStatus.userId)
        guard identityMatchesSession else { return }
        startPendingPromotedPurchases()
        let userID = Purchases.shared.appUserID
        do {
            let info = try await Purchases.shared.syncPurchases()
            guard identityMatchesSession, Purchases.shared.appUserID == userID else { return }
            AppState.shared.updateSubscriptionInfo(SubscriptionInfo(info: info))
        } catch {
            // SDK retains unfinished transactions; the next foreground retries.
            print("[SubscriptionManager] Purchase reconciliation unavailable")
            _ = await refreshCustomerInfo()
        }
        await syncBackendUsage()
    }

    private func syncBackendUsage() async {
        guard identityMatchesSession, !backendSyncInFlight else { return }
        backendSyncInFlight = true
        defer { backendSyncInFlight = false }
        // 2) サーバにRC再取得を要求（DB→/mobile/entitlement反映）
        // 重要(1.6.3): "通常状態ユーザー（= ほぼ全員）" でもサーバがPro/Freeを判定できるようにする。
        // - RevenueCatの購読状態は端末内では分かるが、APNs配信量はサーバが決めるため、サーバ側SSOT(user_subscriptions)の更新が必要。
        // - ここでは Sign in with Apple の userId ではなく、RevenueCatの appUserID を SSOT の鍵として送る。
        //   backendは device-id から profileId(UUID) を解決して user_subscriptions(user_id=profileId) を更新する。
        let deviceId = AppState.shared.resolveDeviceId()
        let revenueCatAppUserId = Purchases.shared.appUserID.trimmingCharacters(in: .whitespacesAndNewlines)
        let userIdHeader = revenueCatAppUserId.isEmpty ? deviceId : revenueCatAppUserId

        var request = URLRequest(url: AppConfig.proxyBaseURL.appendingPathComponent("billing/revenuecat/sync"))
        request.httpMethod = "POST"
        request.timeoutInterval = 10.0 // 10秒でタイムアウト
        request.setValue(deviceId, forHTTPHeaderField: "device-id")
        request.setValue(userIdHeader, forHTTPHeaderField: "user-id")
        
        do {
            let (_, response) = try await NetworkSessionManager.shared.session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                print("[SubscriptionManager] Invalid response type")
                return
            }
            
            if !(200..<300).contains(httpResponse.statusCode) {
                print("[SubscriptionManager] Sync failed with status: \(httpResponse.statusCode)")
                return
            }
            
            // 3) 最新Entitlementを取得
            var subscription = AppState.shared.subscriptionInfo
            await syncUsageInfo(&subscription)
            guard identityMatchesSession, Purchases.shared.appUserID == revenueCatAppUserId else { return }
            // The response contains usage only. Never restore an older entitlement snapshot.
            var current = AppState.shared.subscriptionInfo
            current.monthlyUsageLimit = subscription.monthlyUsageLimit
            current.monthlyUsageRemaining = subscription.monthlyUsageRemaining
            current.monthlyUsageCount = subscription.monthlyUsageCount
            AppState.shared.updateSubscriptionInfo(current)
        } catch {
            print("[SubscriptionManager] Sync error: \(error.localizedDescription)")
            // エラーでも続行（オフライン時など）
        }
    }
}

extension SubscriptionManager: PurchasesDelegate {
    func purchases(_ purchases: Purchases, receivedUpdated customerInfo: CustomerInfo) {
        print("[RevenueCat] Delegate received update. Active entitlements: \(customerInfo.entitlements.active.keys)")
        
        let userID = purchases.appUserID
        Task { @MainActor in
            guard identityMatchesSession, Purchases.shared.appUserID == userID else { return }
            let subscription = SubscriptionInfo(info: customerInfo)
            
            // 1. まずRevenueCatの情報だけで即座に更新（待機なし）
            AppState.shared.updateSubscriptionInfo(subscription)
            
            // CustomerInfo updates also occur on restore/refresh/renewal. They
            // are entitlement state, not new purchase or client revenue events.
            
            // 3. サーバーDBを同期してからlimit情報を取得（POSTでDB更新→GET）
            await syncBackendUsage()
        }
    }
    
    // 追加: アプリ内課金のプロモーション対応（ベストプラクティス）
    func purchases(_ purchases: Purchases, readyForPromotedProduct product: StoreProduct, purchase: @escaping StartPurchaseBlock) {
        pendingPromotedPurchases.append((product, purchase))
        Task { @MainActor in
            await updateIdentity(appUserId: AppState.shared.authStatus.userId)
            startPendingPromotedPurchases()
        }
    }

    private func startPendingPromotedPurchases() {
        // Preserve the continuation across identity failures; foreground reconciliation retries.
        guard identityMatchesSession else { return }
        let pending = pendingPromotedPurchases
        pendingPromotedPurchases.removeAll()
        for (product, purchase) in pending {
            let userID = Purchases.shared.appUserID
            purchase { _, info, error, cancelled in
                Task { @MainActor in
                    let outcome: String
                    if cancelled {
                        outcome = "cancelled"
                    } else if let error {
                        outcome = (error as NSError).code == ErrorCode.paymentPendingError.rawValue ? "pending" : "failed"
                    } else if let info {
                        guard self.identityMatchesSession, Purchases.shared.appUserID == userID else {
                            await self.syncNow()
                            return
                        }
                        AppState.shared.updateSubscriptionInfo(SubscriptionInfo(info: info))
                        outcome = SubscriptionInfo(info: info).isEntitled ? "granted" : "not_entitled"
                        await self.syncBackendUsage()
                    } else {
                        outcome = "pending"
                    }
                    AnalyticsManager.shared.track(.storePurchaseResult, properties: [
                        "result": outcome, "product_id": product.productIdentifier,
                        "source": "promoted_product"
                    ])
                }
            }
        }
    }
}

@MainActor
extension SubscriptionInfo {
    init(info: CustomerInfo) {
        let configuredId = AppConfig.revenueCatEntitlementId
        let primaryEntitlement = info.entitlements[configuredId]
        let fallbackEntitlement = info.entitlements.active.values.first
        let entitlement = primaryEntitlement ?? fallbackEntitlement

        let plan: Plan
        if entitlement?.isActive == true {
            plan = .pro
        } else if let expiration = entitlement?.expirationDate,
                  expiration > Date() {
            plan = .grace
        } else {
            plan = .free
        }

        let productId = entitlement?.productIdentifier
        let offering = AppState.shared.cachedOffering
        let package = offering?
            .availablePackages
            .first(where: { $0.storeProduct.productIdentifier == productId })

        let mappedName: String? = {
            switch productId {
            case "ai.anicca.app.ios.monthly":
                return NSLocalizedString("subscription_plan_monthly", comment: "")
            default:
                return nil
            }
        }()

        let willRenew = entitlement?.willRenew ?? false
        // 2026-06-23: 買い切り(lifetime)は willRenew=false でも有効なので "active" 扱い
        let isLifetime = productId == "ai.anicca.app.ios.lifetime"
        let isTrial = entitlement?.periodType == .trial
        let statusString: String
        if entitlement?.isActive == true {
            statusString = isTrial ? "trialing" : (willRenew || isLifetime ? "active" : "canceled")
        } else {
            statusString = "expired"
        }
        self.init(
            plan: plan,
            status: statusString,
            currentPeriodEnd: entitlement?.expirationDate,
            managementURL: info.managementURL,
            lastSyncedAt: .now,
            productIdentifier: productId,
            // OS言語に合わせたローカライズを優先（4.0対策: アプリの現在のローカライズに合わせる）
            // mappedNameはNSLocalizedStringでOS言語に応じて適切に翻訳される
            planDisplayName: mappedName ?? package?.storeProduct.localizedTitle,
            priceDescription: package?.localizedPriceString,
            monthlyUsageLimit: nil,
            monthlyUsageRemaining: nil,
            monthlyUsageCount: nil,
            willRenew: willRenew
        )
    }
}
