import { useEffect, useState } from 'react';
import { Platform } from 'react-native';
import Purchases, {
  PurchasesPackage,
  CustomerInfo,
  LOG_LEVEL,
  PURCHASES_ERROR_CODE
} from 'react-native-purchases';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import createContextHook from '@nkzw/create-context-hook';

function getRCToken() {
  if (__DEV__ || Platform.OS === 'web') {
    return process.env.EXPO_PUBLIC_REVENUECAT_TEST_API_KEY;
  }
  return Platform.select({
    ios: process.env.EXPO_PUBLIC_REVENUECAT_IOS_API_KEY,
    android: process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY,
    default: process.env.EXPO_PUBLIC_REVENUECAT_TEST_API_KEY,
  });
}

const apiKey = getRCToken();

if (apiKey) {
  console.log('[RevenueCat] Configuring with API key');
  Purchases.setLogLevel(LOG_LEVEL.DEBUG);
  Purchases.configure({ apiKey });
} else {
  console.warn('[RevenueCat] No API key found');
}

export const [RevenueCatProvider, useRevenueCat] = createContextHook(() => {
  const queryClient = useQueryClient();
  const [isConfigured] = useState(!!apiKey);
  const [isPremium, setIsPremium] = useState(false);

  const customerInfoQuery = useQuery({
    queryKey: ['revenuecat-customer-info', isConfigured],
    queryFn: async () => {
      if (!isConfigured) {
        console.log('[RevenueCat] Not configured, returning null');
        return null;
      }
      console.log('[RevenueCat] Fetching customer info');
      const info = await Purchases.getCustomerInfo();
      const hasAccess = typeof info.entitlements.active['premium'] !== 'undefined';
      setIsPremium(hasAccess);
      console.log('[RevenueCat] Customer info, isPremium:', hasAccess);
      return info;
    },
    enabled: isConfigured,
    staleTime: 1000 * 60 * 5,
  });

  const offeringsQuery = useQuery({
    queryKey: ['revenuecat-offerings', isConfigured],
    queryFn: async () => {
      if (!isConfigured) {
        console.log('[RevenueCat] Not configured, returning null');
        return null;
      }
      console.log('[RevenueCat] Fetching offerings');
      const offerings = await Purchases.getOfferings();
      console.log('[RevenueCat] Offerings:', offerings.current?.identifier);
      return offerings;
    },
    enabled: isConfigured,
    staleTime: 1000 * 60 * 10,
  });

  const purchaseMutation = useMutation({
    mutationFn: async (pkg: PurchasesPackage) => {
      console.log('[RevenueCat] Purchasing package:', pkg.identifier);
      const { customerInfo } = await Purchases.purchasePackage(pkg);
      return customerInfo;
    },
    onSuccess: (customerInfo) => {
      const hasAccess = typeof customerInfo.entitlements.active['premium'] !== 'undefined';
      setIsPremium(hasAccess);
      console.log('[RevenueCat] Purchase successful, isPremium:', hasAccess);
      queryClient.setQueryData(['revenuecat-customer-info', isConfigured], customerInfo);
    },
    onError: (error: Error & { code?: string }) => {
      // キャンセルは正常な操作なのでエラーとして扱わない
      if (error.code === PURCHASES_ERROR_CODE.PURCHASE_CANCELLED_ERROR) {
        console.log('[RevenueCat] Purchase cancelled by user');
        return;
      }
      // その他のエラーのみログ出力
      console.warn('[RevenueCat] Purchase error:', error.message);
    },
  });

  const restoreMutation = useMutation({
    mutationFn: async () => {
      console.log('[RevenueCat] Restoring purchases');
      const customerInfo = await Purchases.restorePurchases();
      return customerInfo;
    },
    onSuccess: (customerInfo) => {
      const hasAccess = typeof customerInfo.entitlements.active['premium'] !== 'undefined';
      setIsPremium(hasAccess);
      console.log('[RevenueCat] Restore successful, isPremium:', hasAccess);
      queryClient.setQueryData(['revenuecat-customer-info', isConfigured], customerInfo);
    },
    onError: (error: Error) => {
      console.error('[RevenueCat] Restore error:', error.message);
    },
  });

  useEffect(() => {
    if (!isConfigured) return;

    const listener = (customerInfo: CustomerInfo) => {
      const hasAccess = typeof customerInfo.entitlements.active['premium'] !== 'undefined';
      setIsPremium(hasAccess);
      console.log('[RevenueCat] Customer info updated, isPremium:', hasAccess);
      queryClient.setQueryData(['revenuecat-customer-info', isConfigured], customerInfo);
    };

    Purchases.addCustomerInfoUpdateListener(listener);
    return () => {
      Purchases.removeCustomerInfoUpdateListener(listener);
    };
  }, [isConfigured, queryClient]);

  const currentOffering = offeringsQuery.data?.current ?? null;

  const { mutateAsync: purchasePackageAsync } = purchaseMutation;
  const { mutateAsync: restoreAsync } = restoreMutation;

  const purchasePackage = (pkg: PurchasesPackage) => {
    return purchasePackageAsync(pkg);
  };

  const restorePurchases = () => {
    return restoreAsync();
  };

  return {
    isConfigured,
    isPremium,
    customerInfo: customerInfoQuery.data ?? null,
    currentOffering,
    isLoadingOfferings: offeringsQuery.isLoading,
    isLoadingCustomerInfo: customerInfoQuery.isLoading,
    purchasePackage,
    restorePurchases,
    isPurchasing: purchaseMutation.isPending,
    isRestoring: restoreMutation.isPending,
    purchaseError: purchaseMutation.error,
    restoreError: restoreMutation.error,
  };
});
