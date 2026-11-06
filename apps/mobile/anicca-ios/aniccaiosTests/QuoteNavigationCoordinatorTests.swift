import Foundation
import Testing
import SwiftUI
import UIKit
@testable import aniccaios

@MainActor
struct QuoteNavigationCoordinatorTests {

    @Test("A SwiftUI refresh during a swipe must not restore the previous page")
    func refreshDuringInteractiveSwipeKeepsVisiblePage() {
        var index = 0
        let pager = VerticalPager(count: 3, currentIndex: Binding(get: { index }, set: { index = $0 })) { Text("Card \($0)") }
        let coordinator = pager.makeCoordinator()
        let controller = UIPageViewController(transitionStyle: .scroll, navigationOrientation: .vertical)
        let first = coordinator.hosting(for: 0)
        let next = coordinator.hosting(for: 1)
        controller.setViewControllers([first], direction: .forward, animated: false)
        coordinator.pageViewController(controller, willTransitionTo: [next])
        controller.setViewControllers([next], direction: .forward, animated: false)
        coordinator.synchronizeVisiblePage(controller)
        #expect((controller.viewControllers?.first as? IndexedHosting)?.index == 1)
        coordinator.pageViewController(controller, didFinishAnimating: true, previousViewControllers: [first], transitionCompleted: true)
        #expect(index == 1)
    }

    @Test("A notification requested mid-swipe wins over the gesture destination")
    func notificationDuringSwipeKeepsRequestedDestination() {
        var index = 0
        let pager = VerticalPager(count: 3, currentIndex: Binding(get: { index }, set: { index = $0 })) { Text("Card \($0)") }
        let coordinator = pager.makeCoordinator()
        let controller = UIPageViewController(transitionStyle: .scroll, navigationOrientation: .vertical)
        let first = coordinator.hosting(for: 0)
        let next = coordinator.hosting(for: 1)
        controller.setViewControllers([first], direction: .forward, animated: false)
        coordinator.pageViewController(controller, willTransitionTo: [next])
        index = 2
        controller.setViewControllers([next], direction: .forward, animated: false)
        coordinator.pageViewController(controller, didFinishAnimating: true, previousViewControllers: [first], transitionCompleted: true)
        #expect(index == 2)
        #expect((controller.viewControllers?.first as? IndexedHosting)?.index == 2)
    }

    @Test("A mid-swipe notification targeting the starting index still wins")
    func notificationToStartingIndexWins() {
        var index = 0
        let pager = VerticalPager(count: 3, currentIndex: Binding(get: { index }, set: { index = $0 })) { Text("Card \($0)") }
        let coordinator = pager.makeCoordinator()
        let controller = UIPageViewController(transitionStyle: .scroll, navigationOrientation: .vertical)
        let first = coordinator.hosting(for: 0)
        let next = coordinator.hosting(for: 1)
        controller.setViewControllers([first], direction: .forward, animated: false)
        coordinator.pageViewController(controller, willTransitionTo: [next])
        coordinator.parent.navigationRevision += 1
        controller.setViewControllers([next], direction: .forward, animated: false)
        coordinator.pageViewController(controller, didFinishAnimating: true, previousViewControllers: [first], transitionCompleted: true)
        #expect(index == 0)
        #expect((controller.viewControllers?.first as? IndexedHosting)?.index == 0)
    }

    @Test("Cold-start notification waits for quotes and follows the visible alert body")
    func coldStartUsesAlertBodyWhenQuoteIdDisagrees() {
        let suiteName = "QuoteNavigationCoordinatorTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        let storageKey = "pendingQuoteNavigation"
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let notificationHandler = QuoteNavigationCoordinator(defaults: defaults, storageKey: storageKey)
        notificationHandler.request(
            quoteID: "q001",
            alertBody: "I am exactly where I need to be in my journey."
        )

        let feedAfterColdStart = QuoteNavigationCoordinator(defaults: defaults, storageKey: storageKey)
        #expect(feedAfterColdStart.resolveQuote(in: []) == nil)
        #expect(feedAfterColdStart.pendingRequest?.quoteID == "q001")

        let quotes = [
            Quote(id: "q001", text: "I am committed to becoming who I am meant to be."),
            Quote(id: "q007", text: "I am exactly where I need to be in my journey."),
        ]
        #expect(feedAfterColdStart.resolveQuote(in: quotes) == quotes[1])
        #expect(feedAfterColdStart.pendingRequest == nil)
        #expect(defaults.data(forKey: storageKey) == nil)
    }

    @Test("An alert body absent from the catalog is shown instead of a conflicting quote ID")
    func unknownAlertBodyTakesPrecedenceOverConflictingQuoteID() {
        let suiteName = "QuoteNavigationCoordinatorTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let coordinator = QuoteNavigationCoordinator(defaults: defaults, storageKey: "pendingQuoteNavigation")
        coordinator.request(quoteID: "q001", alertBody: "A different affirmation not in this catalog.")

        let quotes = [Quote(id: "q001", text: "I am committed to becoming who I am meant to be.")]
        let resolved = coordinator.resolveQuote(in: quotes)
        #expect(resolved?.text == "A different affirmation not in this catalog.")
        #expect(resolved?.id.hasPrefix("notification:") == true)
        #expect(coordinator.pendingRequest == nil)
    }

    @Test("ID-only deep links still open the matching stable quote ID")
    func idOnlyDeepLinkKeepsExistingBehavior() {
        let suiteName = "QuoteNavigationCoordinatorTests.\(UUID().uuidString)"
        let defaults = UserDefaults(suiteName: suiteName)!
        defer { defaults.removePersistentDomain(forName: suiteName) }

        let coordinator = QuoteNavigationCoordinator(defaults: defaults, storageKey: "pendingQuoteNavigation")
        coordinator.request(quoteID: "q007", alertBody: nil)

        let quotes = [
            Quote(id: "q001", text: "First affirmation."),
            Quote(id: "q007", text: "Exact deep-link destination."),
        ]
        #expect(coordinator.resolveQuote(in: quotes) == quotes[1])
        #expect(coordinator.pendingRequest == nil)
    }
}
