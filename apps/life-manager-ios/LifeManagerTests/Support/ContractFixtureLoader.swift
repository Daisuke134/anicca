import Foundation

private final class ContractFixtureBundleMarker: NSObject {}

enum ContractFixtureLoader {
    static func data(named name: String, filePath: String = #filePath) throws -> Data {
        let checkoutFixtures = URL(fileURLWithPath: filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("TestFixtures/mobile-v1")
        let bundledFixtures = Bundle(for: ContractFixtureBundleMarker.self)
            .url(forResource: "mobile-v1", withExtension: nil)
        let candidates = [bundledFixtures, checkoutFixtures].compactMap { $0 }

        for candidate in candidates {
            let url = candidate.appendingPathComponent(name)
            if FileManager.default.fileExists(atPath: url.path) {
                return try Data(contentsOf: url)
            }
        }

        throw FixtureError.missing(name, candidates: candidates.map(\.path))
    }

    enum FixtureError: Error, CustomStringConvertible {
        case missing(String, candidates: [String])

        var description: String {
            switch self {
            case let .missing(name, candidates):
                return "Missing canonical fixture \(name); searched \(candidates.joined(separator: ", "))"
            }
        }
    }
}
