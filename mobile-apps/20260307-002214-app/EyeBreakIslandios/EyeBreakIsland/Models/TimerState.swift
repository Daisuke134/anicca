import Foundation

enum TimerState: String, Codable {
    case idle
    case running
    case breaking
    case paused
}
