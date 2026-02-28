# RELEASE CHECKLIST

## 1. Environment
- [ ] Activate correct `venv` for this project.
- [ ] Verify dependencies are installed: `pip install -r requirements.txt`.
- [ ] Confirm `.env` values for target environment (DB, hosts, debug, csrf).

## 2. Security Baseline
- [ ] `DEBUG=False` in production.
- [ ] `ALLOWED_HOSTS` is explicit (not `*`).
- [ ] DB credentials are from environment variables.
- [ ] Admin access is restricted to trusted users only.

## 3. Database and Migrations
- [ ] Run: `python manage.py makemigrations --check --dry-run`.
- [ ] Run: `python manage.py migrate`.
- [ ] Verify new tables/columns for attendance/payroll/regulations exist.
- [ ] Run seed/normalization commands if needed:
  - [ ] `python manage.py normalize_roles`
  - [ ] `python manage.py init_rbac`

## 4. RBAC (Roles and Permissions)
- [ ] Verify role matrix in real data:
  - [ ] `SUPER_ADMIN`/`ADMINISTRATOR` manage users and global admin modules.
  - [ ] `ADMIN` has limited scope where expected (department scope).
  - [ ] `EMPLOYEE`/`INTERN` have only allowed self/team actions.
- [ ] Confirm `/admin/accounts/user/` is blocked for `ADMIN/EMPLOYEE/INTERN`.
- [ ] Confirm side menu visibility matches role policy.

## 5. Payroll Checks
- [ ] Pay types work: `hourly`, `minute`, `fixed_salary`.
- [ ] `SUPER_ADMIN`/`ADMINISTRATOR` can edit others, not themselves.
- [ ] `ADMIN` can edit only employees in own department, not self.
- [ ] `INTERN` excluded from payroll list and my-payroll endpoint.
- [ ] Recalculate month and verify totals/status flow.

## 6. Attendance Checks
- [ ] One check-in per day enforced (`409` on second check-in).
- [ ] `SUPER_ADMIN`/`ADMINISTRATOR`: view attendance only (no check-in buttons).
- [ ] `ADMIN/EMPLOYEE/INTERN`: check-in works per policy.
- [ ] Office whitelist contains needed networks (including localhost for local dev).
- [ ] Attendance page shows:
  - [ ] daily who-checked-in table
  - [ ] monthly totals
  - [ ] detailed per-day employee list
  - [ ] Russian status labels

## 7. Regulations Checks
- [ ] In `/admin/regulations/` only `Regulation` remains visible.
- [ ] Regulation opens correctly by link/file.
- [ ] Read deadline and read report flow works.
- [ ] Quiz flow works (create, submit, pass/fail).

## 8. Profile and Company Pages
- [ ] Profile page has no embedded "company structure" block.
- [ ] Company pages available via sidebar links:
  - [ ] `/admin/company/structure/`
  - [ ] `/admin/company/list/`

## 9. Automated Tests
- [ ] Run targeted tests:
  - [ ] `python manage.py test accounts.tests`
  - [ ] `python manage.py test apps.attendance.tests`
  - [ ] `python manage.py test apps.payroll.tests.test_api`
  - [ ] `python manage.py test regulations.tests`
  - [ ] `python manage.py test content.tests`
- [ ] Fix failing tests before release.

## 10. Manual Smoke Test (Post-deploy)
- [ ] Login as each key role and verify landing/menu.
- [ ] Create/edit one payroll compensation and recalc one month.
- [ ] Execute one attendance check-in (allowed role) and validate it appears.
- [ ] Verify admin pages load without 500 errors.
- [ ] Verify key API endpoints return expected status codes.

## 11. Release Hygiene
- [ ] `git status` clean or intentionally documented.
- [ ] Migrations committed with related code.
- [ ] Release notes/changelog updated.
- [ ] Backup/rollback plan prepared.
