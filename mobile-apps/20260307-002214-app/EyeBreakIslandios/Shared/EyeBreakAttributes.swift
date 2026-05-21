import ActivityKit

struct EyeBreakAttributes: ActivityAttributes {
    public struct ContentState: Codable, Hashable {
        var timerState: String
        var remainingSeconds: Int
        var breakCount: Int
    }
    var sessionId: String
}
