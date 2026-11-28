import Foundation

/// Research only. No mobile policy authorization or production routing.
struct PortableQuantizedResearch {
    enum Failure: Error { case malformed, outOfScope }
    let weights: [Double]
    let bias: Double
    init(data: Data, bits: Int) throws {
        let bytes = Array(data)
        guard [4, 8, 32].contains(bits), bytes.count == (bits == 32 ? 68 : bits == 8 ? 24 : 16) else { throw Failure.malformed }
        func f32(_ i: Int) -> Double {
            let u = UInt32(bytes[i]) | UInt32(bytes[i+1]) << 8 | UInt32(bytes[i+2]) << 16 | UInt32(bytes[i+3]) << 24
            return Double(Float(bitPattern: u))
        }
        if bits == 32 { weights = (0..<16).map { f32($0*4) }; bias = f32(64) }
        else {
            let scale = f32(0)
            guard scale.isFinite, scale > 0 else { throw Failure.malformed }
            if bits == 8 {
                weights = (0..<16).map { Double(Int8(bitPattern: bytes[4+$0])) * scale }
            } else {
                weights = (0..<16).map { i in
                    let packed = bytes[4+i/2]
                    let nibble = i%2 == 0 ? packed & 15 : packed >> 4
                    return Double(Int(nibble)-8) * scale
                }
            }
            bias = f32(bytes.count-4)
        }
        guard weights.allSatisfy({ $0.isFinite }), bias.isFinite else { throw Failure.malformed }
    }
    func predict(_ features: [Double], scope: String) throws -> Double {
        guard scope == "uci_shopper_factual_research" else { throw Failure.outOfScope }
        guard features.count == 16, features.allSatisfy({ $0.isFinite && $0 >= 0 && $0 <= 1 }) else { throw Failure.malformed }
        let z = zip(weights,features).reduce(bias) { $0 + $1.0*$1.1 }
        guard z.isFinite else { throw Failure.malformed }
        return 1/(1+exp(-z))
    }
}
