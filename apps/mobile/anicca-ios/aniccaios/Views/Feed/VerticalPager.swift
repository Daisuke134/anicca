import SwiftUI
import UIKit

/// Vertical full-screen paging via UIPageViewController.
/// Used by FeedRootView to swipe through quote cards top-to-bottom (1:1 i.am app pattern).
struct VerticalPager<Page: View>: UIViewControllerRepresentable {
    let count: Int
    @Binding var currentIndex: Int
    var navigationRevision: Int = 0
    let pageContent: (Int) -> Page

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIViewController(context: Context) -> UIPageViewController {
        let pvc = UIPageViewController(
            transitionStyle: .scroll,
            navigationOrientation: .vertical,
            options: nil
        )
        pvc.dataSource = context.coordinator
        pvc.delegate = context.coordinator
        pvc.view.backgroundColor = UIColor.clear

        for view in pvc.view.subviews {
            if let scroll = view as? UIScrollView {
                scroll.backgroundColor = UIColor.clear
            }
        }

        if count > 0 {
            let first = context.coordinator.hosting(for: clampedIndex(currentIndex))
            pvc.setViewControllers([first], direction: .forward, animated: false)
        }
        return pvc
    }

    func updateUIViewController(_ pvc: UIPageViewController, context: Context) {
        context.coordinator.parent = self
        context.coordinator.synchronizeVisiblePage(pvc)
    }

    private func clampedIndex(_ i: Int) -> Int {
        min(max(0, i), max(0, count - 1))
    }

    final class Coordinator: NSObject, UIPageViewControllerDataSource, UIPageViewControllerDelegate {
        var parent: VerticalPager
        private var interactiveStartIndex: Int?
        private var interactiveStartRevision: Int?

        init(_ parent: VerticalPager) { self.parent = parent }

        // Avoid the Swift 6.3 optimizer crash in the synthesized MainActor deinitializer.
        deinit {}

        func synchronizeVisiblePage(_ pvc: UIPageViewController) {
            // During a gesture UIKit can expose the destination before the binding
            // commits. Reapplying the old binding here cancels an otherwise valid swipe.
            guard interactiveStartIndex == nil, parent.count > 0 else { return }
            let target = parent.clampedIndex(parent.currentIndex)
            let current = pvc.viewControllers?.first as? IndexedHosting
            guard current?.index != target else { return }
            let direction: UIPageViewController.NavigationDirection = (current?.index ?? 0) < target ? .forward : .reverse
            pvc.setViewControllers([hosting(for: target)], direction: direction, animated: false)
        }

        func pageViewController(_ pvc: UIPageViewController, willTransitionTo pendingViewControllers: [UIViewController]) {
            interactiveStartIndex = parent.currentIndex
            interactiveStartRevision = parent.navigationRevision
        }

        func hosting(for index: Int) -> IndexedHosting {
            let host = IndexedHosting(index: index, rootView: AnyView(parent.pageContent(index)))
            host.view.backgroundColor = UIColor.clear
            if #available(iOS 16.0, *) {
                host.sizingOptions = []
            }
            host.view.translatesAutoresizingMaskIntoConstraints = true
            host.view.autoresizingMask = [.flexibleWidth, .flexibleHeight]
            return host
        }

        func pageViewController(_ pvc: UIPageViewController,
                                viewControllerBefore vc: UIViewController) -> UIViewController? {
            guard let host = vc as? IndexedHosting, host.index > 0 else { return nil }
            return hosting(for: host.index - 1)
        }

        func pageViewController(_ pvc: UIPageViewController,
                                viewControllerAfter vc: UIViewController) -> UIViewController? {
            guard let host = vc as? IndexedHosting,
                  host.index + 1 < parent.count else { return nil }
            return hosting(for: host.index + 1)
        }

        func pageViewController(_ pvc: UIPageViewController,
                                didFinishAnimating finished: Bool,
                                previousViewControllers: [UIViewController],
                                transitionCompleted completed: Bool) {
            let startIndex = interactiveStartIndex
            let startRevision = interactiveStartRevision
            interactiveStartIndex = nil
            interactiveStartRevision = nil
            // An explicit notification/deep-link request takes precedence over
            // a swipe that was already in progress when that request arrived.
            if let startIndex, parent.currentIndex != startIndex || parent.navigationRevision != startRevision {
                synchronizeVisiblePage(pvc)
                return
            }
            guard completed,
                  let host = pvc.viewControllers?.first as? IndexedHosting else { return }
            if parent.currentIndex != host.index {
                parent.currentIndex = host.index
            }
        }
    }
}

final class IndexedHosting: UIHostingController<AnyView> {
    let index: Int
    init(index: Int, rootView: AnyView) {
        self.index = index
        super.init(rootView: rootView)
    }
    @MainActor required dynamic init?(coder aDecoder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
}
