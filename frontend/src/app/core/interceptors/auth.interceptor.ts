import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

/**
 * Haengt das Bearer-Token an alle /api-Requests (ausser /api/auth/*).
 * Bei 401 wird ausgeloggt und auf /login geleitet.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  const token = auth.getToken();

  const isApi = req.url.startsWith('/api/');
  const isAuthEndpoint = req.url.startsWith('/api/auth/');

  const authReq =
    token && isApi && !isAuthEndpoint
      ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : req;

  return next(authReq).pipe(
    catchError((err: HttpErrorResponse) => {
      if (err.status === 401 && isApi && !isAuthEndpoint) {
        auth.logout();
        void router.navigate(['/login']);
      }
      return throwError(() => err);
    }),
  );
};
