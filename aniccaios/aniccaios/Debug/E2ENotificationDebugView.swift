import SwiftUI
import UserNotifications

#if DEBUG

/// Maestro-friendly E2E panel for verifying "server nudge -> local notification scheduled".
/// This intentionally avoids interacting with Notification Center UI (system-level),
/// and instead asserts the pending request exists (stable for automation).
struct E2ENotificationDebugView: View {
    @State private var pendingCount: Int = 0
    @State private var deliveredCount: Int = 0
    @State private var lastPendingId: String = ""
    @State private var lastDeliveredId: String = ""
    @State private var deviceId: String = ""
    @State private var lastError: String? = nil
    @State private var isRunning: Bool = false

    var body: some View {
        let scheduled = (pendingCount + deliveredCount) > 0
        VStack(spacing: 16) {
            Text("E2E: Server Nudge -> Local Notification")
                .font(.headline)
                .accessibilityIdentifier("e2e-notif-title")

            HStack {
                Text("Pending: \(pendingCount)")
                    .accessibilityIdentifier("e2e-notif-pending-count")
                Spacer()
            }

            HStack {
                Text("Delivered: \(deliveredCount)")
                    .accessibilityIdentifier("e2e-notif-delivered-count")
                Spacer()
            }

            // Keep this as deterministic text so Maestro can assert scheduling without parsing numbers.
            HStack {
                Text(scheduled ? "Scheduled: YES" : "Scheduled: NO")
                    .accessibilityIdentifier("e2e-notif-scheduled-flag")
                Spacer()
            }

            HStack {
                Text("Last ID: \(lastPendingId)")
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .accessibilityIdentifier("e2e-notif-last-id")
                Spacer()
            }

            HStack {
                Text("Last Delivered ID: \(lastDeliveredId)")
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .accessibilityIdentifier("e2e-notif-last-delivered-id")
                Spacer()
            }

            HStack {
                Text("Device ID: \(deviceId)")
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .font(.caption)
                    .accessibilityIdentifier("e2e-device-id")
                Spacer()
            }

            if let lastError {
                Text("Error: \(lastError)")
                    .foregroundStyle(.red)
                    .font(.caption)
                    .accessibilityIdentifier("e2e-notif-error")
            }

            Button {
                Task { await requestNotifications() }
            } label: {
                Text("Request Notifications Permission")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .accessibilityIdentifier("e2e-request-notif-permission")

            Button {
                Task { await triggerServerNudge() }
            } label: {
                HStack {
                    if isRunning { ProgressView().scaleEffect(0.9) }
                    Text("Trigger /mobile/nudge/trigger (e2e_pause)")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(isRunning)
            .accessibilityIdentifier("e2e-trigger-server-nudge")

            Button {
                Task { await fetchPendingServerNudges() }
            } label: {
                HStack {
                    if isRunning { ProgressView().scaleEffect(0.9) }
                    Text("Fetch /mobile/nudge/pending (send_nudge inbox)")
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .disabled(isRunning)
            .accessibilityIdentifier("e2e-fetch-pending-server-nudges")

            Button {
                Task { await refreshPending() }
            } label: {
                Text("Refresh Pending Requests")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .accessibilityIdentifier("e2e-refresh-pending")

            Button(role: .destructive) {
                Task { await clearPending() }
            } label: {
                Text("Clear Pending Requests")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.bordered)
            .accessibilityIdentifier("e2e-clear-pending")

            Spacer()
        }
        .padding()
        .navigationTitle("E2E Notifications")
        .task {
            deviceId = AppState.shared.resolveDeviceId()
            await refreshPending()
        }
    }

    private func requestNotifications() async {
        lastError = nil
        _ = await NotificationScheduler.shared.requestAuthorizationIfNeeded()
        await refreshPending()
    }

    private func triggerServerNudge() async {
        lastError = nil
        isRunning = true
        defer { isRunning = false }

        await NudgeTriggerService.shared.trigger(eventType: .e2ePause)

        // Give scheduler time to register the pending request.
        try? await Task.sleep(nanoseconds: 2_000_000_000)
        await refreshPending()
    }

    private func refreshPending() async {
        let (pending, delivered) = await fetchPendingAndDelivered()
        pendingCount = pending.count
        deliveredCount = delivered.count
        lastPendingId = pending.map(\.identifier).last ?? ""
        lastDeliveredId = delivered.map(\.request.identifier).last ?? ""
    }

    private func fetchPendingServerNudges() async {
        lastError = nil
        isRunning = true
        defer { isRunning = false }

        // Force a poll now; this schedules local notifications and then acks.
        await ServerNudgeInboxService.shared.pullAndScheduleIfAuthorized(force: true)

        try? await Task.sleep(nanoseconds: 1_000_000_000)
        await refreshPending()
    }

    private func clearPending() async {
        UNUserNotificationCenter.current().removeAllPendingNotificationRequests()
        UNUserNotificationCenter.current().removeAllDeliveredNotifications()
        try? await Task.sleep(nanoseconds: 300_000_000)
        await refreshPending()
    }

    private func fetchPendingAndDelivered() async -> ([UNNotificationRequest], [UNNotification]) {
        async let pending: [UNNotificationRequest] = withCheckedContinuation { cont in
            UNUserNotificationCenter.current().getPendingNotificationRequests { reqs in
                cont.resume(returning: reqs)
            }
        }
        async let delivered: [UNNotification] = withCheckedContinuation { cont in
            UNUserNotificationCenter.current().getDeliveredNotifications { notifs in
                cont.resume(returning: notifs)
            }
        }
        return await (pending, delivered)
    }
}

#endif
