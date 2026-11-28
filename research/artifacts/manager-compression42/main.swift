import Foundation
struct Fixture: Decodable { let x: [[Double]]; let p32:[Double]; let p8:[Double]; let p4:[Double] }
let root = URL(fileURLWithPath: CommandLine.arguments[1])
let f = try JSONDecoder().decode(Fixture.self, from: Data(contentsOf: root.appendingPathComponent("fixtures.json")))
var checks = 0
for (bits,expected) in [(32,f.p32),(8,f.p8),(4,f.p4)] {
    let d = try Data(contentsOf: root.appendingPathComponent("out/kd_43_\(bits).bin"))
    let m = try PortableQuantizedResearch(data:d,bits:bits)
    var e = 0.0
    for (x,p) in zip(f.x,expected) {
        let v = try m.predict(x,scope:"uci_shopper_factual_research")
        e = max(e,abs(v-p)); checks += 1
    }
    precondition(e < 1e-6)
    do { _ = try m.predict(f.x[0],scope:"anicca_mobile"); fatalError("scope bypass") } catch PortableQuantizedResearch.Failure.outOfScope {}
    do { _ = try PortableQuantizedResearch(data: Data(),bits:bits); fatalError("malformed") } catch PortableQuantizedResearch.Failure.malformed {}
    print("bits",bits,"n",expected.count,"max_abs",e)
}
print("checks",checks,"scope/malformed negative controls 6")
