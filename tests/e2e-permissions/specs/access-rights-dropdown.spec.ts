/**
 * Access Rights Dropdown — 6 tests
 *
 * Verifies the Medical permission dropdown renders correctly in
 * Settings > Users > Access Rights for all user roles.
 */
import { test, expect } from '@playwright/test';
import {
  loginAs,
  navigateToUserForm,
  getMedicalDropdown,
  getMedicalDropdownValue,
  getMedicalDropdownOptions,
  USERS,
} from '../helpers/odoo-helpers';

test.describe('Access Rights — Medical dropdown', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, USERS.admin.login, USERS.admin.password);
  });

  test('1. Medical dropdown is visible on user form', async ({ page }) => {
    await navigateToUserForm(page, USERS.test_basic_user.name);
    const dropdown = getMedicalDropdown(page);
    await expect(dropdown).toBeVisible();
  });

  test('2. Dropdown contains 4 options: (empty) / User / Physician / Administrator', async ({ page }) => {
    await navigateToUserForm(page, USERS.test_basic_user.name);
    const options = await getMedicalDropdownOptions(page);
    // Trim whitespace from each option
    const trimmed = options.map(o => o.trim());
    expect(trimmed).toHaveLength(4);
    expect(trimmed[0]).toBe('');                        // empty option
    expect(trimmed).toContain('Medical User');
    expect(trimmed).toContain('Medical Physician');
    expect(trimmed).toContain('Medical Administrator');
  });

  test('3. Administrator shows "Medical Administrator"', async ({ page }) => {
    await navigateToUserForm(page, USERS.admin.name);
    const value = await getMedicalDropdownValue(page);
    expect(value).toBe('Medical Administrator');
  });

  test('4. Test Basic User shows "Medical User"', async ({ page }) => {
    await navigateToUserForm(page, USERS.test_basic_user.name);
    const value = await getMedicalDropdownValue(page);
    expect(value).toBe('Medical User');
  });

  test('5. Test Physician A shows "Medical Physician"', async ({ page }) => {
    await navigateToUserForm(page, USERS.test_physician_a.name);
    const value = await getMedicalDropdownValue(page);
    expect(value).toBe('Medical Physician');
  });

  test('6. Test Med Admin shows "Medical Administrator"', async ({ page }) => {
    await navigateToUserForm(page, USERS.test_med_admin.name);
    const value = await getMedicalDropdownValue(page);
    expect(value).toBe('Medical Administrator');
  });
});
