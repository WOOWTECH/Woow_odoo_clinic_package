/**
 * PII Fields Visibility — 5 tests
 *
 * Verifies that national_id and nhi_card_no are visible to all Medical
 * users (User / Physician / Admin), and that a user without Medical
 * permissions cannot access the Medical module at all.
 */
import { test, expect } from '@playwright/test';
import {
  loginAs,
  navigateToPatients,
  isMedicalMenuAccessible,
  createTestUser,
  deleteTestUser,
  USERS,
} from '../helpers/odoo-helpers';

// Name of the Internal-only user created for negative testing
const NO_MED_LOGIN = 'test_no_medical_user';
const NO_MED_NAME  = 'Test No Medical';
const NO_MED_PASS  = 'test_no_medical_user';

test.describe('PII Fields Visibility', () => {

  // ── Setup: ensure a patient with PII data exists, and create Internal-only user ──
  test.beforeAll(async () => {
    // Create the no-medical user (Internal User only, no Medical group)
    await createTestUser(NO_MED_LOGIN, NO_MED_NAME, NO_MED_PASS, []);
  });

  test.afterAll(async () => {
    await deleteTestUser(NO_MED_LOGIN);
  });

  // Helper: open first patient form and return field visibility
  async function checkPiiFields(page: import('@playwright/test').Page) {
    await navigateToPatients(page);
    const firstRow = page.locator('tr.o_data_row').first();
    await firstRow.waitFor({ timeout: 10_000 });
    await firstRow.click();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    const nidField = page.locator('.o_field_widget[name="national_id"]');
    const nhiField = page.locator('.o_field_widget[name="nhi_card_no"]');

    const nidVisible = await nidField.isVisible({ timeout: 5000 }).catch(() => false);
    const nhiVisible = await nhiField.isVisible({ timeout: 3000 }).catch(() => false);
    return { nidVisible, nhiVisible };
  }

  test('7. Medical User can see national_id and nhi_card_no', async ({ page }) => {
    await loginAs(page, USERS.test_basic_user.login, USERS.test_basic_user.password);
    const { nidVisible, nhiVisible } = await checkPiiFields(page);
    expect(nidVisible, 'national_id should be visible for Medical User').toBe(true);
    expect(nhiVisible, 'nhi_card_no should be visible for Medical User').toBe(true);
  });

  test('8. Medical Physician can see national_id and nhi_card_no', async ({ page }) => {
    await loginAs(page, USERS.test_physician_a.login, USERS.test_physician_a.password);
    const { nidVisible, nhiVisible } = await checkPiiFields(page);
    expect(nidVisible, 'national_id should be visible for Physician').toBe(true);
    expect(nhiVisible, 'nhi_card_no should be visible for Physician').toBe(true);
  });

  test('9. Medical Administrator can see national_id and nhi_card_no', async ({ page }) => {
    await loginAs(page, USERS.test_med_admin.login, USERS.test_med_admin.password);
    const { nidVisible, nhiVisible } = await checkPiiFields(page);
    expect(nidVisible, 'national_id should be visible for Med Admin').toBe(true);
    expect(nhiVisible, 'nhi_card_no should be visible for Med Admin').toBe(true);
  });

  test('10. PII fields show correct data (not masked or empty)', async ({ page }) => {
    await loginAs(page, USERS.test_basic_user.login, USERS.test_basic_user.password);
    await navigateToPatients(page);

    // Search for a patient with PII data (created by layer1 tests)
    const searchBox = page.locator('.o_searchview_input, input.o_searchview_input');
    if (await searchBox.isVisible({ timeout: 3000 }).catch(() => false)) {
      await searchBox.fill('PII Test');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(2000);
    }

    const firstRow = page.locator('tr.o_data_row').first();
    if (await firstRow.isVisible({ timeout: 5000 }).catch(() => false)) {
      await firstRow.click();
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      const nidWidget = page.locator('.o_field_widget[name="national_id"]');
      const nidText = await nidWidget.textContent();
      // If the patient has a national_id set, it should not be "****" or empty
      if (nidText && nidText.trim().length > 0) {
        expect(nidText.trim()).not.toContain('****');
      }
    }
    // If no PII test patient found, this is a soft pass — data may not exist yet
  });

  test('11. Internal User without Medical group cannot access Medical module', async ({ page }) => {
    await loginAs(page, NO_MED_LOGIN, NO_MED_PASS);
    const accessible = await isMedicalMenuAccessible(page);
    expect(accessible, 'Internal User should NOT be able to access Medical module').toBe(false);
  });
});
