import Foundation
struct Fixture: Decodable { let x:[[Double]]; let p32:[Double]; let p8:[Double]; let p4:[Double] }
struct Result: Encodable { let bits:Int; let rows:Int; let maxAbsoluteError:Double; let negativeControls:Int; let medianBatchMilliseconds:Double; let checksum:Double }
enum TestFailure: Error { case invariant }
func require(_ ok:Bool) throws { if !ok { throw TestFailure.invariant } }
let root=URL(fileURLWithPath:CommandLine.arguments[1])
let f=try JSONDecoder().decode(Fixture.self,from:Data(contentsOf:root.appendingPathComponent("fixtures.json")))
func context(_ x:[Double]) throws -> (String,String,String,Double) {
    try require(x.count==16)
    let a=Array(x[0..<10]), b=Array(x[10..<13]), c=Array(x[13..<15])
    try require([a,b,c].allSatisfy { $0.filter{$0==1}.count==1 && $0.allSatisfy{$0==0 || $0==1} })
    return (VerifiedResearchInference.months[a.firstIndex(of:1)!],VerifiedResearchInference.visitors[b.firstIndex(of:1)!],VerifiedResearchInference.weekends[c.firstIndex(of:1)!],x[15])
}
let contexts=try f.x.map(context)
var results=[Result]()
for (bits,expected) in [(32,f.p32),(8,f.p8),(4,f.p4)] {
    let data=try Data(contentsOf:root.appendingPathComponent("out/kd_43_\(bits).bin"))
    let m=try VerifiedResearchInference(data:data,bits:bits)
    try require(expected.count==contexts.count)
    func run() throws -> [Double] {try contexts.map{try m.predict(month:$0.0,visitor:$0.1,weekend:$0.2,specialDay:$0.3,scope:VerifiedResearchInference.scope)}}
    let v=try run()
    let error=zip(v,expected).map{abs($0-$1)}.max()!
    try require(error<1e-6 && !VerifiedResearchInference.mobileReleaseEligible)
    var negative=0
    var corrupt=data;corrupt[0] ^= 1
    do {_ = try VerifiedResearchInference(data:corrupt,bits:bits);throw TestFailure.invariant} catch VerifiedResearchInference.Failure.hashMismatch {negative += 1}
    do {_ = try VerifiedResearchInference(data:Data(),bits:bits);throw TestFailure.invariant} catch VerifiedResearchInference.Failure.hashMismatch {negative += 1}
    let a=contexts[0]
    for scope in ["anicca_mobile","intervention",""] {
        do {_ = try m.predict(month:a.0,visitor:a.1,weekend:a.2,specialDay:a.3,scope:scope);throw TestFailure.invariant} catch VerifiedResearchInference.Failure.outOfScope {negative += 1}
    }
    for c in [("Jan",a.1,a.2,a.3),(a.0,"UNKNOWN",a.2,a.3),(a.0,a.1,"unknown",a.3),(a.0,a.1,a.2,Double.nan),(a.0,a.1,a.2,-0.1),(a.0,a.1,a.2,1.1)] {
        do {_ = try m.predict(month:c.0,visitor:c.1,weekend:c.2,specialDay:c.3,scope:VerifiedResearchInference.scope);throw TestFailure.invariant} catch VerifiedResearchInference.Failure.invalidContext {negative += 1}
    }
    var times=[Double]();var sum=0.0
    for _ in 0..<9 { let start=DispatchTime.now().uptimeNanoseconds;let pred=try run();times.append(Double(DispatchTime.now().uptimeNanoseconds-start)/1e6);sum += pred.reduce(0,+) }
    results.append(Result(bits:bits,rows:v.count,maxAbsoluteError:error,negativeControls:negative,medianBatchMilliseconds:times.sorted()[4],checksum:sum))
}
do {_ = try VerifiedResearchInference(data:Data(),bits:16);throw TestFailure.invariant} catch VerifiedResearchInference.Failure.unsupportedFormat {}
let encoder=JSONEncoder();encoder.outputFormatting=[.prettyPrinted,.sortedKeys]
print(String(data:try encoder.encode(results),encoding:.utf8)!)
