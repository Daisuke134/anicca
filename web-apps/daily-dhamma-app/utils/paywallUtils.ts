import type { PurchasesPackage } from 'react-native-purchases';

/**
 * RevenueCat の Offering から月額パッケージを返す。
 * identifier が 'monthly' または '$rc_monthly' のパッケージを探す。
 */
export function findMonthlyPackage(
  packages: PurchasesPackage[]
): PurchasesPackage | undefined {
  return packages.find(
    (pkg) => pkg.identifier === 'monthly' || pkg.identifier === '$rc_monthly'
  );
}

/**
 * RevenueCat の Offering から年額パッケージを返す。
 * identifier が 'annual' または '$rc_annual' のパッケージを探す。
 */
export function findYearlyPackage(
  packages: PurchasesPackage[]
): PurchasesPackage | undefined {
  return packages.find(
    (pkg) => pkg.identifier === 'annual' || pkg.identifier === '$rc_annual'
  );
}

/**
 * パッケージの価格文字列を返す。パッケージが undefined の場合は空文字を返す。
 */
export function formatPackagePrice(
  pkg: PurchasesPackage | undefined
): string {
  if (!pkg) return '';
  return pkg.product.priceString;
}
