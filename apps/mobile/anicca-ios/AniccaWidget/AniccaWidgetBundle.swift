import WidgetKit
import SwiftUI

@main
struct AniccaWidgetBundle: WidgetBundle {
    var body: some Widget {
        // The sample timer control was removed: ControlWidget is not a Widget
        // accepted by this WidgetBundleBuilder.buildBlock overload.
        if #available(iOS 17.0, *) {
            return WidgetBundleBuilder.buildBlock(
                AniccaWidget(), AniccaWidgetLiveActivity()
            )
        }
        return WidgetBundleBuilder.buildBlock(
            LegacyAniccaWidget(), AniccaWidgetLiveActivity()
        )
    }
}
