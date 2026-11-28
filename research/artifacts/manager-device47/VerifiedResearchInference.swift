import Foundation
import CryptoKit

/// Offline factual research only, not an Anicca intervention model.
struct VerifiedResearchInference {
    enum Failure: Error { case hashMismatch, unsupportedFormat, invalidContext, outOfScope }
    static let scope = "uci_shopper_factual_research"
    static let months = ["Aug","Dec","Feb","Jul","June","Mar","May","Nov","Oct","Sep"]
    static let visitors = ["New_Visitor","Other","Returning_Visitor"]
    static let weekends = ["FALSE","TRUE"]
    static let hashes = [
        32:"d5d90f175e549e5ae40436c2e0430fb4f6ffe2d5e515f2ac77582ceb30bb6c75",
        8:"df4e3478636ed879ecbd58d262a93eb20edc6284c6b35c2a01e984a84f2f4b52",
        4:"05e690a712846e56ddc58755d96ac51992076236ae662c14f76f0782b0c88977"
    ]
    let model: PortableQuantizedResearch
    init(data: Data, bits: Int) throws {
        guard let expected = Self.hashes[bits] else { throw Failure.unsupportedFormat }
        let digest = SHA256.hash(data: data).map { String(format:"%02x",$0) }.joined()
        guard digest == expected else { throw Failure.hashMismatch }
        model = try PortableQuantizedResearch(data:data,bits:bits)
    }
    func predict(month: String, visitor: String, weekend: String, specialDay: Double, scope: String) throws -> Double {
        guard scope == Self.scope else { throw Failure.outOfScope }
        guard Self.months.contains(month), Self.visitors.contains(visitor), Self.weekends.contains(weekend),
              specialDay.isFinite, (0...1).contains(specialDay) else { throw Failure.invalidContext }
        let features = Self.months.map { $0 == month ? 1.0 : 0.0 }
          + Self.visitors.map { $0 == visitor ? 1.0 : 0.0 }
          + Self.weekends.map { $0 == weekend ? 1.0 : 0.0 } + [specialDay]
        return try model.predict(features,scope:scope)
    }
    static var mobileReleaseEligible: Bool { false }
}
