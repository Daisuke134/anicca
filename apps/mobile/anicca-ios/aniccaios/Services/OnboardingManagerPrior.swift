import Foundation

/// Cold-start categorical model. Editorial tags supply the prior; the person's
/// answers and first save/skip label update its mass before sampling. This is
/// explicitly a local prior, not a claim of trained or remote LLM inference.
enum OnboardingManagerPrior {
    static let policyVersion = "manager_onboarding_prior_v1"

    struct Candidate {
        let quote: Quote
        let probability: Double
    }

    static func distribution(user: SyntheticUser, pool: [Quote], band: PersonalizedNudgeSelector.TimeBand) -> [Candidate] {
        let answers = user.answerSnapshot.values
        let profile = user.conditioningProfile
        let primary = PersonalizationRules.primaryCategory(desiredState: profile.desiredState)
        let focus = Set(PersonalizationRules.focusCategories(answers["focus_categories"] ?? []))
        let pain = Set(profile.painPointIds.flatMap(PersonalizationRules.boostCategories))
        let beliefs = Set(user.beliefThemes)
        let candidates = pool.filter { PersonalizedNudgeSelector.isEligible(quote: $0, user: user, band: band) }
            .sorted { $0.id < $1.id }
        let weights = candidates.map { quote -> Double in
            var mass = 1.0
            if quote.categoryID == primary { mass *= 4 }
            if focus.contains(quote.categoryID) { mass *= 2 }
            if pain.contains(quote.categoryID) { mass *= 1.5 }
            if let traits = AdaptiveAffirmationCatalog.traits(for: quote) {
                let matches = beliefs.intersection(traits.beliefThemes).count
                mass *= pow(2.0, Double(matches))
                // Beta(1,1) response model for this belief archetype. Only
                // observed saves/skips update it; unobserved is not failure.
                var outcomes: [String: Bool] = [:]
                for event in user.interventionHistory {
                    guard event.event == .saved || event.event == .skipped,
                          let id = event.messageId,
                          let observed = pool.first(where: { $0.id == id }),
                          let observedTraits = AdaptiveAffirmationCatalog.traits(for: observed),
                          !Set(observedTraits.beliefThemes).isDisjoint(with: traits.beliefThemes) else { continue }
                    outcomes[event.deliveryId] = (outcomes[event.deliveryId] == true) || event.event == .saved
                }
                let successes = Double(outcomes.values.filter { $0 }.count)
                mass *= (1 + successes) / (2 + Double(outcomes.count))
                for (axis, ids) in traits.answerMatches where !Set(ids).isDisjoint(with: answers[axis] ?? []) { mass *= 3 }
                // People who already tried a method get less introductory advice.
                if !Set(traits.methods).isDisjoint(with: answers["prior_attempts"] ?? []) { mass *= 0.25 }
                if traits.intensity == PersonalizationRules.intensity(profile: profile) { mass *= 1.5 }
            }
            return mass
        }
        let total = weights.reduce(0, +)
        guard total > 0 else { return [] }
        return zip(candidates, weights).map { Candidate(quote: $0.0, probability: $0.1 / total) }
    }

    static func select(user: SyntheticUser, pool: [Quote], band: PersonalizedNudgeSelector.TimeBand,
                       random: () -> Double = { Double.random(in: 0..<1) }) -> PersonalizedNudgeSelector.Selection? {
        let candidates = distribution(user: user, pool: pool, band: band)
        guard let last = candidates.last else { return nil }
        let draw = min(max(random(), 0), 1)
        var cumulative = 0.0
        let selected = candidates.first { candidate in
            cumulative += candidate.probability
            return draw < cumulative
        } ?? last
        let activeAxes = user.answerSnapshot.values.keys.sorted().filter {
            !Set(user.answerSnapshot.values[$0] ?? []).isSubset(of: ["unknown", "not_asked"])
        }
        return PersonalizedNudgeSelector.Selection(
            quote: selected.quote,
            reason: "posterior_conditioned_on:" + activeAxes.joined(separator: ","),
            candidateCount: candidates.count,
            candidateIDs: candidates.map { $0.quote.id },
            assignedProbability: selected.probability,
            policyVersion: policyVersion)
    }
}
