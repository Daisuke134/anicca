import Foundation

/// ぽよ (Poyo) — Anicca's mascot. One character, one voice, every surface.
///
/// The WORDS are chosen by Manager (the model). Poyo only carries "who says it":
/// first-person voice, dry tone, and the face. This file is the face half:
/// which expression shows for which intervention context.
///
/// Canonical spec: anicca-ops `files/mascot-design-2026-11-22.md` (design),
/// `files/mascot-poyo-kit-2026-11-24.md` (kit), wiring spec §4 (mapping).
enum PoyoExpression: String, CaseIterable, Codable {
    case happy
    case sleepy
    case sad
    case excited
    case laughing

    /// Asset-catalog imageset name (must match `Assets.xcassets/Poyo*.imageset`).
    var imageName: String {
        switch self {
        case .happy: return "PoyoHappy"
        case .sleepy: return "PoyoSleepy"
        case .sad: return "PoyoSad"
        case .excited: return "PoyoExcited"
        case .laughing: return "PoyoLaughing"
        }
    }

    /// Filename (no extension) of the transparent expression PNG.
    /// Used for notification attachments exported to the App Group container.
    var fileName: String {
        switch self {
        case .happy: return "poyo-happy"
        case .sleepy: return "poyo-sleepy"
        case .sad: return "poyo-sad"
        case .excited: return "poyo-excited"
        case .laughing: return "poyo-laughing"
        }
    }

    /// Parse a remote payload value (`poyoExpression` in the push userInfo).
    /// Remote payloads win over the on-device selector (wiring spec §3.4):
    /// the generator already applied the §4 mapping, so the device must not
    /// decide twice.
    init?(payloadValue: String?) {
        guard let payloadValue,
              let parsed = PoyoExpression(rawValue: payloadValue.lowercased()) else {
            return nil
        }
        self = parsed
    }

    /// Wiring spec §4 mapping: intervention context + time of day → expression.
    ///
    /// - Parameters:
    ///   - interventionType: free-form intervention/context tag from the caller
    ///     (e.g. "bedtime", "wake_up", "rumination", "streak", "comedy").
    ///     Unknown or nil falls through to the time-of-day rules.
    ///   - hour: local hour 0–23.
    ///   - isReturningAfterAbsence: true when the user comes back after a long
    ///     absence. A return is ALWAYS `happy`, never `sad` — a reunion that
    ///     does not blame (spec §3). This exception wins over every other rule.
    static func select(interventionType: String?, hour: Int, isReturningAfterAbsence: Bool) -> PoyoExpression {
        if isReturningAfterAbsence { return .happy }

        let type = (interventionType ?? "").lowercased()

        // Comedy / celebration with a punchline.
        if type.contains("comedy") || type.contains("celebrat") || type.contains("laugh") {
            return .laughing
        }
        // Achievement, streaks, invitations to a new challenge.
        if type.contains("achiev") || type.contains("streak") || type.contains("challenge")
            || type.contains("milestone") || type.contains("excited") {
            return .excited
        }
        // Hard days, rumination, "just be with them" interventions.
        if type.contains("sad") || type.contains("ruminat") || type.contains("self_loathing")
            || type.contains("self-loathing") || type.contains("anxiety") || type.contains("hard_day")
            || type.contains("grief") || type.contains("lonely") {
            return .sad
        }
        // Night / rest / bedtime.
        if type.contains("bedtime") || type.contains("sleep") || type.contains("rest")
            || type.contains("night") {
            return .sleepy
        }

        // Time-of-day fallback: night and late evening are sleepy.
        if hour >= 22 || hour < 5 { return .sleepy }

        return .happy
    }
}

/// Animation STATE for Poyo on screen. Animation is code state, not video:
/// the view maps each state to an expression plus a small procedural motion
/// (breathing, bounce, sway, shake) rendered by SwiftUI.
enum PoyoState: String, CaseIterable {
    case idle
    case happy
    case waiting
    case thinking
    case error
    case celebrating

    /// Expression shown while in this state.
    var expression: PoyoExpression {
        switch self {
        case .idle: return .happy
        case .happy: return .happy
        case .waiting: return .sleepy
        case .thinking: return .happy
        case .error: return .sad
        case .celebrating: return .laughing
        }
    }

    /// State derived from an expression (e.g. home shows the selected face
    /// with its natural motion).
    static func from(expression: PoyoExpression) -> PoyoState {
        switch expression {
        case .happy: return .idle
        case .sleepy: return .waiting
        case .sad: return .error
        case .excited: return .happy
        case .laughing: return .celebrating
        }
    }
}

/// Tracks "long absence" for the no-blame reunion rule (spec §3):
/// returning after 3+ days counts as a return, and Poyo greets with `happy`.
enum PoyoPresence {
    static let lastSeenKey = "poyo.lastSeenAt"
    static let absenceThreshold: TimeInterval = 3 * 24 * 60 * 60

    static func isReturningAfterAbsence(now: Date, defaults: UserDefaults = .standard) -> Bool {
        guard let last = defaults.object(forKey: lastSeenKey) as? Date else { return false }
        return now.timeIntervalSince(last) >= absenceThreshold
    }

    static func markSeen(now: Date, defaults: UserDefaults = .standard) {
        defaults.set(now, forKey: lastSeenKey)
    }
}
