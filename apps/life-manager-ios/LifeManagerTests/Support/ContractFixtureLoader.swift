import Foundation

enum ContractFixtureLoader {
    static func data(named name: String, filePath: String = #filePath) throws -> Data {
        let fileManager = FileManager.default
        let checkoutFixtures = URL(fileURLWithPath: filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("TestFixtures/mobile-v1")
        var candidates: [String?] = [
            checkoutFixtures.path,
            ProcessInfo.processInfo.environment["LIFEMANAGER_CONTRACT_FIXTURES"],
            fileManager.currentDirectoryPath + "/../life-manager/contracts/mobile-v1",
            URL(fileURLWithPath: filePath)
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("apps/life-manager/contracts/mobile-v1")
                .path
        ]

        let worktreeRoot = URL(fileURLWithPath: filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        if let siblingWorktrees = try? fileManager.contentsOfDirectory(
            at: worktreeRoot,
            includingPropertiesForKeys: [.isDirectoryKey],
            options: [.skipsHiddenFiles]
        ) {
            candidates.append(contentsOf: siblingWorktrees.map {
                $0.appendingPathComponent("apps/life-manager/contracts/mobile-v1").path
            })
        }

        for candidate in candidates.compactMap({ $0 }) {
            let url = URL(fileURLWithPath: candidate, isDirectory: true)
                .appendingPathComponent(name)
            if fileManager.fileExists(atPath: url.path) {
                return try Data(contentsOf: url)
            }
        }

        throw FixtureError.missing(name, candidates: candidates.compactMap({ $0 }))
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
