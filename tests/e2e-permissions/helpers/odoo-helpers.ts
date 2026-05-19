/**
 * Odoo 18 E2E test helpers — login, navigation, JSON-RPC, permission utilities.
 */
import { type Page, expect } from '@playwright/test';

// ── Configuration ──────────────────────────────────────────────────
const BASE_URL = process.env.ODOO_URL ?? 'http://localhost:9103';
const DB_NAME  = process.env.ODOO_DB  ?? 'odoo-clinic';
const ADMIN_LOGIN = process.env.ODOO_USER ?? 'admin';
const ADMIN_PASS  = process.env.ODOO_PASS ?? 'admin';

// ── JSON-RPC client ────────────────────────────────────────────────
let _rpcId = 0;

interface RpcResult {
  jsonrpc: string;
  id: number;
  result?: unknown;
  error?: { message: string; data?: { message?: string } };
}

async function jsonrpc(endpoint: string, service: string, method: string, args: unknown[]): Promise<unknown> {
  _rpcId++;
  const resp = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      method: 'call',
      params: { service, method, args },
      id: _rpcId,
    }),
  });
  const data: RpcResult = await resp.json();
  if (data.error) {
    const msg = data.error.data?.message ?? data.error.message;
    throw new Error(`RPC Error: ${msg}`);
  }
  return data.result;
}

// Cache admin uid
let _adminUid: number | null = null;

async function adminUid(): Promise<number> {
  if (_adminUid === null) {
    _adminUid = (await jsonrpc('/jsonrpc', 'common', 'authenticate', [
      DB_NAME, ADMIN_LOGIN, ADMIN_PASS, {},
    ])) as number;
    if (!_adminUid) throw new Error('Admin authentication failed');
  }
  return _adminUid;
}

export async function adminCall(
  model: string, method: string, args: unknown[] = [], kwargs: Record<string, unknown> = {},
): Promise<unknown> {
  const uid = await adminUid();
  return jsonrpc('/jsonrpc', 'object', 'execute_kw', [
    DB_NAME, uid, ADMIN_PASS, model, method, args, kwargs,
  ]);
}

// ── Group ID resolution ────────────────────────────────────────────
const _groupIdCache = new Map<string, number>();

export async function getGroupId(xmlId: string): Promise<number> {
  if (_groupIdCache.has(xmlId)) return _groupIdCache.get(xmlId)!;
  const [module, name] = xmlId.split('.');
  const result = (await adminCall('ir.model.data', 'search_read', [
    [['module', '=', module], ['name', '=', name], ['model', '=', 'res.groups']],
  ], { fields: ['res_id'], limit: 1 })) as { res_id: number }[];
  if (!result.length) throw new Error(`Group XML ID not found: ${xmlId}`);
  _groupIdCache.set(xmlId, result[0].res_id);
  return result[0].res_id;
}

// ── Browser helpers ────────────────────────────────────────────────
export async function loginAs(page: Page, username: string, password: string): Promise<void> {
  // Clear cookies + localStorage to prevent "Choose a user" session picker
  await page.context().clearCookies();
  // Navigate to a page on the target origin so we can clear localStorage
  await page.goto('/web/login', { waitUntil: 'commit' });
  await page.evaluate(() => {
    try { localStorage.clear(); } catch {}
    try { sessionStorage.clear(); } catch {}
  });
  // Reload to get a clean login form
  await page.goto('/web/login');
  await page.waitForLoadState('domcontentloaded');

  // Fallback: if session picker still shows, click "Use another user"
  const useAnother = page.getByText('Use another user');
  if (await useAnother.isVisible({ timeout: 2000 }).catch(() => false)) {
    await useAnother.click();
    await page.waitForLoadState('domcontentloaded');
  }

  await page.getByRole('textbox', { name: 'Email' }).fill(username);
  await page.locator('input[name="password"]').fill(password);
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.waitForURL(/\/odoo/, { timeout: 30_000 });
  await page.waitForLoadState('domcontentloaded');
}

export async function navigateToUserForm(page: Page, displayName: string): Promise<void> {
  await page.goto('/odoo/settings/users');
  await page.waitForLoadState('domcontentloaded');
  // Wait for user table to render
  await page.locator('tr.o_data_row').first().waitFor({ timeout: 15_000 });
  // Click the matching row
  await page.locator(`tr.o_data_row:has-text("${displayName}")`).first().click();
  await page.waitForLoadState('domcontentloaded');
  // Ensure Access Rights tab is active
  const accessTab = page.getByRole('tab', { name: 'Access Rights' });
  if (await accessTab.isVisible()) {
    await accessTab.click();
  }
  await page.waitForTimeout(1000);
}

