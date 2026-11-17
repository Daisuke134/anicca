import Foundation
import UserNotifications

/// Uses the existing authenticated proxy, never a model/provider secret in the app.
/// The proxy must mount models/manager/product/http_api.py; absent wiring fails closed.
@MainActor
final class ManagerInterventionService {
    static let shared = ManagerInterventionService()
    private struct PendingDecision: Codable {
        let deliveryId: String
        let context: [String: String]
    }
    private struct Observation: Codable, Equatable {
        let deliveryId: String
        let event: String
        let observedAt: Double
    }
    private struct Journal: Codable {
        var moments: [String: String] = [:]
        var submitted: [String] = []
        var pending: [String: PendingDecision] = [:]
        var decisions: [ManagerDecision] = []
        var observations: [Observation] = []
    }
    private var journal: Journal
    private var inFlight = Set<String>()
    private var flushing = false
    private var generation = 0
    private let url: URL
    private let encoder: JSONEncoder = {
        let value = JSONEncoder(); value.keyEncodingStrategy = .convertToSnakeCase; return value
    }()
    private let decoder: JSONDecoder = {
        let value = JSONDecoder(); value.keyDecodingStrategy = .convertFromSnakeCase; return value
    }()

    private init() {
        url = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("manager-interventions.json")
        journal = (try? Data(contentsOf: url)).flatMap { try? JSONDecoder().decode(Journal.self, from: $0) } ?? Journal()
    }

    private func persist() throws {
        try FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
        try JSONEncoder().encode(journal).write(to: url, options: [.atomic, .completeFileProtectionUntilFirstUserAuthentication])
    }

    func clearLocal() {
        generation += 1
        journal = Journal()
        try? FileManager.default.removeItem(at: url)
    }

    func momentID(for key: String) throws -> String {
        if let existing = journal.moments[key] { return existing }
        let id = UUID().uuidString
        journal.moments[key] = id
        try persist()
        return id
    }

    private func request<T: Encodable>(_ path: String, body: T) async throws -> Data {
        var request = URLRequest(url: AppConfig.proxyBaseURL.appendingPathComponent("manager/" + path))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try encoder.encode(body)
        try await NetworkSessionManager.shared.setAuthHeaders(for: &request)
        let (data, response) = try await NetworkSessionManager.shared.session.data(for: request)
        guard let response = response as? HTTPURLResponse, (200..<300).contains(response.statusCode) else {
            throw AniccaAPIError.serviceUnavailable
        }
        return data
    }

    /// Stable moment IDs survive process death and ambiguous HTTP responses.
    /// No-send is a durable decision, not a reason to draw again.
    func decide(source: String, moment: String) async throws -> ManagerDecision? {
        if let existing = journal.decisions.first(where: { $0.deliveryId == moment }) { return existing }
        guard !inFlight.contains(moment) else { return nil }
        inFlight.insert(moment)
        defer { inFlight.remove(moment) }
        let epoch = generation
        let context = [
            "time_band": PersonalizedNudgeSelector.TimeBand.band(forHour: Calendar.current.component(.hour, from: Date())).rawValue,
            "language": AppState.shared.effectiveLanguage.rawValue,
            "desired_state": AppState.shared.personalizationProfile.desiredState ?? "unknown",
            "source": source
        ]
        if journal.pending[moment] == nil {
            journal.pending[moment] = PendingDecision(deliveryId: moment, context: context)
        }
        try persist() // Never send a request whose retry ID was not saved.
        let pending = journal.pending[moment]!
        let data = try await request("decisions", body: pending)
        guard generation == epoch else { return nil }
        let decision = try decoder.decode(ManagerDecision.self, from: data)
        guard decision.isValid, decision.deliveryId == moment, decision.context == pending.context else {
            throw AniccaAPIError.serviceUnavailable
        }
        journal.decisions.append(decision)
        journal.pending.removeValue(forKey: moment)
        try persist()
        AnalyticsManager.shared.track(.nudgeDecisionMade, properties: [
            "delivery_id": decision.deliveryId, "assigned_probability": decision.assignedProbability,
            "candidate_count": decision.candidates.count, "policy_version": decision.policyVersion,
            "backend": decision.backend, "send": decision.send, "source": source,
            "outcome_window_sec": decision.outcomeWindowSec
        ])
        return decision
    }

    /// Caller supplies one durable UUID per real intervention moment, including APNs wakeups.
    func notify(moment: String) async throws {
        guard await NotificationScheduler.shared.isAuthorizedForAlerts(),
              let decision = try await decide(source: "notification", moment: moment), decision.send else { return }
        // A retry must not deliver an expired decision as a new intervention.
        guard Date().timeIntervalSince1970 < decision.outcomeWindowEnd else { return }
        guard !journal.submitted.contains(moment) else { return }
        let center = UNUserNotificationCenter.current()
        let delivered = await center.deliveredNotifications()
        guard !delivered.contains(where: { $0.request.identifier == moment }) else { return }
        let content = UNMutableNotificationContent()
        content.title = "Anicca"
        content.body = decision.chosen.text
        content.categoryIdentifier = NotificationScheduler.Category.nudge.rawValue
        content.userInfo = ["delivery_id": moment, "quoteId": decision.quote!.id, "manager": true]
        // Persist intent first. A crash around add remains delivery-unknown;
        // never resubmit a possibly delivered notification after dismissal.
        journal.submitted.append(moment)
        try persist()
        try await center.add(UNNotificationRequest(identifier: moment, content: content, trigger: nil))
    }

    func observe(deliveryId: String, event: ManagerBenchEvent, at date: Date) {
        guard UUID(uuidString: deliveryId) != nil else { return }
        let observation = Observation(deliveryId: deliveryId, event: event.rawValue, observedAt: date.timeIntervalSince1970)
        if !journal.observations.contains(observation) { journal.observations.append(observation) }
        do { try persist() } catch { return }
        Task { await flush() }
    }

    func flush() async {
        guard !flushing else { return }
        flushing = true
        defer { flushing = false }
        let epoch = generation
        for observation in journal.observations {
            do {
                let data = try await request("observations", body: observation)
                guard generation == epoch else { return }
                let ack = try JSONSerialization.jsonObject(with: data) as? [String: Any]
                guard ack?["accepted"] as? Bool == true, ack?["delivery_id"] as? String == observation.deliveryId else { return }
                journal.observations.removeAll { $0 == observation }
                try persist()
            } catch { return } // Durable queue retried on next response or foreground.
        }
    }

    func appOpened(at date: Date = Date()) {
        for decision in journal.decisions where decision.decisionPointAt <= date.timeIntervalSince1970 && date.timeIntervalSince1970 <= decision.outcomeWindowEnd {
            observe(deliveryId: decision.deliveryId, event: .appOpened, at: date)
        }
        Task { await flush() }
    }
}
