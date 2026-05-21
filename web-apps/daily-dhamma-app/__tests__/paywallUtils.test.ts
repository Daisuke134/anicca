/**
 * paywallUtils Unit Tests (TDD)
 *
 * T-P1: findMonthlyPackage finds 'monthly' identifier
 * T-P2: findMonthlyPackage finds '$rc_monthly' identifier
 * T-P3: findYearlyPackage finds 'annual' identifier
 * T-P4: findYearlyPackage finds '$rc_annual' identifier
 * T-P5: findMonthlyPackage returns undefined when packages empty
 * T-P6: formatPackagePrice returns priceString when pkg exists
 * T-P7: formatPackagePrice returns empty string when pkg undefined
 */

import { findMonthlyPackage, findYearlyPackage, formatPackagePrice } from '../utils/paywallUtils';
import type { PurchasesPackage } from 'react-native-purchases';

function makePkg(identifier: string, priceString = '$9.99'): PurchasesPackage {
  return {
    identifier,
    packageType: 'CUSTOM',
    product: {
      identifier: `com.dailydhamma.${identifier}`,
      description: 'Test product',
      title: 'Test',
      price: 9.99,
      priceString,
      currencyCode: 'USD',
      introPrice: null,
      discounts: [],
      productCategory: 'NON_SUBSCRIPTION',
      productType: 'NON_CONSUMABLE',
      subscriptionPeriod: null,
    },
    offeringIdentifier: 'default',
    presentedOfferingContext: { offeringIdentifier: 'default', placementIdentifier: null, targetingContext: null },
  } as unknown as PurchasesPackage;
}

describe('findMonthlyPackage', () => {
  // T-P1
  test('finds package with identifier "monthly"', () => {
    const pkgs = [makePkg('annual'), makePkg('monthly')];
    expect(findMonthlyPackage(pkgs)?.identifier).toBe('monthly');
  });

  // T-P2
  test('finds package with identifier "$rc_monthly"', () => {
    const pkgs = [makePkg('$rc_annual'), makePkg('$rc_monthly')];
    expect(findMonthlyPackage(pkgs)?.identifier).toBe('$rc_monthly');
  });

  // T-P5
  test('returns undefined when packages array is empty', () => {
    expect(findMonthlyPackage([])).toBeUndefined();
  });
});

describe('findYearlyPackage', () => {
  // T-P3
  test('finds package with identifier "annual"', () => {
    const pkgs = [makePkg('monthly'), makePkg('annual')];
    expect(findYearlyPackage(pkgs)?.identifier).toBe('annual');
  });

  // T-P4
  test('finds package with identifier "$rc_annual"', () => {
    const pkgs = [makePkg('$rc_monthly'), makePkg('$rc_annual')];
    expect(findYearlyPackage(pkgs)?.identifier).toBe('$rc_annual');
  });

  test('returns undefined when packages array is empty', () => {
    expect(findYearlyPackage([])).toBeUndefined();
  });
});

describe('formatPackagePrice', () => {
  // T-P6
  test('returns priceString when package exists', () => {
    const pkg = makePkg('monthly', '$4.99');
    expect(formatPackagePrice(pkg)).toBe('$4.99');
  });

  // T-P7
  test('returns empty string when package is undefined', () => {
    expect(formatPackagePrice(undefined)).toBe('');
  });
});
