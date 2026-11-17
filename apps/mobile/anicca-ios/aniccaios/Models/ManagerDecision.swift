import Foundation

/// Generated text is retained as stimulus evidence; user free text is never sent.
struct ManagerDecision: Codable, Equatable {
    struct Candidate: Codable, Equatable {
        let id: String
        let kind: String
        let text: String
        let probability: Double
    }
    let deliveryId: String
    let decisionPointAt: Double
    let context: [String: String]
    let candidates: [Candidate]
    let chosen: Candidate
    let assignedProbability: Double
    let send: Bool
    let backend: String
    let policyVersion: String
    let outcomeWindowSec: Int
    let outcomeWindowEnd: Double

    var isValid: Bool {
        UUID(uuidString: deliveryId) != nil && backend == "manager-v1" && policyVersion == "manager-generated-v1" &&
        decisionPointAt.isFinite && outcomeWindowSec == 1800 && outcomeWindowEnd == decisionPointAt + 1800 &&
        (2...8).contains(candidates.count) && Set(candidates.map(\.id)).count == candidates.count &&
        candidates.allSatisfy {
            $0.probability.isFinite && $0.probability > 0 && $0.probability <= 1 &&
            ["reflection", "humor", "question", "teaching", "breathing", "action", "none"].contains($0.kind) &&
            $0.text.count <= 500 && (($0.kind == "none") == $0.text.isEmpty)
        } && candidates.filter { $0.kind == "none" }.count == 1 &&
        abs(candidates.reduce(0) { $0 + $1.probability } - 1) <= 1e-12 &&
        candidates.contains(chosen) && assignedProbability == chosen.probability && send == (chosen.kind != "none")
    }

    var quote: Quote? { send ? Quote(id: "manager.\(deliveryId).\(chosen.id)", text: chosen.text) : nil }
}
