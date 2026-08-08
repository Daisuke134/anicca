import SwiftUI

struct RootView: View {
    let environment: AppEnvironment

    var body: some View {
        VStack {
            Text("Life Manager")
                .font(.largeTitle)
                .fontWeight(.semibold)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
