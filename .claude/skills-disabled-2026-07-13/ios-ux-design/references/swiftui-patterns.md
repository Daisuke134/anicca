# SwiftUI Patterns Reference

## View Composition

SwiftUI's natural pattern is similar to MVC:
- Views are declarative descriptions
- @State for view-local state
- @StateObject for observable model data
- @EnvironmentObject for shared data

## Navigation in SwiftUI

```swift
// Tab-based app structure
TabView {
    NavigationStack {
        HomeView()
    }
    .tabItem {
        Label("Home", systemImage: "house")
    }

    NavigationStack {
        SearchView()
    }
    .tabItem {
        Label("Search", systemImage: "magnifyingglass")
    }
}
```

## List Patterns

```swift
List {
    Section("Header") {
        ForEach(items) { item in
            NavigationLink(value: item) {
                HStack {
                    Image(systemName: item.icon)
                    VStack(alignment: .leading) {
                        Text(item.title)
                        Text(item.subtitle)
                            .foregroundStyle(.secondary)
                            .font(.caption)
                    }
                }
            }
        }
    }
}
.listStyle(.insetGrouped)
.navigationDestination(for: Item.self) { item in
    DetailView(item: item)
}
```

## Semantic Colors in SwiftUI

```swift
// Use semantic colors
Text("Title")
    .foregroundStyle(.primary) // Not .black

// Use system colors
Button("Action") { }
    .tint(.blue) // .blue adapts to dark mode

// Background hierarchy
VStack {
    // Content
}
.background(.background) // systemBackground
.background(.secondaryBackground, in: RoundedRectangle(cornerRadius: 12))
```

## SF Symbols in SwiftUI

```swift
// Basic usage
Image(systemName: "heart.fill")

// With semantic styling
Image(systemName: "star.fill")
    .symbolRenderingMode(.multicolor)
    .imageScale(.large) // small, medium, large

// Aligned with text
Label("Favorites", systemImage: "star")
```

## Standard List with Sections

```swift
struct ContentView: View {
    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(items) { item in
                        NavigationLink(value: item) {
                            Label(item.title, systemImage: item.icon)
                        }
                    }
                } header: {
                    Text("Items")
                } footer: {
                    Text("Helpful context about this section")
                }
            }
            .navigationTitle("List")
            .navigationDestination(for: Item.self) { item in
                DetailView(item: item)
            }
        }
    }
}
```

## Modal Sheet Presentation

```swift
struct ContentView: View {
    @State private var showingSheet = false

    var body: some View {
        Button("Show Settings") {
            showingSheet = true
        }
        .sheet(isPresented: $showingSheet) {
            NavigationStack {
                SettingsView()
                    .navigationTitle("Settings")
                    .navigationBarTitleDisplayMode(.inline)
                    .toolbar {
                        ToolbarItem(placement: .confirmationAction) {
                            Button("Done") {
                                showingSheet = false
                            }
                        }
                    }
            }
            .presentationDetents([.medium, .large])
        }
    }
}
```

## Form Input with Validation

```swift
struct FormView: View {
    @State private var email = ""
    @State private var password = ""

    var body: some View {
        Form {
            Section {
                TextField("Email", text: $email)
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .autocapitalization(.none)

                SecureField("Password", text: $password)
                    .textContentType(.password)
            } header: {
                Text("Account")
            } footer: {
                Text("Your email and password are securely stored")
            }

            Section {
                Button("Sign In") {
                    // Action
                }
                .disabled(email.isEmpty || password.isEmpty)
            }
        }
    }
}
```

## Context Menu Implementation

```swift
struct ItemView: View {
    let item: Item

    var body: some View {
        Text(item.title)
            .contextMenu {
                Button {
                    // Action
                } label: {
                    Label("Share", systemImage: "square.and.arrow.up")
                }

                Button(role: .destructive) {
                    // Destructive action
                } label: {
                    Label("Delete", systemImage: "trash")
                }
            }
    }
}
```

## Dark Mode — Semantic Color Strategy (Required)

Never use fixed colors. Always use:
- System semantic colors for UI elements
- Custom dynamic colors with 4 variants
- Color assets in Xcode with Appearance variants

```swift
// UIKit
let backgroundColor = UIColor { traitCollection in
    switch traitCollection.userInterfaceStyle {
    case .dark:
        return UIColor(red: 0.1, green: 0.1, blue: 0.1, alpha: 1.0)
    case .light:
        return UIColor.white
    case .unspecified:
        return UIColor.white
    @unknown default:
        return UIColor.white
    }
}
```

## Images and Assets

- Provide separate image assets for light/dark appearances
- Use SF Symbols (automatically adapt)
- PDF vectors with "Preserve Vector Data"
- Asset catalog with Appearance variants

## Materials and Blur Effects

iOS provides system materials that adapt:
- .ultraThinMaterial, .thinMaterial, .regular, .thick, .ultraThick
- Automatically adjust for appearance
- Use for overlays, sidebars, sheets
