import { describe, it, expect } from 'vitest';
import { authGuardInternals } from 'src/router/guards';

describe('route guard internals', () => {
  it('detects public routes', () => {
    expect(authGuardInternals.isPublicRoute('/login')).toBe(true);
    expect(authGuardInternals.isPublicRoute('/register/patient')).toBe(true);
    expect(authGuardInternals.isPublicRoute('/landing')).toBe(true);
    expect(authGuardInternals.isPublicRoute('/doctor-dashboard')).toBe(false);
  });

  it('infers required role by path prefix', () => {
    expect(authGuardInternals.getRequiredRole('/doctor-dashboard')).toBe('doctor');
    expect(authGuardInternals.getRequiredRole('/nurse-dashboard')).toBe('nurse');
    expect(authGuardInternals.getRequiredRole('/patient-dashboard')).toBe('patient');
    expect(authGuardInternals.getRequiredRole('/verification')).toBe(null);
  });

  it('maps role to dashboard route', () => {
    expect(authGuardInternals.getDashboardForRole('doctor')).toBe('/doctor-dashboard');
    expect(authGuardInternals.getDashboardForRole('nurse')).toBe('/nurse-dashboard');
    expect(authGuardInternals.getDashboardForRole('patient')).toBe('/patient-dashboard');
  });
});

