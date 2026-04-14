import type { NavigationGuardNext, RouteLocationNormalized, Router } from 'vue-router';
import { isJwtExpired } from 'src/utils/jwt';

const PUBLIC_PATH_PREFIXES = [
  '/login',
  '/forgot-password',
  '/reset-password',
  '/role-selection',
  '/register',
  '/landing',
];

const isPublicRoute = (path: string) => PUBLIC_PATH_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));

const getRequiredRole = (path: string): string | null => {
  if (path.startsWith('/doctor-')) return 'doctor';
  if (path.startsWith('/nurse-')) return 'nurse';
  if (path.startsWith('/patient-')) return 'patient';
  return null;
};

const safeJsonParse = <T>(value: string | null): T | null => {
  try {
    if (!value) return null;
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
};

type StoredUser = {
  role?: string;
  verification_status?: string;
  is_verified?: boolean;
};

const getStoredAuth = () => {
  const accessToken = localStorage.getItem('access_token') || '';
  const refreshToken = localStorage.getItem('refresh_token') || '';
  const user = safeJsonParse<StoredUser>(localStorage.getItem('user'));
  const role = (user?.role || localStorage.getItem('role') || '').toLowerCase();
  const verificationStatus = (user?.verification_status || '').toLowerCase();
  const isVerifiedFlag = user?.is_verified === true;
  return { accessToken, refreshToken, user, role, verificationStatus, isVerifiedFlag };
};

const clearAuth = () => {
  try {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    localStorage.removeItem('role');
  } catch {
    return;
  }
};

const getDashboardForRole = (role: string): string => {
  if (role === 'doctor') return '/doctor-dashboard';
  if (role === 'nurse') return '/nurse-dashboard';
  if (role === 'patient') return '/patient-dashboard';
  return '/login';
};

const requiresVerification = (role: string) => role === 'doctor' || role === 'nurse';

export const applyAuthGuards = (router: Router) => {
  router.beforeEach((to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) => {
    const path = to.path || '/';

    if (isPublicRoute(path)) {
      next();
      return;
    }

    if (path === '/verification') {
      const { accessToken } = getStoredAuth();
      if (!accessToken || isJwtExpired(accessToken)) {
        clearAuth();
        next({ path: '/login', query: { redirect: to.fullPath } });
        return;
      }
      next();
      return;
    }

    const { accessToken, role, verificationStatus, isVerifiedFlag } = getStoredAuth();
    if (!accessToken || isJwtExpired(accessToken)) {
      clearAuth();
      next({ path: '/login', query: { redirect: to.fullPath } });
      return;
    }

    const requiredRole = getRequiredRole(path);
    if (requiredRole && role && requiredRole !== role) {
      next({ path: getDashboardForRole(role) });
      return;
    }

    if (requiresVerification(role)) {
      const isApproved = verificationStatus === 'approved' || isVerifiedFlag;
      if (!isApproved) {
        next({ path: '/verification' });
        return;
      }
    }

    next();
  });
};

export const authGuardInternals = {
  isPublicRoute,
  getRequiredRole,
  getDashboardForRole,
};

