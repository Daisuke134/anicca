import { useEffect, useRef, useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Dimensions,
  FlatList,
  TouchableOpacity,
  Animated,
  StatusBar,
  useColorScheme,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Settings, Bookmark, BookmarkCheck } from 'lucide-react-native';
import * as Haptics from 'expo-haptics';
import * as Localization from 'expo-localization';
import Colors from '@/constants/colors';
import { Verse, getFreeVerses, getAllVerses, getLocalizedVerse, getLocalizedSource, getLocalizedChapter } from '@/data/verses';
import { useApp } from '@/providers/AppProvider';
import { t } from '@/utils/i18n';

const { width, height } = Dimensions.get('window');

export default function MainScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { settings, isLoading, toggleBookmark, isBookmarked, isPremium } = useApp();
  const colorScheme = useColorScheme();
  const isDark = settings.darkMode || colorScheme === 'dark';
  const colors = isDark ? Colors.dark : Colors.light;

  const [currentIndex, setCurrentIndex] = useState(0);
  const flatListRef = useRef<FlatList>(null);
  const scrollY = useRef(new Animated.Value(0)).current;

  const availableVerses = isPremium ? getAllVerses() : getFreeVerses();
  const locale = Localization.getLocales()[0]?.languageTag ?? 'en';

  useEffect(() => {
    if (!isLoading && !settings.hasCompletedOnboarding) {
      console.log('[MainScreen] User has not completed onboarding, redirecting');
      router.replace('/onboarding');
    }
  }, [isLoading, settings.hasCompletedOnboarding, router]);

  const handleBookmark = useCallback((verseId: number) => {
    if (!isPremium) {
      router.push('/paywall');
      return;
    }
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    toggleBookmark(verseId);
  }, [isPremium, toggleBookmark, router]);

  const renderVerse = ({ item, index }: { item: Verse; index: number }) => {
    const inputRange = [
      (index - 1) * height,
      index * height,
      (index + 1) * height,
    ];

    const opacity = scrollY.interpolate({
      inputRange,
      outputRange: [0.3, 1, 0.3],
      extrapolate: 'clamp',
    });

    const translateY = scrollY.interpolate({
      inputRange,
      outputRange: [50, 0, -50],
      extrapolate: 'clamp',
    });

    const bookmarked = isBookmarked(item.id);

    return (
      <View style={[styles.versePage, { height, backgroundColor: colors.background }]}>
        <Animated.View
          style={[
            styles.verseContent,
            { opacity, transform: [{ translateY }] },
          ]}
        >
          <View style={styles.decorLine} />
          
          <Text style={[styles.verseText, { color: colors.text }]}>
            {getLocalizedVerse(item, locale)}
          </Text>

          <View style={styles.sourceContainer}>
            <View style={[styles.sourceDivider, { backgroundColor: colors.gold }]} />
            <Text style={[styles.sourceText, { color: colors.textSecondary }]}>
              {getLocalizedSource(item.source, locale)}
            </Text>
            <Text style={[styles.chapterText, { color: colors.textMuted }]}>
              {getLocalizedChapter(item.chapter, item.verseNumber, locale)}
            </Text>
          </View>

          <TouchableOpacity
            style={[styles.bookmarkButton, { backgroundColor: colors.backgroundSecondary }]}
            onPress={() => handleBookmark(item.id)}
            activeOpacity={0.7}
          >
            {bookmarked ? (
              <BookmarkCheck size={22} color={colors.gold} />
            ) : (
              <Bookmark size={22} color={colors.textMuted} />
            )}
          </TouchableOpacity>
        </Animated.View>

        <View style={styles.swipeHint}>
          <Text style={[styles.swipeHintText, { color: colors.textMuted }]}>
            {t('index.swipeHint')}
          </Text>
        </View>
      </View>
    );
  };

  if (isLoading) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: colors.background }]}>
        <Text style={[styles.loadingText, { color: colors.textMuted }]}>...</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      
      <View style={[styles.header, { paddingTop: insets.top + 8 }]}>
        <View style={styles.headerLeft}>
          <Text style={[styles.headerTitle, { color: colors.textMuted }]}>
            {t('index.title')}
          </Text>
        </View>
        <TouchableOpacity
          style={[styles.settingsButton, { backgroundColor: colors.backgroundSecondary }]}
          onPress={() => router.push('/settings')}
          activeOpacity={0.7}
        >
          <Settings size={20} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>

      <Animated.FlatList
        ref={flatListRef}
        data={availableVerses}
        renderItem={renderVerse}
        keyExtractor={(item) => item.id.toString()}
        pagingEnabled
        showsVerticalScrollIndicator={false}
        snapToInterval={height}
        decelerationRate="fast"
        onScroll={Animated.event(
          [{ nativeEvent: { contentOffset: { y: scrollY } } }],
          { useNativeDriver: true }
        )}
        onMomentumScrollEnd={(e) => {
          const index = Math.round(e.nativeEvent.contentOffset.y / height);
          if (index !== currentIndex) {
            setCurrentIndex(index);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
          }
        }}
        scrollEventThrottle={16}
        getItemLayout={(_, index) => ({
          length: height,
          offset: height * index,
          index,
        })}
      />

      <View style={[styles.pageIndicator, { bottom: insets.bottom + 24 }]}>
        <Text style={[styles.pageIndicatorText, { color: colors.textMuted }]}>
          {currentIndex + 1} / {availableVerses.length}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    fontSize: 24,
  },
  header: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  headerLeft: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 14,
    fontWeight: '500',
    letterSpacing: 1,
    textTransform: 'uppercase',
  },
  settingsButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  versePage: {
    width: width,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  verseContent: {
    alignItems: 'center',
    maxWidth: 600,
  },
  decorLine: {
    width: 40,
    height: 2,
    backgroundColor: Colors.light.gold,
    marginBottom: 32,
    borderRadius: 1,
  },
  verseText: {
    fontSize: 26,
    fontWeight: '300',
    lineHeight: 40,
    textAlign: 'center',
    letterSpacing: -0.3,
    fontStyle: 'italic',
  },
  sourceContainer: {
    alignItems: 'center',
    marginTop: 40,
  },
  sourceDivider: {
    width: 24,
    height: 1,
    marginBottom: 16,
  },
  sourceText: {
    fontSize: 15,
    fontWeight: '500',
    marginBottom: 4,
  },
  chapterText: {
    fontSize: 13,
  },
  bookmarkButton: {
    marginTop: 32,
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  swipeHint: {
    position: 'absolute',
    bottom: 100,
  },
  swipeHintText: {
    fontSize: 13,
    letterSpacing: 0.5,
  },
  pageIndicator: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  pageIndicatorText: {
    fontSize: 12,
    letterSpacing: 1,
  },
});
