import WidgetKit
import SwiftUI

@main
struct AniccaWidgetBundle: WidgetBundle {
    var body: some Widget {
        // Explicit returns use opaque-result availability, not builder conditionals.
        if #available(iOS 18.0, *) {
            return WidgetBundleBuilder.buildBlock(
                AniccaWidget(), AniccaWidgetLiveActivity(), AniccaWidgetControl()
            )
        } else if #available(iOS 17.0, *) {
            return WidgetBundleBuilder.buildBlock(
                AniccaWidget(), AniccaWidgetLiveActivity()
            )
        } else {
            return WidgetBundleBuilder.buildBlock(
                LegacyAniccaWidget(), AniccaWidgetLiveActivity()
            )
        }
    }
}
