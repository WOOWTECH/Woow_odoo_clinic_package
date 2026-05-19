/**
 * Permission Escalation / De-escalation — 4 tests
 *
 * Verifies that changing a user's Medical permission level via the
 * Settings UI takes effect immediately upon the user's next login.
 *
 * Tests cover: upgrade, downgrade, removal, and restoration of permissions.
 *
 * Uses test_basic_user as the target — original permission = Medical User.
 * Each test modifies the permission via admin, then logs in as the target
 * user to verify the effect. An afterEach hook restores original permission.
 */
import { test, expect } from '@playwright/test';
import {
  loginAs,
  navigateToUserForm,
  getMedicalDropdownValue,
  setMedicalPermission,
  navigateToPatients,
  isMedicalMenuAccessible,
  USERS,
} from '../helpers/odoo-helpers';

const TARGET = USERS.test_basic_user;
const ORIGINAL_LEVEL = 'Medical User';

test.describe('Permission Escalation & De-escalation', () => {

  // Restore target user to original permission after each test
  test.afterEach(async ({ page }) => {
    await loginAs(page, USERS.admin.login, USERS.admin.password);
    await navigateToUserForm(page, TARGET.name);
    const current = await getMedicalDropdownValue(page);
    if (current !== ORIGINAL_LEVEL) {
      await setMedicalPermission(page, ORIGINAL_LEVEL);
    }
  });

  test('12. Upgrade: User → Physician grants Medical Record creation', async ({ page }) => {
    // Step 1: Admin upgrades target from Medical User to Medical Physician
    await loginAs(page, USERS.admin.login, USERS.admin.password);
    await navigateToUserForm(page, TARGET.name);
    await setMedicalPermission(page, 'Medical Physician');

    // Verify the change was saved
    await navigateToUserForm(page, TARGET.name);
    const saved = await getMedicalDropdownValue(page);
    expect(saved).toBe('Medical Physician');

    // Step 2: Target user logs in — should be able to access Medical Records
    await loginAs(page, TARGET.login, TARGET.password);
    await page.goto('/web#action=woow_medical_record.medical_record_action', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForTimeout(3000);

    // Physician should see the "New" button to create records
    const newBtn = page.locator(
      '.o_control_panel button.o_list_button_add, .o_control_panel .btn-primary:has-text("New")',
    );
    const canCreate = await newBtn.isVisible({ timeout: 5000 }).catch(() => false);
    expect(canCreate, 'Physician should be able to create Medical Records').toBe(true);
  });

  test('13. Downgrade: Physician → User removes Record creation ability', async ({ page }) => {
    // Step 1: Admin upgrades to Physician first
    await loginAs(page, USERS.admin.login, USERS.admin.password);
    await navigateToUserForm(page, TARGET.name);
    await setMedicalPermission(page, 'Medical Physician');

    // Step 2: Admin downgrades back to Medical User
    await navigateToUserForm(page, TARGET.name);
    await setMedicalPermission(page, 'Medical User');

    // Verify the change persisted
    await navigateToUserForm(page, TARGET.name);
    const saved = await getMedicalDropdownValue(page);
    expect(saved).toBe('Medical User');

    // Step 3: Target user logs in — should NOT see "New" on Medical Records
    await loginAs(page, TARGET.login, TARGET.password);
    await page.goto('/web#action=woow_medical_record.medical_record_action', {
      waitUntil: 'domcontentloaded',
    });
    await page.waitForTimeout(3000);

    // Medical User cannot create records — either no "New" button or access denied
    const newBtn = page.locator(
      '.o_control_panel button.o_list_button_add, .o_control_panel .btn-primary:has-text("New")',
    );
    const canCreate = await newBtn.isVisible({ timeout: 3000 }).catch(() => false);
    expect(canCreate, 'Medical User should NOT be able to create Medical Records').toBe(false);
  });

  test('14. Removal: Set Medical to (empty) blocks module access', async ({ page }) => {
    // Step 1: Admin removes Medical permission entirely
    await loginAs(page, USERS.admin.login, USERS.admin.password);
    await navigateToUserForm(page, TARGET.name);
    await setMedicalPermission(page, '');

    // Verify dropdown shows empty
    await navigateToUserForm(page, TARGET.name);
    const saved = await getMedicalDropdownValue(page);
    expect(saved).toBe('');

    // Step 2: Target user logs in — Medical module should be inaccessible
    await loginAs(page, TARGET.login, TARGET.password);
    const accessible = await isMedicalMenuAccessible(page);
    expect(accessible, 'User with no Medical group should not access Medical module').toBe(false);
  });

  test('15. Restoration: Re-granting permission restores access', async ({ page }) => {
    // Step 1: Admin removes permission
    await loginAs(page, USERS.admin.login, USERS.admin.password);
    await navigateToUserForm(page, TARGET.name);
    await setMedicalPermission(page, '');

    // Step 2: Admin restores to Medical User
    await navigateToUserForm(page, TARGET.name);
    await setMedicalPermission(page, ORIGINAL_LEVEL);

    // Verify restoration
    await navigateToUserForm(page, TARGET.name);
    const saved = await getMedicalDropdownValue(page);
    expect(saved).toBe(ORIGINAL_LEVEL);

    // Step 3: Target user logs in — Medical module should be accessible again
    await loginAs(page, TARGET.login, TARGET.password);
    const accessible = await isMedicalMenuAccessible(page);
    expect(accessible, 'User should regain access after permission restoration').toBe(true);

    // Also verify patient list loads
    await navigateToPatients(page);
    const listView = page.locator('.o_list_view, .o_kanban_view');
    await expect(listView).toBeVisible({ timeout: 10_000 });
  });
});
