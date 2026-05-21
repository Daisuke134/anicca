import Testing
@testable import ChiDaily

struct ConstitutionTypeTests {

    @Test func woodConstitutionJapaneseName() {
        let c = ConstitutionType.wood
        #expect(c.japaneseName == "木のタイプ")
    }

    @Test func fireConstitutionJapaneseName() {
        let c = ConstitutionType.fire
        #expect(c.japaneseName == "火のタイプ")
    }

    @Test func earthConstitutionJapaneseName() {
        let c = ConstitutionType.earth
        #expect(c.japaneseName == "土のタイプ")
    }

    @Test func metalConstitutionJapaneseName() {
        let c = ConstitutionType.metal
        #expect(c.japaneseName == "金のタイプ")
    }

    @Test func waterConstitutionJapaneseName() {
        let c = ConstitutionType.water
        #expect(c.japaneseName == "水のタイプ")
    }

    @Test func allCasesExist() {
        let allCases = ConstitutionType.allCases
        #expect(allCases.count == 5)
    }

    @Test func fromStringValid() {
        let c = ConstitutionType.from(string: "Fire")
        #expect(c == .fire)
    }

    @Test func fromStringInvalidDefaultsToEarth() {
        let c = ConstitutionType.from(string: "Unknown")
        #expect(c == .earth)
    }
}
