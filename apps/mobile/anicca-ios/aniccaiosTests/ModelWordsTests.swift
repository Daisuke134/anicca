import XCTest
@testable import aniccaios

final class ModelWordsTests: XCTestCase {
    func testCandidateDistributionJournalRoundTrip() throws {
        let data = Data("""
        {"message_id":"generated:delivery:a","category":"reflection","tags":[],
         "treatment_assigned":"generated:delivery:a","assigned_probability":0.8,
         "policy_version":"manager-generated-v1","selection_reason":"model_generated_weighted_draw",
         "text":"Breathe.","candidates":[
           {"id":"generated:delivery:a","kind":"reflection","text":"Breathe.","probability":0.8},
           {"id":"generated:delivery:b","kind":"none","text":"","probability":0.2}]}
        """.utf8)
        let stimulus = try ManagerBenchCase.decoder.decode(ManagerBenchCase.Stimulus.self, from: data)
        XCTAssertEqual(stimulus.candidates?.count, 2)
        XCTAssertEqual(stimulus.candidates?.first?.probability, stimulus.assignedProbability)
        let encoded = try ManagerBenchCase.encoder.encode(stimulus)
        XCTAssertEqual(try ManagerBenchCase.decoder.decode(ManagerBenchCase.Stimulus.self, from: encoded), stimulus)
    }

    func testOnlyGeneratedValidatedChosenWordCanDisplay() throws {
        let id = UUID().uuidString
        let data = Data("""
        {"delivery_id":"\(id)","backend":"manager-v1","policy_version":"manager-generated-v1",
         "generator_model":"fixture","send":true,"assigned_probability":0.8,
         "chosen":{"id":"a","kind":"reflection","text":"Let this breath finish.","probability":0.8},
         "candidates":[{"id":"a","kind":"reflection","text":"Let this breath finish.","probability":0.8},
                       {"id":"b","kind":"none","text":"","probability":0.2}]}
        """.utf8)
        let decision = try JSONDecoder().decode(ModelWordDecision.self, from: data)
        XCTAssertTrue(decision.isValid(for: id))
        XCTAssertFalse(decision.isValid(for: UUID().uuidString))
        XCTAssertEqual(decision.quote?.text, "Let this breath finish.")
        XCTAssertTrue(decision.quote!.id.contains(id))
        let invalid = Data(String(decoding: data, as: UTF8.self).replacingOccurrences(of: "\"assigned_probability\":0.8", with: "\"assigned_probability\":0.2").utf8)
        XCTAssertFalse(try JSONDecoder().decode(ModelWordDecision.self, from: invalid).isValid(for: id))
    }
}
