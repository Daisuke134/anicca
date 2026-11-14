import Foundation
import OSLog

/// One row per decision point, per the Phase 1 measurement contract in
/// `files/onboarding-answer-change-mapping-2026-11-14.md` and the
/// state-transition schema (1 row = 1 person × 1 decision point).
///
/// Two row kinds share this file:
/// - `decision`: made on device by `PersonalizedNudgeSelector`. Always
///   carries the exact `assignedProbability` of the chosen treatment
///   (required, never blank, never reconstructed afterwards).
/// - `outcome`: a later observation (delivered / opened / responded /
///   skipped) joined to its decision by `deliveryId`. For notifications
///   decided by the backend sender, the outcome row is the on-device half
///   of the record; the decision row lives with the sender.
///
/// Storage is on-device only (Application Support). Analytics receives IDs,
/// categories, and versions — never the user's name or free text.
struct DecisionPointRecord: Codable, Equatable {
    var recordKind: String              // "decision" | "outcome"
    var personId: String                // pseudonymous, device-generated UUID
    var deliveryId: String              // join key across decision + outcomes
    var decisionPointAt: String         // ISO-8601 UTC
    var available: Bool                 // user was available at the decision point
    var treatmentAssigned: String       // message id, or "do_not_send"
    var assignedProbability: Double?    // required on decision rows: 0 < p <= 1
    var messageId: String?
    var policyVersion: String
    var source: String                  // onboarding_first_intervention / notification / ...
    var desiredState: String?
    var painPointIds: [String]
    var struggleFrequency: String?
    var candidateCount: Int?
    var selectionReason: String?
    var proximalOutcome: String?        // nil = unobserved; delivered/opened/responded/skipped
    var outcomeWindowSec: Int
}

final class DecisionPointStore {
    static let shared = DecisionPointStore()

    private let queue = DispatchQueue(label: "com.anicca.decision-points")
    private let logger = Logger(subsystem: "com.anicca.ios", category: "DecisionPointStore")

    private var fileURL: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let dir = base.appendingPathComponent("Anicca", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("decision-points.jsonl")
    }

    private init() {}

    func append(_ record: DecisionPointRecord) {
        queue.sync {
            guard let data = try? JSONEncoder().encode(record),
                  let line = String(data: data, encoding: .utf8) else { return }
            let url = fileURL
            if let handle = try? FileHandle(forWritingTo: url) {
                defer { try? handle.close() }
                _ = try? handle.seekToEnd()
                try? handle.write(contentsOf: Data((line + "\n").utf8))
            } else {
                try? (line + "\n").write(to: url, atomically: true, encoding: .utf8)
            }
        }
    }

    func allRecords() -> [DecisionPointRecord] {
        queue.sync {
            guard let text = try? String(contentsOf: fileURL, encoding: .utf8) else { return [] }
            let decoder = JSONDecoder()
            return text.split(separator: "\n").compactMap { line in
                try? decoder.decode(DecisionPointRecord.self, from: Data(line.utf8))
            }
        }
    }

    /// Update the proximal outcome of the decision row for a delivery.
    /// Returns false when no decision row exists for the delivery (e.g. a
    /// backend-decided notification), so the caller can append an outcome
    /// row instead.
    @discardableResult
    func updateOutcome(deliveryId: String, outcome: String) -> Bool {
        queue.sync {
            var records = loadRecordsUnlocked()
            guard let index = records.lastIndex(where: { $0.deliveryId == deliveryId && $0.recordKind == "decision" }) else {
                return false
            }
            records[index].proximalOutcome = outcome
            rewriteUnlocked(records)
            return true
        }
    }

    /// message id → most recent decision time, for the selector's cooldown.
    func shownTimestamps() -> [String: Date] {
        let formatter = ISO8601DateFormatter()
        var result: [String: Date] = [:]
        for record in allRecords() where record.recordKind == "decision" {
            guard let messageId = record.messageId,
                  let date = formatter.date(from: record.decisionPointAt) else { continue }
            if let existing = result[messageId], existing > date { continue }
            result[messageId] = date
        }
        return result
    }

