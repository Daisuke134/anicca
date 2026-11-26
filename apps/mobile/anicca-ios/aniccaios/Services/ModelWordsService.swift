import Foundation
import CryptoKit

/// The server chooses once and commits the assignment before returning it.
struct ModelWordDecision: Decodable {
    struct Candidate: Decodable, Equatable {
        let id: String
        let kind: String
        let text: String
        let probability: Double
    }
    let deliveryID: String
    let backend: String
    let policyVersion: String
    let generatorModel: String
    let send: Bool
    let assignedProbability: Double
    let chosen: Candidate
    let candidates: [Candidate]

    enum CodingKeys: String, CodingKey {
        case deliveryID = "delivery_id", backend, policyVersion = "policy_version"
        case generatorModel = "generator_model", send, assignedProbability = "assigned_probability"
        case chosen, candidates
    }

    func isValid(for id: String) -> Bool {
        deliveryID == id && backend == "manager-v1" && policyVersion == "manager-generated-v1"
            && !generatorModel.isEmpty && candidates.count >= 2 && candidates.count <= 8
            && Set(candidates.map(\.id)).count == candidates.count
            && candidates.contains(chosen) && assignedProbability == chosen.probability
            && abs(candidates.reduce(0) { $0 + $1.probability } - 1) < 1e-10
            && candidates.filter { $0.kind == "none" }.count == 1
            && candidates.allSatisfy {
                ["reflection", "humor", "question", "teaching", "breathing", "action", "none"].contains($0.kind)
                    && $0.probability.isFinite && $0.probability > 0 && $0.probability <= 1
                    && $0.text.count <= 500 && ($0.kind == "none" ? $0.text.isEmpty : !$0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }
            && send == (chosen.kind != "none")
    }

    var quote: Quote? {
        guard send, isValid(for: deliveryID) else { return nil }
        return Quote(id: "generated:\(deliveryID):\(chosen.id)", text: chosen.text)
    }
}

@MainActor
final class ModelWordsService {
    static let shared = ModelWordsService()

    /// Account, categorical answers, language, time band and local day bind retries to one
    /// draw. Never reuse the pre-model DailyAffirmationStore's catalog cache.
    func today(user: SyntheticUser, language: String, now: Date = Date()) async throws -> ModelWordDecision {
        guard let account = AppState.shared.authStatus.userId else { throw AniccaAPIError.unauthorized }
        let calendar = Calendar.current
        let context: [String: Any] = [
            "source": "daily_home", "language": language,
            "desired_state": user.conditioningProfile.desiredState ?? "unknown",
            "time_band": PersonalizedNudgeSelector.TimeBand.band(forHour: calendar.component(.hour, from: now)).rawValue,
            "synthetic_user": ["answer_ids": user.answerSnapshot.values, "answer_version": user.answerSnapshot.version]
        ]
        let day = calendar.dateComponents([.year, .month, .day], from: now)
        let bytes = try JSONSerialization.data(withJSONObject: ["account": account,
            "day": [day.year!, day.month!, day.day!], "timezone": calendar.timeZone.identifier,
            "context": context], options: [.sortedKeys])
        let hex = SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
        let raw = Array(hex.prefix(32))
        let id = "\(String(raw[0..<8]))-\(String(raw[8..<12]))-\(String(raw[12..<16]))-\(String(raw[16..<20]))-\(String(raw[20..<32]))"
        var request = URLRequest(url: AppConfig.proxyBaseURL.appendingPathComponent("manager/decisions"))
        request.httpMethod = "POST"
        request.timeoutInterval = 75
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: ["delivery_id": id, "context": context])
        try await NetworkSessionManager.shared.setAuthHeaders(for: &request)
        let (data, response) = try await NetworkSessionManager.shared.session.data(for: request)
        guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
            throw AniccaAPIError.serviceUnavailable
        }
        let decision = try JSONDecoder().decode(ModelWordDecision.self, from: data)
        guard decision.isValid(for: id), AppState.shared.authStatus.userId == account else {
            throw AniccaAPIError.serviceUnavailable
        }
        // Persist the exact server assignment locally; outcomes join its ID.
        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              var record = json["managerbench_case"] as? [String: Any] else {
            throw AniccaAPIError.serviceUnavailable
        }
        record["person_id"] = DecisionPointRecorder.shared.personId
        let row = try ManagerBenchCase.decoder.decode(ManagerBenchCase.self,
            from: JSONSerialization.data(withJSONObject: record))
        // Hoisted out of the guard: a trailing closure inside a guard
        // condition list does not parse in Swift.
        let expectedCandidates = decision.candidates.map {
            ManagerBenchCase.Candidate(id: "generated:\(id):\($0.id)",
                kind: $0.kind, text: $0.text, probability: $0.probability)
        }
        guard row.deliveryId == id, row.hasValidAssignment,
              row.stimulus.assignedProbability == decision.assignedProbability,
              row.stimulus.text == decision.chosen.text,
              row.stimulus.generatorModel == decision.generatorModel,
              row.stimulus.policyVersion == decision.policyVersion,
              row.stimulus.candidates == expectedCandidates,
              row.stimulus.selectionReason == "model_generated_weighted_draw",
              DecisionPointStore.shared.append(row) else {
            throw AniccaAPIError.serviceUnavailable
        }
        return decision
    }
}
