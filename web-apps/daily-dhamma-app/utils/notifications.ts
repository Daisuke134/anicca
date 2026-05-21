import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import * as Localization from 'expo-localization';
import { getDailyVerse, stayPresentMessages, stayPresentMessagesJa, getLocalizedVerse } from '@/data/verses';

function getDeviceLocale(): string {
  return Localization.getLocales()[0]?.languageTag ?? 'en';
}

// 日付とインデックスに基づいてメッセージを選択（毎日変わる）
function getStayPresentMessage(dayOffset: number, index: number, locale: string): string {
  const lang = locale.toLowerCase().split('-')[0];
  const messages = lang === 'ja' ? stayPresentMessagesJa : stayPresentMessages;
  return messages[(dayOffset + index) % messages.length];
}

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldPlaySound: false,
    shouldSetBadge: false,
    shouldShowBanner: true,
    shouldShowList: true,
  }),
});

export async function scheduleMorningVerseNotification(time: string, isPremium: boolean) {
  if (Platform.OS === 'web') {
    console.log('[Notifications] Web platform - skipping morning verse notification');
    return;
  }

  console.log('[Notifications] Scheduling morning verse notification for:', time);

  // 既存のmorning-verse通知をすべてキャンセル
  const existingNotifications = await Notifications.getAllScheduledNotificationsAsync();
  const morningVerseIds = existingNotifications
    .filter(n => n.identifier.startsWith('morning-verse'))
    .map(n => n.identifier);

  for (const id of morningVerseIds) {
    await Notifications.cancelScheduledNotificationAsync(id);
  }

  const locale = getDeviceLocale();
  const [hours, minutes] = time.split(':').map(Number);
  const daysToSchedule = 7; // 7日分をスケジュール（morning notificationsは合計数が少ないため固定7日）

  for (let day = 0; day < daysToSchedule; day++) {
    // 通知日時を計算
    const triggerDate = new Date();
    triggerDate.setDate(triggerDate.getDate() + day);
    triggerDate.setHours(hours, minutes, 0, 0);

    // 過去の時刻はスキップ
    if (triggerDate <= new Date()) {
      continue;
    }

    // 日付に基づいてverseを取得（未来の日付を渡して毎日異なるverseに）
    const verse = getDailyVerse(isPremium, triggerDate);

    await Notifications.scheduleNotificationAsync({
      identifier: `morning-verse-${day}`,
      content: {
        title: 'Daily Dhamma',
        body: getLocalizedVerse(verse, locale),
        data: { verseId: verse.id },
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: triggerDate,
      },
    });
  }

  console.log('[Notifications] Morning verse notifications scheduled for', daysToSchedule, 'days');
}

export async function scheduleStayPresentNotifications(frequency: number, isPremium: boolean) {
  if (Platform.OS === 'web') {
    console.log('[Notifications] Web platform - skipping stay present notifications');
    return;
  }

  const locale = getDeviceLocale();
  const actualFrequency = isPremium ? frequency : Math.min(frequency, 3);
  // iOS上限64通知を超えないよう daysToSchedule を動的計算
  // 合計 = morning(daysToSchedule) + stayPresent(frequency × daysToSchedule) ≤ 60
  // → daysToSchedule ≤ 60 / (frequency + 1)
  const daysToSchedule = Math.min(7, Math.floor(60 / (actualFrequency + 1)));

  console.log('[Notifications] Scheduling', actualFrequency, 'stay present notifications for', daysToSchedule, 'days');

  // 既存のstay-present通知をすべてキャンセル
  const existingNotifications = await Notifications.getAllScheduledNotificationsAsync();
  const stayPresentIds = existingNotifications
    .filter(n => n.identifier.startsWith('stay-present-'))
    .map(n => n.identifier);

  for (const id of stayPresentIds) {
    await Notifications.cancelScheduledNotificationAsync(id);
  }

  const wakeHour = 8;
  const sleepHour = 21;
  const availableHours = sleepHour - wakeHour;
  const interval = availableHours / actualFrequency;

  // 7日分の通知をスケジュール
  for (let day = 0; day < daysToSchedule; day++) {
    for (let i = 0; i < actualFrequency; i++) {
      const baseHour = wakeHour + (interval * i) + (interval / 2);
      const hour = Math.floor(baseHour);
      const minute = Math.floor((baseHour - hour) * 60) + Math.floor(Math.random() * 30);

      // 日付とインデックスに基づいてメッセージを選択（毎日変わる）
      const message = getStayPresentMessage(day, i, locale);

      // 通知日時を計算
      const triggerDate = new Date();
      triggerDate.setDate(triggerDate.getDate() + day);
      triggerDate.setHours(hour, Math.min(minute, 59), 0, 0);

      // 過去の時刻はスキップ
      if (triggerDate <= new Date()) {
        continue;
      }

      await Notifications.scheduleNotificationAsync({
        identifier: `stay-present-${day}-${i}`,
        content: {
          title: 'Daily Dhamma',
          body: message,
        },
        trigger: {
          type: Notifications.SchedulableTriggerInputTypes.DATE,
          date: triggerDate,
        },
      });
    }
  }

  console.log('[Notifications] Stay present notifications scheduled');
}

export async function cancelAllNotifications() {
  if (Platform.OS === 'web') return;

  console.log('[Notifications] Cancelling all notifications');
  await Notifications.cancelAllScheduledNotificationsAsync();
}

export async function getNotificationPermissionStatus() {
  if (Platform.OS === 'web') return 'granted';

  const { status } = await Notifications.getPermissionsAsync();
  return status;
}