    private func loadRecordsUnlocked() -> [DecisionPointRecord] {
        guard let text = try? String(contentsOf: fileURL, encoding: .utf8) else { return [] }
        let decoder = JSONDecoder()
        return text.split(separator: "\n").compactMap { line in
            try? decoder.decode(DecisionPointRecord.self, from: Data(line.utf8))
        }
    }

    private func rewriteUnlocked(_ records: [DecisionPointRecord]) {
        let encoder = JSONEncoder()
        let text = records.compactMap { record -> String? in
            guard let data = try? encoder.encode(record) else { return nil }
            return String(data: data, encoding: .utf8)
        }.joined(separator: "\n")
        try? (text + (text.isEmpty ? "" : "\n")).write(to: fileURL, atomically: true, encoding: .utf8)
    }
}

@MainActor
final class DecisionPointRecorder {
    static let shared = DecisionPointRecorder()

    private let personIdKey = "com.anicca.decisionPersonId"
    private let outcomeWindowSec = 30 * 60

    private init() {}

    /// Stable pseudonymous id for decision records. Device-generated; not
    /// derived from the user's name or any account identifier.
    var personId: String {
        if let existing = UserDefaults.standard.string(forKey: personIdKey) {
            return existing
        }
        let created = UUID().uuidString
        UserDefaults.standard.set(created, forKey: personIdKey)
        return created
    }

    private func nowISO() -> String {
        ISO8601DateFormatter().string(from: Date())
    }

    /// Record an on-device selection (first intervention, plan preview).
    /// Returns the delivery id so later outcomes can join to this decision.
    @discardableResult
    func recordDecision(
        selection: PersonalizedNudgeSelector.Selection,
        profile: PersonalizationProfile,
        source: String
    ) -> String {
        let deliveryId = UUID().uuidString
        let record = DecisionPointRecord(
            recordKind: "decision",
            personId: personId,
            deliveryId: deliveryId,
            decisionPointAt: nowISO(),
            available: true,
            treatmentAssigned: selection.quote.id,
            assignedProbability: selection.assignedProbability,
            messageId: selection.quote.id,
            policyVersion: selection.policyVersion,
            source: source,
            desiredState: profile.desiredState,
            painPointIds: profile.painPointIds,
            struggleFrequency: profile.struggleFrequency,
            candidateCount: selection.candidateCount,
            selectionReason: selection.reason,
            proximalOutcome: nil,
            outcomeWindowSec: outcomeWindowSec
        )
        DecisionPointStore.shared.append(record)
        AnalyticsManager.shared.track(.nudgeDecisionMade, properties: [
            "delivery_id": deliveryId,
            "message_id": selection.quote.id,
            "category": selection.quote.categoryID,
            "assigned_probability": selection.assignedProbability,
            "policy_version": selection.policyVersion,
            "selection_reason": selection.reason,
            "source": source,
        ])
        return deliveryId
    }

    /// Record a notification outcome observed on device (foreground receipt,
    /// tap, dismiss). Joins to an on-device decision row when one exists;
    /// otherwise appends an outcome row keyed by the payload's delivery id.
    func recordNotificationOutcome(deliveryId: String, messageId: String?, outcome: String) {
        if DecisionPointStore.shared.updateOutcome(deliveryId: deliveryId, outcome: outcome) {
            return
        }
        let profile = AppState.shared.personalizationProfile
        let record = DecisionPointRecord(
            recordKind: "outcome",
            personId: personId,
            deliveryId: deliveryId,
            decisionPointAt: nowISO(),
            available: true,
            treatmentAssigned: messageId ?? "server_selected",
            assignedProbability: nil,
            messageId: messageId,
            policyVersion: "server",
            source: "notification",
            desiredState: profile.desiredState,
            painPointIds: profile.painPointIds,
            struggleFrequency: profile.struggleFrequency,
            candidateCount: nil,
            selectionReason: nil,
            proximalOutcome: outcome,
            outcomeWindowSec: outcomeWindowSec
        )
        DecisionPointStore.shared.append(record)
    }
}
