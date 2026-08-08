import Foundation

enum ContractFixtureLoader {
    static func data(named name: String, filePath: String = #filePath) throws -> Data {
        let fileManager = FileManager.default
        var candidates: [String?] = [
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
                let data = try Data(contentsOf: url)
                guard isCompatible(data: data, name: name) else { continue }
                return data
            }
        }

        throw FixtureError.missing(name, candidates: candidates.compactMap({ $0 }))
    }

    private static func isCompatible(data: Data, name: String) -> Bool {
        guard name == "bootstrap.json" else { return true }
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return false
        }
        return object["product"] != nil
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