/**
 * Get the Medical dropdown <select> element on a user form page.
 * Odoo renders the reified field as a <select> labelled "Medical?".
 */
export function getMedicalDropdown(page: Page) {
  return page.getByRole('combobox', { name: /Medical/ });
}

/**
 * Read the currently selected option text in the Medical dropdown.
 */
export async function getMedicalDropdownValue(page: Page): Promise<string> {
  const select = getMedicalDropdown(page);
  await select.waitFor({ timeout: 10_000 });
  const value = await select.locator('option:checked').textContent();
  return (value ?? '').trim();
}

/**
 * Get all option labels from the Medical dropdown.
 */
export async function getMedicalDropdownOptions(page: Page): Promise<string[]> {
  const select = getMedicalDropdown(page);
  await select.waitFor({ timeout: 10_000 });
  return select.locator('option').allTextContents();
}

/**
 * Set a user's Medical permission level via the Settings UI.
 * Must be logged in as admin and on the target user's form page.
 * @param label - The option label: '' (empty), 'Medical User', 'Medical Physician', 'Medical Administrator'
 */
export async function setMedicalPermission(page: Page, label: string): Promise<void> {
  const select = getMedicalDropdown(page);
  await select.waitFor({ timeout: 10_000 });
  if (label === '') {
    await select.selectOption({ index: 0 });
  } else {
    await select.selectOption({ label });
  }
  // Save the form — Odoo 18 auto-saves on navigation, but we click the save button if visible
  const saveBtn = page.locator('.o_form_button_save');
  if (await saveBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await saveBtn.click();
    await page.waitForTimeout(1500);
  } else {
    // Trigger auto-save by navigating away and back
    await page.locator('.o_breadcrumb a:has-text("Users")').click();
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);
  }
}

// ── Test user management via JSON-RPC ──────────────────────────────
export async function createTestUser(
  login: string, name: string, password: string, groupXmlIds: string[] = [],
): Promise<number> {
  // Check if user exists (include archived users to avoid unique constraint)
  const existing = (await adminCall('res.users', 'search', [
    [['login', '=', login]],
  ], { context: { active_test: false } })) as number[];
  if (existing.length) {
    // Re-activate if archived
    await adminCall('res.users', 'write', [existing, { active: true }]);
    return existing[0];
  }

  const baseGroupId = await getGroupId('base.group_user');
  const groupIds = [baseGroupId];
  for (const xmlId of groupXmlIds) {
    groupIds.push(await getGroupId(xmlId));
  }

  const uid = await adminCall('res.users', 'create', [[{
    name,
    login,
    password,
    groups_id: [[6, 0, [...new Set(groupIds)]]],
  }]]);
  return Array.isArray(uid) ? uid[0] : uid as number;
}

export async function deleteTestUser(login: string): Promise<void> {
  const ids = (await adminCall('res.users', 'search', [
    [['login', '=', login]],
  ], { context: { active_test: false } })) as number[];
  if (ids.length) {
    // Deactivate instead of delete to avoid constraint issues
    await adminCall('res.users', 'write', [ids, { active: false }]);
  }
}

/**
 * Navigate to Medical > Patients action via Odoo action XML ID.
 */
export async function navigateToPatients(page: Page): Promise<void> {
  await page.goto('/web#action=woow_medical_patient.medical_patient_action', {
    waitUntil: 'domcontentloaded',
  });
  await page.waitForTimeout(2500);
}

/**
 * Check if the Medical menu/sidebar entry is accessible for the current user.
 * Returns true if the patient list view loads, false if access is denied or menu missing.
 */
export async function isMedicalMenuAccessible(page: Page): Promise<boolean> {
  await page.goto('/web#action=woow_medical_patient.medical_patient_action', {
    waitUntil: 'domcontentloaded',
  });
  await page.waitForTimeout(3000);
  // If user has no access, Odoo shows an error or redirects
  const listView = page.locator('.o_list_view, .o_kanban_view');
  const hasAccess = await listView.isVisible({ timeout: 3000 }).catch(() => false);
  return hasAccess;
}

// ── Constants for test user credentials ────────────────────────────
export const USERS = {
  admin:            { login: ADMIN_LOGIN, password: ADMIN_PASS,    name: 'Administrator' },
  test_basic_user:  { login: 'test_basic_user',  password: 'test_basic_user',  name: 'Test Basic User' },
  test_physician_a: { login: 'test_physician_a', password: 'test_physician_a', name: 'Test Physician A' },
  test_med_admin:   { login: 'test_med_admin',   password: 'test_med_admin',   name: 'Test Med Admin' },
} as const;
