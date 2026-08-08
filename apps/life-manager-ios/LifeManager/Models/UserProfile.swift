import Foundation

struct Bootstrap: Codable, Equatable, Sendable {
    let product: BootstrapProduct
    let user: BootstrapUser
    let calendar: CalendarConnection
    let analysis: BootstrapAnalysis
}

struct BootstrapProduct: Codable, Equatable, Sendable {
    let locale: ProductLocale
    let timezone: String
}

struct BootstrapUser: Codable, Equatable, Sendable {
    let id: String
    let name: String?
    let home: HomeAddress
}

enum HomeAddressStatus: String, Codable, Equatable, Sendable {
    case missing
    case present
}

struct HomeAddress: Codable, Equatable, Sendable {
    let status: HomeAddressStatus
    let display: String?
}

enum CalendarConnectionStatus: String, Codable, Equatable, Sendable {
    case connected
    case disconnected
}

struct CalendarConnection: Codable, Equatable, Sendable {
    let status: CalendarConnectionStatus
}

enum BootstrapAnalysisStatus: String, Codable, Equatable, Sendable {
    case idle
    case readingEvents = "reading_events"
    case checkingLocations = "checking_locations"
    case calculatingRoute = "calculating_route"
}

struct BootstrapAnalysis: Codable, Equatable, Sendable {
    let status: BootstrapAnalysisStatus
}

struct ProfileDraft: Codable, Equatable, Sendable {
    let name: String?
    let home: String?
    let productLocale: ProductLocale

    init(name: String?, home: String?, productLocale: ProductLocale = .en) {
        self.name = name
        self.home = home
        self.productLocale = productLocale
    }
}
