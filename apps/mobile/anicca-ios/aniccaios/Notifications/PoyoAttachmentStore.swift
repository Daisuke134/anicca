import Foundation
import OSLog
import UIKit

/// Exports Poyo's expression PNGs into the shared App Group container so the
/// notification service extension can attach the right face to a remote push.
///
/// Why this exists: a UNNotificationServiceExtension cannot read the main
/// app's asset catalog. The shared container (`group.ai.anicca.app.ios`,
/// already used for auth UserDefaults) is the bridge. The app refreshes the
/// PNGs on launch; `NotificationService` reads `poyoExpression` from the
/// push payload and attaches the matching file. Every failure path is
/// silent — a missing face must never break a notification.
enum PoyoAttachmentStore {
    static let appGroupID = "group.ai.anicca.app.ios"
    static let directoryName = "poyo"

    private static let logger = Logger(subsystem: "com.anicca.ios", category: "PoyoAttachmentStore")

    static var sharedDirectory: URL? {
        FileManager.default
            .containerURL(forSecurityApplicationGroupIdentifier: appGroupID)?
            .appendingPathComponent(directoryName, isDirectory: true)
    }

    /// Copy all expression PNGs from the asset catalog into the shared
    /// container. Idempotent; safe to call on every app launch.
    static func exportExpressionsIfNeeded() {
        guard let directory = sharedDirectory else {
            logger.error("App Group container unavailable for Poyo export")
            return
        }
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        } catch {
            logger.error("Failed to create Poyo directory: \(error.localizedDescription, privacy: .public)")
            return
        }

        for expression in PoyoExpression.allCases {
            let destination = directory.appendingPathComponent(expression.fileName + ".png")
            if FileManager.default.fileExists(atPath: destination.path) { continue }
            guard let image = UIImage(named: expression.imageName),
                  let data = image.pngData() else {
                logger.error("Poyo asset missing from catalog: \(expression.imageName, privacy: .public)")
                continue
            }
            do {
                try data.write(to: destination, options: .atomic)
            } catch {
                logger.error("Failed to write Poyo PNG: \(error.localizedDescription, privacy: .public)")
            }
        }
    }

    /// URL of an exported expression PNG in the shared container, if present.
    /// (The extension implements the same lookup against its own container
    /// path — extensions cannot link this app-target type.)
    static func exportedURL(for expression: PoyoExpression) -> URL? {
        guard let directory = sharedDirectory else { return nil }
        let url = directory.appendingPathComponent(expression.fileName + ".png")
        return FileManager.default.fileExists(atPath: url.path) ? url : nil
    }
}
