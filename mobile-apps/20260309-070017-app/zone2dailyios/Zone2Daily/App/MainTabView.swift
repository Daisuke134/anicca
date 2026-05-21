// File: App/MainTabView.swift
// Main tab bar — Dashboard | Workout | Settings

import SwiftUI

struct MainTabView: View {
    var body: some View {
        TabView {
            DashboardView()
                .tabItem {
                    Label("Dashboard", systemImage: "chart.bar.fill")
                }
                .accessibilityIdentifier("tab_dashboard")

            WorkoutTimerView()
                .tabItem {
                    Label("Workout", systemImage: "timer")
                }
                .accessibilityIdentifier("tab_workout")

            SettingsView()
                .tabItem {
                    Label("Settings", systemImage: "gear")
                }
                .accessibilityIdentifier("tab_settings")
        }
    }
}
