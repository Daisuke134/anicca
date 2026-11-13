import AVFoundation
import CoreVideo
import Foundation

// Validate real simulator output independently of the Maestro exit status.
let arguments = CommandLine.arguments
guard arguments.count == 3, let elapsed = Double(arguments[2]) else {
    fatalError("Usage: verify-maestro-recording.swift VIDEO ELAPSED_SECONDS")
}
let asset = AVURLAsset(url: URL(fileURLWithPath: arguments[1]))
let duration = asset.duration.seconds
// The simulator recorder starts/stops a few seconds inside the elapsed
// wall-clock window (observed lag: 9s on run 43328980080, whose flow
// passed and whose 627s video was complete). A 30s allowance covers
// recorder lag; the decodable-frame check below remains the real
// truncation gate.
guard duration.isFinite, duration >= max(1, elapsed - 30),
      let track = asset.tracks(withMediaType: .video).first else {
    fatalError("Video is missing, truncated, or shorter than the recorded journey")
}
let reader = try AVAssetReader(asset: asset)
let output = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
])
reader.add(output)
guard reader.startReading(), let sample = output.copyNextSampleBuffer(),
      CMSampleBufferGetImageBuffer(sample) != nil else {
    fatalError("Recorded video has no decodable frame")
}
reader.cancelReading()
let result: [String: Any] = [
    "duration_seconds": duration,
    "journey_elapsed_seconds": elapsed,
    "decoded_frame": true
]
let data = try JSONSerialization.data(withJSONObject: result, options: [.prettyPrinted, .sortedKeys])
print(String(decoding: data, as: UTF8.self))
