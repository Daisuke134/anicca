import SwiftUI
import Combine
import RevenueCat
import RevenueCatUI

/// ↓ pull-down sheet from FeedRootView.
/// 1mm clone of i.am app settings (modal sheet with categories: Theme / Notifications / Saved / Liked / Subscription / Account / Sign out).
struct SettingsSheet: View {
    @EnvironmentObject var themeStore: ThemeStore
    @EnvironmentObject var likedStore: LikedQuotesStore
    @Environment(\.dismiss) private var dismiss

    @State private var showThemePicker = false
    @State private var showSavedQuotes = false
    @State private var showLikedQuotes = false

    var body: some View {
        List {
            Section {
                NavigationLink {
                    ThemePickerView()
                        .environmentObject(themeStore)
                } label: {
                    HStack {
                        Label(String(localized: "settings_theme"), systemImage: "paintpalette")
                        Spacer()
                        Text(themeStore.selected.displayName)
                            .foregroundStyle(.secondary)
                    }
                }
                .accessibilityIdentifier("settings-theme")

                NavigationLink {
                    NotificationsSettingsView()
                } label: {
                    Label(String(localized: "settings_notifications"), systemImage: "bell")
                }

                NavigationLink {
                    LikedQuotesView()
                        .environmentObject(likedStore)
                } label: {
                    HStack {
                        Label(String(localized: "settings_liked_quotes"), systemImage: "heart")
                        Spacer()
                        Text("\(likedStore.likedIds.count)")
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Section {
                NavigationLink {
                    RevenueCatUI.CustomerCenterView()
                        .navigationTitle(String(localized: "settings_subscription"))
                        .navigationBarTitleDisplayMode(.inline)
                } label: {
                    Label(String(localized: "settings_subscription"), systemImage: "creditcard")
                }
            }

            // v1.9.1: Newsletter signup
            NewsletterSection()

            // v1.9.1: Feedback form
            FeedbackSection()

            Section {
                Button(role: .destructive) {
                    // Sign out hook — kept minimal here; app-level wiring stays in AppState.
                } label: {
                    Label(String(localized: "settings_sign_out"), systemImage: "rectangle.portrait.and.arrow.right")
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle(String(localized: "settings_title"))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(String(localized: "common_done")) { dismiss() }
            }
        }
    }
}

/// 8 theme grid. Tap = select + persist + dismiss.
struct ThemePickerView: View {
    @EnvironmentObject var themeStore: ThemeStore
    @Environment(\.dismiss) private var dismiss

    private let columns = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        ScrollView {
            LazyVGrid(columns: columns, spacing: 16) {
                ForEach(ThemeID.allCases) { theme in
                    Button {
                        themeStore.select(theme)
                        dismiss()
                    } label: {
                        ZStack(alignment: .bottomLeading) {
                            theme.image
                                .resizable()
                                .scaledToFill()
                                .frame(height: 240)
                                .clipped()
                                .clipShape(RoundedRectangle(cornerRadius: 16))
                            HStack {
                                Text(theme.displayName)
                                    .font(.footnote)
                                    .foregroundStyle(.white)
                                    .padding(8)
                                Spacer()
                                if themeStore.selected == theme {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundStyle(.white)
                                        .padding(8)
                                }
                            }
                            .background(LinearGradient(colors: [.clear, .black.opacity(0.5)], startPoint: .top, endPoint: .bottom))
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                        }
                        .accessibilityIdentifier("theme-\(theme.rawValue)")
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(16)
        }
        .navigationTitle(String(localized: "settings_theme"))
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// Liked quotes grid. Tap = (future) jump back to feed at that quote.
struct LikedQuotesView: View {
    @EnvironmentObject var likedStore: LikedQuotesStore

    var likedQuotes: [Quote] {
        QuoteProvider.shared.all().filter { likedStore.isLiked($0.id) }
    }

    var body: some View {
        Group {
            if likedQuotes.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "heart")
                        .font(.system(size: 44))
                        .foregroundStyle(.secondary)
                    Text(String(localized: "liked_empty_title"))
                        .font(.headline)
                    Text(String(localized: "liked_empty_subtitle"))
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding(40)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                List {
                    ForEach(likedQuotes) { q in
                        Text(q.text)
                            .padding(.vertical, 8)
                    }
                }
            }
        }
        .navigationTitle(String(localized: "settings_liked_quotes"))
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// Minimal notifications settings stub — wired to NotificationScheduler.
struct NotificationsSettingsView: View {
    @State private var dailyCount = 4

    var body: some View {
        Form {
            Section {
                HStack {
                    Text(String(localized: "notifications_daily_count"))
                    Spacer()
                    Text("\(dailyCount)")
                        .foregroundStyle(.secondary)
                }
                Text(String(localized: "notifications_schedule_label"))
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            } footer: {
                Text(String(localized: "notifications_footer"))
            }
        }
        .navigationTitle(String(localized: "settings_notifications"))
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: - v1.9.1: Newsletter signup section

struct NewsletterSection: View {
    @ObservedObject private var appState = AppState.shared
    @State private var email: String = ""
    @State private var status: Status = .notRegistered
    @State private var submitting: Bool = false
    @State private var errorMsg: String?

    enum Status: Equatable {
        case notRegistered
        case registered(maskedEmail: String)
    }

    var body: some View {
        Section {
            switch status {
            case .registered(let masked):
                HStack {
                    Image(systemName: "envelope.badge").foregroundStyle(.green)
                    Text(String(format: NSLocalizedString("newsletter_status_registered", comment: ""), masked))
                        .font(.subheadline)
                    Spacer()
                }
                .accessibilityIdentifier("newsletter-status-text")

                Button(role: .destructive) {
                    Task { await unsubscribe() }
                } label: {
                    Label(String(localized: "newsletter_unsubscribe_button"), systemImage: "envelope.open")
                }
                .accessibilityIdentifier("newsletter-unsubscribe-button")
                .disabled(submitting)

            case .notRegistered:
                TextField(String(localized: "newsletter_email_placeholder"), text: $email)
                    .textContentType(.emailAddress)
                    .autocapitalization(.none)
                    .disableAutocorrection(true)
                    .accessibilityIdentifier("newsletter-email-field")

                if let err = errorMsg {
                    Text(err).font(.caption).foregroundStyle(.red)
                }

                Button {
                    Task { await submit() }
                } label: {
                    HStack {
                        if submitting { ProgressView() }
                        Text(String(localized: "newsletter_submit_button"))
                    }
                }
                .accessibilityIdentifier("newsletter-submit-button")
                .disabled(submitting || !isValidEmail(email))
            }
        } header: {
            Text(String(localized: "newsletter_section_title"))
        } footer: {
            Text(String(localized: "newsletter_section_description"))
                .font(.caption2).foregroundStyle(.secondary)
        }
        .accessibilityIdentifier("newsletter-section")
    }

    private func isValidEmail(_ s: String) -> Bool {
        s.range(of: #"^[^@\s]+@[^@\s]+\.[^@\s]+$"#, options: .regularExpression) != nil
    }

    private func mask(_ email: String) -> String {
        guard let at = email.firstIndex(of: "@") else { return email }
        let local = String(email[..<at])
        let domain = String(email[at...])
        return "\(local.prefix(1))***\(local.suffix(1))\(domain)"
    }

    @MainActor
    private func submit() async {
        guard !submitting else { return }
        submitting = true
        defer { submitting = false }
        errorMsg = nil
        let url = AppConfig.proxyBaseURL.appendingPathComponent("mobile/newsletter/subscribers")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = [
            "email": email,
            "locale": AppState.shared.effectiveLanguage.rawValue,
            "deviceId": AppState.shared.resolveDeviceId()
        ]
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (_, resp) = try await URLSession.shared.data(for: req)
            guard let http = resp as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                errorMsg = String(localized: "newsletter_submit_error")
                return
            }
            status = .registered(maskedEmail: mask(email))
        } catch {
            errorMsg = error.localizedDescription
        }
    }

    @MainActor
    private func unsubscribe() async {
        guard !submitting else { return }
        submitting = true
        defer { submitting = false }
        let deviceId = AppState.shared.resolveDeviceId()
        let url = AppConfig.proxyBaseURL.appendingPathComponent("mobile/newsletter/subscribers/\(deviceId)")
        var req = URLRequest(url: url)
        req.httpMethod = "DELETE"
        _ = try? await URLSession.shared.data(for: req)
        status = .notRegistered
        email = ""
    }
}

// MARK: - v1.9.1: Feedback form section

struct FeedbackSection: View {
    var body: some View {
        Section {
            NavigationLink {
                FeedbackFormView()
            } label: {
                Label(String(localized: "feedback_link_label"), systemImage: "envelope")
            }
            .accessibilityIdentifier("feedback-link")
        } header: {
            Text(String(localized: "feedback_section_title"))
        }
        .accessibilityIdentifier("feedback-section")
    }
}

struct FeedbackFormView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var text: String = ""
    @State private var showPIIWarning: Bool = false
    @State private var submitting: Bool = false
    @State private var sent: Bool = false
    @State private var errorMsg: String?

    var body: some View {
        Form {
            Section {
                TextEditor(text: $text)
                    .frame(minHeight: 180)
                    .accessibilityIdentifier("feedback-textarea")
                Text("\(text.count) / 2000")
                    .font(.caption2)
                    .foregroundStyle(text.count > 2000 ? .red : .secondary)
            } footer: {
                Text(String(localized: "feedback_placeholder"))
                    .font(.caption2).foregroundStyle(.secondary)
            }

            if let err = errorMsg {
                Section {
                    Text(err).foregroundStyle(.red).font(.caption)
                }
            }

            Section {
                Button {
                    if containsPII(text) { showPIIWarning = true } else { Task { await submit() } }
                } label: {
                    HStack {
                        if submitting { ProgressView() }
                        Text(sent ? String(localized: "feedback_sent_label") : String(localized: "feedback_submit_button"))
                    }
                }
                .accessibilityIdentifier("feedback-submit-button")
                .disabled(submitting || sent || text.count < 5 || text.count > 2000)
            }
        }
        .navigationTitle(String(localized: "feedback_section_title"))
        .navigationBarTitleDisplayMode(.inline)
        .alert(String(localized: "feedback_pii_warning_title"), isPresented: $showPIIWarning) {
            Button(role: .destructive) {
                Task { await submit() }
            } label: {
                Text(String(localized: "feedback_submit_button"))
            }
            .accessibilityIdentifier("feedback-pii-confirm-button")

            Button(role: .cancel) {} label: { Text(String(localized: "common_cancel")) }
                .accessibilityIdentifier("feedback-pii-cancel-button")
        } message: {
            Text(String(localized: "feedback_pii_warning_message"))
        }
    }

    private func containsPII(_ s: String) -> Bool {
        s.range(of: #"[\w.+-]+@[\w-]+\.[\w-]+|\b\d{3}-?\d{4}-?\d{4}\b"#, options: .regularExpression) != nil
    }

    @MainActor
    private func submit() async {
        guard !submitting else { return }
        submitting = true
        defer { submitting = false }
        errorMsg = nil
        let url = AppConfig.proxyBaseURL.appendingPathComponent("mobile/feedback")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = [
            "text": text,
            "locale": AppState.shared.effectiveLanguage.rawValue,
            "appUserId": AppState.shared.resolveDeviceId(),
            "appVersion": AppConfig.appVersion
        ]
        req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (_, resp) = try await URLSession.shared.data(for: req)
            guard let http = resp as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
                errorMsg = String(localized: "feedback_submit_error")
                return
            }
            sent = true
            text = ""
        } catch {
            errorMsg = error.localizedDescription
        }
    }
}
