## URL Structure Changes (Removal of `/api/` Prefix)

### Summary

The backend routing has been refactored to remove the redundant `/api/` prefix. All API endpoints are now mounted at clean, resource-oriented root paths.

### Old vs New Base Paths

| Area | Old Base | New Base |
|---|---|---|
| Users | `/api/users/` | `/users/` |
| Operations | `/api/operations/` | `/operations/` |
| Analytics | `/api/analytics/` | `/analytics/` |
| Admin API (admin_site) | `/api/admin/` | `/admin/` |
| Django admin UI | `/admin/` | `/django-admin/` |

### What Was Updated

#### Backend
- Root router updated to mount app URLs without `/api/` in `backend/urls.py`.
- Admin API overview endpoint updated to return new `/admin/*` paths.
- Analytics stress-test endpoint list updated to use new `/operations/*` paths.
- Tests updated to call new endpoint paths.

#### Frontend
- Axios base URL configuration updated to remove `/api` suffix.
- Admin dashboard frontend defaults updated from `/api/admin` to `/admin`.

#### Documentation
- API documentation, testing protocol, and system design docs updated to reflect new base paths.

### Compatibility Notes

- Any clients using absolute URLs must be updated to the new bases.
- Reverse URL lookups (`reverse(...)`) are unaffected because URL names did not change; only mount points changed.

