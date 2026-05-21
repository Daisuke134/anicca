import SwiftUI
import SwiftData

struct HistoryView: View {
    let viewModel: AppViewModel
    @Query(sort: \GratitudeEntry.date, order: .reverse) private var entries: [GratitudeEntry]
    @State private var selectedDate: Date = Date()
    @State private var displayedMonth: Date = Date()

    private var language: AppLanguage { viewModel.language }

    private var entryDates: Set<String> {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return Set(entries.map { formatter.string(from: $0.date) })
    }

    private var selectedEntry: GratitudeEntry? {
        let calendar = Calendar.current
        let selected = calendar.startOfDay(for: selectedDate)
        return entries.first { calendar.startOfDay(for: $0.date) == selected }
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    calendarSection
                    if let entry = selectedEntry {
                        selectedEntryCard(entry)
                    }
                    recentEntriesList
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 32)
                .frame(maxWidth: 700)
                .frame(maxWidth: .infinity)
            }
            .background(
                LinearGradient(
                    colors: [Color(red: 1.0, green: 0.98, blue: 0.95), Color(red: 0.99, green: 0.94, blue: 0.88)],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .ignoresSafeArea()
            )
            .navigationTitle(L10n.historyTab(language))
            .navigationBarTitleDisplayMode(.large)
        }
    }

    private var calendarSection: some View {
        VStack(spacing: 16) {
            HStack {
                Button {
                    withAnimation {
                        displayedMonth = Calendar.current.date(byAdding: .month, value: -1, to: displayedMonth) ?? displayedMonth
                    }
                } label: {
                    Image(systemName: "chevron.left")
                        .font(.body.weight(.semibold))
                        .foregroundStyle(Color(red: 0.83, green: 0.65, blue: 0.46))
                }

                Spacer()

                Text(displayedMonth, format: .dateTime.month(.wide).year())
                    .font(.headline)

                Spacer()

                Button {
                    withAnimation {
                        displayedMonth = Calendar.current.date(byAdding: .month, value: 1, to: displayedMonth) ?? displayedMonth
                    }
                } label: {
                    Image(systemName: "chevron.right")
                        .font(.body.weight(.semibold))
                        .foregroundStyle(Color(red: 0.83, green: 0.65, blue: 0.46))
                }
            }

            let daysInMonth = calendarDays(for: displayedMonth)
            let weekdays = language == .japanese
                ? ["日", "月", "火", "水", "木", "金", "土"]
                : ["S", "M", "T", "W", "T", "F", "S"]

            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 7), spacing: 8) {
                ForEach(weekdays, id: \.self) { day in
                    Text(day)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.secondary)
                }

                ForEach(daysInMonth, id: \.self) { date in
                    if let date {
                        let formatter = DateFormatter()
                        let _ = formatter.dateFormat = "yyyy-MM-dd"
                        let dateStr = formatter.string(from: date)
                        let hasEntry = entryDates.contains(dateStr)
                        let isSelected = Calendar.current.isDate(date, inSameDayAs: selectedDate)
                        let isToday = Calendar.current.isDateInToday(date)

                        Button {
                            selectedDate = date
                        } label: {
                            VStack(spacing: 2) {
                                Text("\(Calendar.current.component(.day, from: date))")
                                    .font(.subheadline.weight(isToday ? .bold : .regular))
                                    .foregroundStyle(isSelected ? .white : (isToday ? Color(red: 0.83, green: 0.65, blue: 0.46) : .primary))

                                Circle()
                                    .fill(hasEntry ? Color(red: 0.49, green: 0.71, blue: 0.62) : .clear)
                                    .frame(width: 5, height: 5)
                            }
                            .frame(height: 40)
                            .frame(maxWidth: .infinity)
                            .background(
                                Circle()
                                    .fill(isSelected ? Color(red: 0.83, green: 0.65, blue: 0.46) : .clear)
                                    .frame(width: 36, height: 36)
                            )
                        }
                        .buttonStyle(.plain)
                    } else {
                        Color.clear
                            .frame(height: 40)
                    }
                }
            }
        }
        .padding(16)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(.rect(cornerRadius: 16))
    }

    private func selectedEntryCard(_ entry: GratitudeEntry) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(entry.date, format: .dateTime.weekday(.wide).month(.abbreviated).day())
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(Color(red: 0.83, green: 0.65, blue: 0.46))

            if !entry.gratitude1.isEmpty {
                gratitudeRow(number: 1, text: entry.gratitude1)
            }
            if !entry.gratitude2.isEmpty {
                gratitudeRow(number: 2, text: entry.gratitude2)
            }
            if !entry.gratitude3.isEmpty {
                gratitudeRow(number: 3, text: entry.gratitude3)
            }

            if !entry.affirmation.isEmpty {
                Divider()
                HStack(spacing: 8) {
                    Image(systemName: "sparkles")
                        .font(.caption)
                        .foregroundStyle(Color(red: 0.49, green: 0.71, blue: 0.62))
                    Text(entry.affirmation)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .italic()
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground))
        .clipShape(.rect(cornerRadius: 16))
    }

    private func gratitudeRow(number: Int, text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Text("\(number)")
                .font(.caption.bold())
                .foregroundStyle(.white)
                .frame(width: 22, height: 22)
                .background(Color(red: 0.83, green: 0.65, blue: 0.46))
                .clipShape(Circle())

            Text(text)
                .font(.body)
        }
    }

    private var recentEntriesList: some View {
        VStack(alignment: .leading, spacing: 12) {
            if !entries.isEmpty {
                Text(L10n.recentEntries(language))
                    .font(.headline)
                    .padding(.top, 4)

                ForEach(entries.prefix(10)) { entry in
                    Button {
                        selectedDate = entry.date
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(entry.date, format: .dateTime.month(.abbreviated).day().weekday(.abbreviated))
                                    .font(.subheadline.weight(.medium))
                                Text(entry.gratitude1.isEmpty ? entry.gratitude2 : entry.gratitude1)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            }
                            Spacer()
                            Image(systemName: "chevron.right")
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                        .padding(14)
                        .background(Color(.secondarySystemGroupedBackground))
                        .clipShape(.rect(cornerRadius: 12))
                    }
                    .buttonStyle(.plain)
                }
            } else {
                ContentUnavailableView(
                    L10n.noEntries(language),
                    systemImage: "book.closed",
                    description: Text(language == .english ? "Start writing your gratitude journal" : "感謝日記を書き始めましょう")
                )
            }
        }
    }

    private func calendarDays(for month: Date) -> [Date?] {
        let calendar = Calendar.current
        let range = calendar.range(of: .day, in: .month, for: month)!
        let firstDay = calendar.date(from: calendar.dateComponents([.year, .month], from: month))!
        let weekday = calendar.component(.weekday, from: firstDay)
        let offset = weekday - calendar.firstWeekday
        let adjustedOffset = offset < 0 ? offset + 7 : offset

        var days: [Date?] = Array(repeating: nil, count: adjustedOffset)

        for day in range {
            if let date = calendar.date(byAdding: .day, value: day - 1, to: firstDay) {
                days.append(date)
            }
        }

        return days
    }
}
