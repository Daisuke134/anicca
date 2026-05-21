import { View, Text, StyleSheet, TouchableOpacity, Switch, ScrollView, Linking, Alert } from 'react-native';
import { useRouter, Stack } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ChevronLeft, Bell, Sun, Moon, Clock, ExternalLink, Crown, Info, Shield, FileText, FlaskConical, Sunrise, RotateCcw } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import * as Notifications from 'expo-notifications';
import * as Localization from 'expo-localization';
import Colors from '@/constants/colors';
import { useApp } from '@/providers/AppProvider';
import { getDailyVerse, getLocalizedVerse, stayPresentMessages, stayPresentMessagesJa } from '@/data/verses';
import { t } from '@/utils/i18n';

export default function SettingsScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { settings, updateSettings, isPremium } = useApp();
  const colors = settings.darkMode ? Colors.dark : Colors.light;

  const handleFrequencyChange = (frequency: 3 | 5 | 7 | 10) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    updateSettings({ notificationFrequency: frequency });
  };

  const handleDarkModeToggle = (value: boolean) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    updateSettings({ darkMode: value });
  };

  const handleNotificationsToggle = async (value: boolean) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

    if (value) {
      // 通知を有効化 - 権限がない場合はリクエスト
      const { status } = await Notifications.getPermissionsAsync();
      if (status !== 'granted') {
        const { status: newStatus } = await Notifications.requestPermissionsAsync();
        if (newStatus !== 'granted') {
          // 権限が拒否された場合は設定を変更しない
          return;
        }
      }
    }

    updateSettings({ notificationsEnabled: value });
  };

  const FrequencyButton = ({ value, label }: { value: 3 | 5 | 7 | 10; label: string }) => {
    const isSelected = settings.notificationFrequency === value;
    return (
      <TouchableOpacity
        style={[
          styles.frequencyButton,
          {
            backgroundColor: isSelected ? colors.gold : colors.backgroundSecondary,
            borderColor: isSelected ? colors.gold : colors.border,
          },
        ]}
        onPress={() => handleFrequencyChange(value)}
        activeOpacity={0.7}
      >
        <Text
          style={[
            styles.frequencyButtonText,
            { color: isSelected ? Colors.light.background : colors.textSecondary },
          ]}
        >
          {label}
        </Text>
      </TouchableOpacity>
    );
  };

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Stack.Screen
        options={{
          headerShown: true,
          headerTitle: t('settings.title'),
          headerStyle: { backgroundColor: colors.background },
          headerTintColor: colors.text,
          headerShadowVisible: false,
          headerLeft: () => (
            <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
              <ChevronLeft size={24} color={colors.text} />
            </TouchableOpacity>
          ),
        }}
      />

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 24 }]}
        showsVerticalScrollIndicator={false}
      >
        {!isPremium && (
          <TouchableOpacity
            style={[styles.premiumBanner, { backgroundColor: colors.gold }]}
            onPress={() => router.push('/paywall')}
            activeOpacity={0.8}
          >
            <Crown size={24} color={Colors.light.background} />
            <View style={styles.premiumBannerText}>
              <Text style={styles.premiumTitle}>{t('settings.premium.title')}</Text>
              <Text style={styles.premiumSubtitle}>{t('settings.premium.subtitle')}</Text>
            </View>
            <ChevronLeft size={20} color={Colors.light.background} style={{ transform: [{ rotate: '180deg' }] }} />
          </TouchableOpacity>
        )}

        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{t('settings.section.appearance')}</Text>
          <View style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border }]}>
            <View style={styles.settingLeft}>
              {settings.darkMode ? (
                <Moon size={20} color={colors.textSecondary} />
              ) : (
                <Sun size={20} color={colors.textSecondary} />
              )}
              <Text style={[styles.settingLabel, { color: colors.text }]}>{t('settings.darkMode')}</Text>
            </View>
            <Switch
              value={settings.darkMode}
              onValueChange={handleDarkModeToggle}
              trackColor={{ false: colors.border, true: colors.gold }}
              thumbColor={Colors.light.background}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{t('settings.section.notifications')}</Text>
          <View style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border }]}>
            <View style={styles.settingLeft}>
              <Bell size={20} color={colors.textSecondary} />
              <Text style={[styles.settingLabel, { color: colors.text }]}>{t('settings.enableNotifications')}</Text>
            </View>
            <Switch
              value={settings.notificationsEnabled}
              onValueChange={handleNotificationsToggle}
              trackColor={{ false: colors.border, true: colors.gold }}
              thumbColor={Colors.light.background}
            />
          </View>
          <Text style={[styles.notificationHint, { color: colors.textMuted }]}>
            {t('settings.notificationsHint')}
          </Text>
        </View>

        {settings.notificationsEnabled && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{t('settings.section.stayPresent')}</Text>
          <View style={[styles.settingCard, { backgroundColor: colors.card, borderColor: colors.border }]}>
            <View style={styles.settingCardHeader}>
              <Bell size={20} color={colors.textSecondary} />
              <Text style={[styles.settingLabel, { color: colors.text }]}>{t('settings.dailyFrequency')}</Text>
            </View>
            <Text style={[styles.settingDescription, { color: colors.textMuted }]}>
              {t('settings.frequencyHint')}
            </Text>
            {isPremium ? (
              <View style={styles.frequencyButtons}>
                <FrequencyButton value={3} label={t('settings.freq.x3')} />
                <FrequencyButton value={5} label={t('settings.freq.x5')} />
                <FrequencyButton value={7} label={t('settings.freq.x7')} />
                <FrequencyButton value={10} label={t('settings.freq.x10')} />
              </View>
            ) : (
              <View style={styles.frequencyFixed}>
                <Text style={[styles.frequencyFixedText, { color: colors.text }]}>
                  {t('settings.frequencyFixed')}
                </Text>
                <TouchableOpacity onPress={() => router.push('/paywall')}>
                  <Text style={[styles.upgradeLink, { color: colors.gold }]}>
                    {t('settings.upgradeForMore')}
                  </Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </View>
        )}

        {settings.notificationsEnabled && (
        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{t('settings.section.morningVerse')}</Text>
          <View style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border }]}>
            <View style={styles.settingLeft}>
              <Clock size={20} color={colors.textSecondary} />
              <Text style={[styles.settingLabel, { color: colors.text }]}>{t('settings.notificationTime')}</Text>
            </View>
            <Text style={[styles.settingValue, { color: colors.textMuted }]}>
              {settings.morningNotificationTime}
            </Text>
          </View>
        </View>
        )}

        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{t('settings.section.about')}</Text>
          <TouchableOpacity
            style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border }]}
            onPress={() => Linking.openURL('https://en.wikipedia.org/wiki/Dhammapada')}
            activeOpacity={0.7}
          >
            <View style={styles.settingLeft}>
              <Info size={20} color={colors.textSecondary} />
              <Text style={[styles.settingLabel, { color: colors.text }]}>{t('settings.aboutDhammapada')}</Text>
            </View>
            <ExternalLink size={18} color={colors.textMuted} />
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{t('settings.section.legal')}</Text>
          <TouchableOpacity
            style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border, marginBottom: 8 }]}
            onPress={() => Linking.openURL('https://aniccaai.com/dailydharma/privacy')}
            activeOpacity={0.7}
          >
            <View style={styles.settingLeft}>
              <Shield size={20} color={colors.textSecondary} />
              <Text style={[styles.settingLabel, { color: colors.text }]}>{t('settings.privacyPolicy')}</Text>
            </View>
            <ExternalLink size={18} color={colors.textMuted} />
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border }]}
            onPress={() => Linking.openURL('https://www.apple.com/legal/internet-services/itunes/dev/stdeula/')}
            activeOpacity={0.7}
          >
            <View style={styles.settingLeft}>
              <FileText size={20} color={colors.textSecondary} />
              <Text style={[styles.settingLabel, { color: colors.text }]}>{t('settings.termsOfService')}</Text>
            </View>
            <ExternalLink size={18} color={colors.textMuted} />
          </TouchableOpacity>
        </View>

        {__DEV__ && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>DEVELOPER</Text>

            {/* Test Morning Verse */}
            <TouchableOpacity
              style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border, marginBottom: 8 }]}
              onPress={async () => {
                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                const verse = getDailyVerse(isPremium);
                const locale = Localization.getLocales()[0]?.languageTag ?? 'en';
                const localizedText = getLocalizedVerse(verse, locale);
                const body = localizedText.length > 100
                  ? localizedText.substring(0, 100) + '...'
                  : localizedText;

                await Notifications.scheduleNotificationAsync({
                  content: {
                    title: 'Daily Dhamma ☀️',
                    body: body,
                    data: { verseId: verse.id },
                  },
                  trigger: null,
                });

                Alert.alert('Morning Verse Test', `✅ Sent!\n\n"${body}"`);
              }}
              activeOpacity={0.7}
            >
              <View style={styles.settingLeft}>
                <Sunrise size={20} color={colors.gold} />
                <Text style={[styles.settingLabel, { color: colors.text }]}>Test Morning Verse</Text>
              </View>
            </TouchableOpacity>

            {/* Test Stay Present */}
            <TouchableOpacity
              style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border, marginBottom: 8 }]}
              onPress={async () => {
                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                const stayLocale = Localization.getLocales()[0]?.languageTag ?? 'en';
                const stayLang = stayLocale.toLowerCase().split('-')[0];
                const msgs = stayLang === 'ja' ? stayPresentMessagesJa : stayPresentMessages;
                const message = msgs[Math.floor(Math.random() * msgs.length)];

                await Notifications.scheduleNotificationAsync({
                  content: {
                    title: 'Daily Dhamma 🧘',
                    body: message,
                  },
                  trigger: null,
                });

                Alert.alert('Stay Present Test', `✅ Sent!\n\n"${message}"`);
              }}
              activeOpacity={0.7}
            >
              <View style={styles.settingLeft}>
                <Bell size={20} color={colors.gold} />
                <Text style={[styles.settingLabel, { color: colors.text }]}>Test Stay Present</Text>
              </View>
            </TouchableOpacity>

            {/* Show Scheduled Notifications */}
            <TouchableOpacity
              style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border, marginBottom: 8 }]}
              onPress={async () => {
                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
                const scheduled = await Notifications.getAllScheduledNotificationsAsync();

                console.log('[Test] Scheduled notifications count:', scheduled.length);
                scheduled.forEach((n, i) => {
                  console.log(`[Test] Notification ${i + 1}:`, {
                    id: n.identifier,
                    title: n.content.title,
                    body: n.content.body,
                    trigger: n.trigger,
                  });
                });

                const summary = scheduled.map(n => {
                  const trigger = n.trigger as { dateComponents?: { hour?: number; minute?: number } };
                  const time = trigger.dateComponents
                    ? `${trigger.dateComponents.hour}:${String(trigger.dateComponents.minute).padStart(2, '0')}`
                    : 'unknown';
                  return `• ${time} - ${n.identifier}`;
                }).join('\n');

                Alert.alert(
                  'Scheduled Notifications',
                  `📋 ${scheduled.length} notifications\n\n${summary}\n\nCheck console for details.`
                );
              }}
              activeOpacity={0.7}
            >
              <View style={styles.settingLeft}>
                <FlaskConical size={20} color={colors.gold} />
                <Text style={[styles.settingLabel, { color: colors.text }]}>Show Scheduled</Text>
              </View>
            </TouchableOpacity>

            {/* Reset Onboarding */}
            <TouchableOpacity
              style={[styles.settingRow, { backgroundColor: colors.card, borderColor: colors.border }]}
              onPress={() => {
                Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
                Alert.alert(
                  'Reset Onboarding',
                  'This will reset the app to show onboarding again. The app will close.',
                  [
                    { text: 'Cancel', style: 'cancel' },
                    {
                      text: 'Reset',
                      style: 'destructive',
                      onPress: () => {
                        updateSettings({ hasCompletedOnboarding: false });
                        Alert.alert('Done', 'Restart the app to see onboarding.');
                      },
                    },
                  ]
                );
              }}
              activeOpacity={0.7}
            >
              <View style={styles.settingLeft}>
                <RotateCcw size={20} color="#FF6B6B" />
                <Text style={[styles.settingLabel, { color: '#FF6B6B' }]}>Reset Onboarding</Text>
              </View>
            </TouchableOpacity>
          </View>
        )}

        <Text style={[styles.versionText, { color: colors.textMuted }]}>
          {t('settings.version')}
        </Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  backButton: {
    padding: 4,
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 20,
  },
  premiumBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 16,
    marginBottom: 24,
    gap: 12,
  },
  premiumBannerText: {
    flex: 1,
  },
  premiumTitle: {
    fontSize: 17,
    fontWeight: '600',
    color: Colors.light.background,
  },
  premiumSubtitle: {
    fontSize: 13,
    color: Colors.light.background,
    opacity: 0.9,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: '600',
    letterSpacing: 1,
    marginBottom: 12,
    marginLeft: 4,
  },
  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  settingLabel: {
    fontSize: 16,
  },
  settingValue: {
    fontSize: 16,
  },
  settingCard: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
  },
  settingCardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 8,
  },
  settingDescription: {
    fontSize: 14,
    marginBottom: 16,
    marginLeft: 32,
  },
  notificationHint: {
    fontSize: 13,
    marginTop: 8,
    marginLeft: 4,
  },
  frequencyButtons: {
    flexDirection: 'row',
    gap: 12,
    marginLeft: 32,
  },
  frequencyButton: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 10,
    alignItems: 'center',
    borderWidth: 1,
  },
  frequencyButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  frequencyFixed: {
    marginLeft: 32,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  frequencyFixedText: {
    fontSize: 16,
    fontWeight: '600',
  },
  upgradeLink: {
    fontSize: 14,
    textDecorationLine: 'underline',
  },
  versionText: {
    textAlign: 'center',
    fontSize: 13,
    marginTop: 24,
  },
});
