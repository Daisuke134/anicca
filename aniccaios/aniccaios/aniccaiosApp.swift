//
//  aniccaiosApp.swift
//  aniccaios
//
//  Created by CBNS03 on 2025/11/02.
//

import Combine
import SwiftUI

@main
struct aniccaiosApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var appState = AppState.shared

    var body: some Scene {
        WindowGroup {
            ContentRouterView()
                .environmentObject(appState)
                // v3: OSロケールに追従（locale overrideを撤廃）
                .tint(AppTheme.Colors.accent)
                .onAppear {
                    #if DEBUG
                    ScreenshotDebugManager.shared.configure()
                    #endif
                }
                .onOpenURL { url in
                    // Debug deep link for E2E: anicca://debug/pushTap?messageId=<uuid>
                    guard url.scheme == "anicca" else { return }
                    guard url.host == "debug" else { return }
                    guard url.path == "/pushTap" else { return }
                    guard let comps = URLComponents(url: url, resolvingAgainstBaseURL: false),
                          let messageId = comps.queryItems?.first(where: { $0.name == "messageId" })?.value,
                          !messageId.isEmpty else {
                        return
                    }
                    Task { @MainActor in
                        do {
                            let delivery = try await ProblemNudgeDeliveryService.shared.fetchDelivery(id: messageId)
                            if let problem = ProblemType(rawValue: delivery.problemType) {
                                let content = NudgeContent(
                                    problemType: problem,
                                    notificationText: delivery.hook,
                                    detailText: delivery.detail,
                                    variantIndex: delivery.variantIndex,
                                    isAIGenerated: false,
                                    llmNudgeId: nil
                                )
                                AppState.shared.showNudgeCard(content)
                            }
                        } catch {
                            print("deep link fetch failed: \(error)")
                        }
                    }
                }
        }
    }
}
