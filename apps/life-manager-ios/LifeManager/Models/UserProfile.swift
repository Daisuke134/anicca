import Foundation

struct Bootstrap: Codable, Equatable, Sendable {
    let user: BootstrapUser
    let calendar: CalendarConnection
    let analysis: BootstrapAnalysis
    let offer: BootstrapOffer?

    init(
        user: BootstrapUser,
        calendar: CalendarConnection,
        analysis: BootstrapAnalysis,
        offer: BootstrapOffer? = nil
    ) {
        self.user = user
        self.calendar = calendar
        self.analysis = analysis
        self.offer = offer
    }
}

struct BootstrapUser: Codable, Equatable, Sendable {
    let id: String
    let name: String?
    let productLocale: ProductLocale
    let timezone: String
    let home: HomeAddress
    let phone: PhoneSettings
    let callsEnabled: Bool
    let callLanguage: ProductLocale?

    init(
        id: String,
        name: String?,
        productLocale: ProductLocale = .en,
        timezone: String = "UTC",
        home: HomeAddress,
        phone: PhoneSettings = .missing,
        callsEnabled: Bool = false,
        callLanguage: ProductLocale? = nil
    ) {
        self.id = id
        self.name = name
        self.productLocale = productLocale
        self.timezone = timezone
        self.home = home
        self.phone = phone
        self.callsEnabled = callsEnabled
        self.callLanguage = callLanguage
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.init(
            id: try container.decode(String.self, forKey: .id),
            name: try container.decodeIfPresent(String.self, forKey: .name),
            productLocale: try container.decode(ProductLocale.self, forKey: .productLocale),
            timezone: try container.decode(String.self, forKey: .timezone),
            home: try container.decode(HomeAddress.self, forKey: .home),
            phone: try container.decodeIfPresent(PhoneSettings.self, forKey: .phone) ?? .missing,
            callsEnabled: try container.decodeIfPresent(Bool.self, forKey: .callsEnabled) ?? false,
            callLanguage: try container.decodeIfPresent(ProductLocale.self, forKey: .callLanguage)
        )
    }

    private enum CodingKeys: String, CodingKey {
        case id
        case name
        case productLocale
        case timezone
        case home
        case phone
        case callsEnabled
        case callLanguage
    }
}

enum PhoneStatus: String, Codable, Equatable, Sendable {
    case configured
    case missing
}

struct PhoneSettings: Codable, Equatable, Sendable {
    let status: PhoneStatus
    let masked: String?

    static let missing = PhoneSettings(status: .missing, masked: nil)

    static func configured(_ masked: String) -> Self {
        Self(status: .configured, masked: masked)
    }
}

enum HomeAddressStatus: String, Codable, Equatable, Sendable {
    case missing
    case ready
}

struct HomeAddress: Codable, Equatable, Sendable {
    let status: HomeAddressStatus
    let display: String?
}

struct UserProfile: Codable, Equatable, Sendable {
    let id: String
    let name: String?
    let home: HomeAddress
    let productLocale: ProductLocale
    let timezone: String
    let phone: PhoneSettings
    let callsEnabled: Bool
    let callLanguage: ProductLocale?
    let calendarStatus: CalendarConnectionStatus
    let offerStatus: OfferStatus

    init(
        id: String,
        name: String?,
        home: HomeAddress,
        productLocale: ProductLocale,
        timezone: String,
        phone: PhoneSettings = .missing,
        callsEnabled: Bool = false,
        callLanguage: ProductLocale? = nil,
        calendarStatus: CalendarConnectionStatus = .connected,
        offerStatus: OfferStatus = .unavailable
    ) {
        self.id = id
        self.name = name
        self.home = home
        self.productLocale = productLocale
        self.timezone = timezone
        self.phone = phone
        self.callsEnabled = callsEnabled
        self.callLanguage = callLanguage
        self.calendarStatus = calendarStatus
        self.offerStatus = offerStatus
    }

    init(bootstrap: Bootstrap) {
        self.init(
            id: bootstrap.user.id,
            name: bootstrap.user.name,
            home: bootstrap.user.home,
            productLocale: bootstrap.user.productLocale,
            timezone: bootstrap.user.timezone,
            phone: bootstrap.user.phone,
            callsEnabled: bootstrap.user.callsEnabled,
            callLanguage: bootstrap.user.callLanguage,
            calendarStatus: bootstrap.calendar.status,
            offerStatus: bootstrap.offer?.status ?? .unavailable
        )
    }
}

enum CalendarConnectionStatus: String, Codable, Equatable, Sendable {
    case connected
    case actionRequired = "action_required"
    case error
    case disconnected
}

struct CalendarConnection: Codable, Equatable, Sendable {
    let status: CalendarConnectionStatus
}

enum OfferStatus: String, Codable, Equatable, Sendable {
    case available
    case unavailable
}

struct BootstrapOffer: Codable, Equatable, Sendable {
    let status: OfferStatus
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
    let phone: String?
    let callsEnabled: Bool
    let callLanguage: ProductLocale?

    init(
        name: String?,
        home: String?,
        productLocale: ProductLocale = .en,
        phone: String? = nil,
        callsEnabled: Bool = false,
        callLanguage: ProductLocale? = nil
    ) {
        self.name = name
        self.home = home
        self.productLocale = productLocale
        self.phone = phone
        self.callsEnabled = callsEnabled
        self.callLanguage = callLanguage
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.init(
            name: try container.decodeIfPresent(String.self, forKey: .name),
            home: try container.decodeIfPresent(String.self, forKey: .home),
            productLocale: try container.decodeIfPresent(ProductLocale.self, forKey: .productLocale) ?? .en,
            phone: try container.decodeIfPresent(String.self, forKey: .phone),
            callsEnabled: try container.decodeIfPresent(Bool.self, forKey: .callsEnabled) ?? false,
            callLanguage: try container.decodeIfPresent(ProductLocale.self, forKey: .callLanguage)
        )
    }

    private enum CodingKeys: String, CodingKey {
        case name
        case home
        case productLocale
        case phone
        case callsEnabled
        case callLanguage
    }
}
