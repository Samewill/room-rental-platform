import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  ApiError,
  getMyProfile,
  login,
  registerAccount,
  type UserProfile,
} from "./api";
import AppLink from "./components/AppLink";
import DashboardPage, { type DashboardRole } from "./pages/DashboardPage";
import LandlordDashboardPage from "./pages/LandlordDashboardPage";
import ListingDetailsPage from "./pages/ListingDetailsPage";
import ListingsPage from "./pages/ListingsPage";
import "./App.css";

type AuthMode = "login" | "register";
type RegistrationRole = "tenant" | "landlord";
type FormFields = {
  fullName: string;
  phoneNo: string;
  email: string;
  password: string;
  businessName: string;
};

const AUTH_TOKEN_STORAGE_KEY = "room-rental-access-token";

const emptyForm: FormFields = {
  fullName: "",
  phoneNo: "",
  email: "",
  password: "",
  businessName: "",
};

function getDashboardRole(roles: string[]): DashboardRole {
  if (roles.includes("admin")) {
    return "admin";
  }
  if (roles.includes("landlord")) {
    return "landlord";
  }
  if (roles.includes("tenant")) {
    return "tenant";
  }

  throw new Error("Your account has no supported role. Please contact support.");
}

function App() {
  const [pathname, setPathname] = useState(window.location.pathname);
  const [mode, setMode] = useState<AuthMode>(
    window.location.pathname === "/register" ? "register" : "login",
  );
  const [registrationRole, setRegistrationRole] =
    useState<RegistrationRole>("tenant");
  const [fields, setFields] = useState<FormFields>(emptyForm);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isAuthReady, setIsAuthReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sessionRestoreError, setSessionRestoreError] = useState<string | null>(
    null,
  );
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isCurrent = true;

    async function restoreSession() {
      setIsAuthReady(false);
      setSessionRestoreError(null);
      setSessionNotice(null);

      let savedToken: string | null;
      try {
        savedToken = window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
      } catch {
        if (isCurrent) {
          setSessionRestoreError(
            "Browser session storage is unavailable. Enable it and sign in again.",
          );
          setIsAuthReady(true);
        }
        return;
      }

      if (!savedToken) {
        if (isCurrent) {
          setIsAuthReady(true);
        }
        return;
      }

      try {
        const restoredProfile = await getMyProfile(savedToken);
        getDashboardRole(restoredProfile.roles);
        if (isCurrent) {
          setAccessToken(savedToken);
          setProfile(restoredProfile);
        }
      } catch (error: unknown) {
        if (!isCurrent) {
          return;
        }

        if (error instanceof ApiError && error.statusCode === 401) {
          try {
            window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
            setSessionNotice("Your session expired. Please sign in again.");
          } catch {
            setSessionRestoreError(
              "Your session expired, but browser storage could not be cleared. Please close this tab after signing in again.",
            );
          }
        } else {
          setSessionRestoreError(
            error instanceof Error
              ? `We couldn't verify your saved session: ${error.message}`
              : "We couldn't verify your saved session. Check your connection and try again.",
          );
        }
      } finally {
        if (isCurrent) {
          setIsAuthReady(true);
        }
      }
    }

    void restoreSession();
    return () => {
      isCurrent = false;
    };
  }, [restoreAttempt]);

  useEffect(() => {
    function syncPathname() {
      setPathname(window.location.pathname);
      setMode(window.location.pathname === "/register" ? "register" : "login");
    }

    window.addEventListener("popstate", syncPathname);
    return () => window.removeEventListener("popstate", syncPathname);
  }, []);

  function navigate(path: string) {
    const destination = new URL(path, window.location.href);
    if (destination.origin !== window.location.origin) {
      window.location.assign(destination.href);
      return;
    }
    window.history.pushState(null, "", destination.href);
    setPathname(destination.pathname);
    setMode(destination.pathname === "/register" ? "register" : "login");
    window.scrollTo({ top: 0 });
  }

  function updateField(field: keyof FormFields, value: string) {
    setFields((currentFields) => ({ ...currentFields, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setSessionRestoreError(null);
    setSessionNotice(null);
    setNotice(null);
    setIsSubmitting(true);

    try {
      if (mode === "register") {
        await registerAccount({
          full_name: fields.fullName,
          phone_no: fields.phoneNo,
          email: fields.email,
          password: fields.password,
          role: registrationRole,
          ...(registrationRole === "landlord" && fields.businessName.trim()
            ? { business_name: fields.businessName }
            : {}),
        });
        setMode("login");
        setRegistrationRole("tenant");
        setFields((currentFields) => ({
          ...emptyForm,
          email: currentFields.email,
        }));
        navigate("/login");
        setNotice("Your account is ready. Sign in with your new credentials.");
        return;
      }

      const tokenResponse = await login({
        email: fields.email,
        password: fields.password,
      });
      const currentProfile = await getMyProfile(tokenResponse.access_token);
      const dashboardRole = getDashboardRole(currentProfile.roles);
      window.sessionStorage.setItem(
        AUTH_TOKEN_STORAGE_KEY,
        tokenResponse.access_token,
      );
      setAccessToken(tokenResponse.access_token);
      setProfile(currentProfile);
      setFields(emptyForm);
      setSessionRestoreError(null);
      setSessionNotice(null);
      navigate(`/${dashboardRole}`);
    } catch (error: unknown) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "We could not complete your request. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSignOut() {
    let storageError: string | null = null;
    try {
      window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    } catch {
      storageError =
        "The saved session could not be cleared from this tab. Close this tab to discard it.";
    }

    setAccessToken(null);
    setProfile(null);
    setFields(emptyForm);
    setErrorMessage(storageError);
    setSessionRestoreError(null);
    setSessionNotice(null);
    setNotice(null);
    navigate(storageError === null ? "/" : "/login");
  }

  function retrySessionRestore() {
    setSessionRestoreError(null);
    setSessionNotice(null);
    setRestoreAttempt((attempt) => attempt + 1);
  }

  const listingMatch = pathname.match(/^\/listings\/(\d+)\/?$/);
  if (listingMatch !== null) {
    const listingId = Number(listingMatch[1]);
    if (Number.isSafeInteger(listingId) && listingId > 0) {
      return (
        <ListingDetailsPage
          accessToken={
            profile?.roles.includes("tenant") === true ? accessToken : null
          }
          isAuthReady={isAuthReady}
          isAuthenticated={profile !== null}
          listingId={listingId}
          onNavigate={navigate}
          onRetrySessionRestore={retrySessionRestore}
          sessionNotice={sessionNotice}
          sessionRestoreError={sessionRestoreError}
        />
      );
    }
  }

  if (pathname === "/") {
    return (
      <ListingsPage
        isAuthReady={isAuthReady}
        onNavigate={navigate}
        onRetrySessionRestore={retrySessionRestore}
        onSignOut={handleSignOut}
        profile={profile}
        sessionNotice={sessionNotice}
        sessionRestoreError={sessionRestoreError}
      />
    );
  }

  if (!isAuthReady) {
    return (
      <main className="page-shell">
        <p role="status">Checking your session…</p>
      </main>
    );
  }

  if (
    profile !== null &&
    accessToken !== null &&
    ["tenant", "landlord", "admin"].includes(pathname.slice(1))
  ) {
    const dashboardRole = getDashboardRole(profile.roles);
    if (pathname === `/${dashboardRole}`) {
      if (dashboardRole === "landlord") {
        return (
          <LandlordDashboardPage
            accessToken={accessToken}
            onNavigate={navigate}
            onSignOut={handleSignOut}
            profile={profile}
          />
        );
      }

      return (
        <DashboardPage
          accessToken={accessToken}
          onNavigate={navigate}
          onSignOut={handleSignOut}
          profile={profile}
          role={dashboardRole}
        />
      );
    }
  }

  const isRegistering = mode === "register";

  return (
    <main className="page-shell">
      <section className="auth-card" aria-labelledby="auth-heading">
        <p className="eyebrow">Room Rentals</p>
        <h1 id="auth-heading">
          {isRegistering ? "Create your account" : "Welcome back"}
        </h1>
        <p className="intro">
          {isRegistering
            ? "Choose how you’ll use Room Rentals."
            : "Sign in to continue to your account."}
        </p>

        {notice !== null && (
          <p className="message message-success" role="status">
            {notice}
          </p>
        )}
        {errorMessage !== null && (
          <p className="message message-error" role="alert">
            {errorMessage}
          </p>
        )}
        {sessionRestoreError !== null && (
          <div className="message message-error" role="alert">
            <p>{sessionRestoreError}</p>
            <button
              className="text-button"
              onClick={retrySessionRestore}
              type="button"
            >
              Retry session check
            </button>
          </div>
        )}
        {sessionNotice !== null && (
          <p className="message message-error" role="status">
            {sessionNotice}
          </p>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          {isRegistering && (
            <>
              <fieldset className="role-picker">
                <legend>I want to...</legend>
                <div className="role-options">
                  <button
                    aria-pressed={registrationRole === "tenant"}
                    className={`role-option${registrationRole === "tenant" ? " selected" : ""}`}
                    onClick={() => setRegistrationRole("tenant")}
                    type="button"
                  >
                    <span className="role-option-title">I need a room</span>
                    <span className="role-option-description">
                      Browse and find a place to rent
                    </span>
                  </button>
                  <button
                    aria-pressed={registrationRole === "landlord"}
                    className={`role-option${registrationRole === "landlord" ? " selected" : ""}`}
                    onClick={() => setRegistrationRole("landlord")}
                    type="button"
                  >
                    <span className="role-option-title">
                      I have a room to rent
                    </span>
                    <span className="role-option-description">
                      Offer a room to prospective tenants
                    </span>
                  </button>
                </div>
              </fieldset>
              <label>
                Full name
                <input
                  autoComplete="name"
                  maxLength={150}
                  onChange={(event) => updateField("fullName", event.target.value)}
                  required
                  value={fields.fullName}
                />
              </label>
              <label>
                Phone number
                <input
                  autoComplete="tel"
                  maxLength={20}
                  onChange={(event) => updateField("phoneNo", event.target.value)}
                  required
                  type="tel"
                  value={fields.phoneNo}
                />
              </label>
            </>
          )}

          <label>
            Email
            <input
              autoComplete="email"
              onChange={(event) => updateField("email", event.target.value)}
              required
              type="email"
              value={fields.email}
            />
          </label>
          <label>
            Password
            <input
              autoComplete={isRegistering ? "new-password" : "current-password"}
              maxLength={128}
              minLength={isRegistering ? 8 : 1}
              onChange={(event) => updateField("password", event.target.value)}
              required
              type="password"
              value={fields.password}
            />
          </label>

          {isRegistering && registrationRole === "landlord" && (
            <label>
              Business name <span className="optional-label">Optional</span>
              <input
                autoComplete="organization"
                maxLength={150}
                onChange={(event) =>
                  updateField("businessName", event.target.value)
                }
                value={fields.businessName}
              />
            </label>
          )}

          <button
            className="primary-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting
              ? "Please wait..."
              : isRegistering
                ? "Create account"
                : "Sign in"}
          </button>
        </form>

        <p className="switch-mode">
          {isRegistering ? "Already have an account?" : "New to the platform?"}{" "}
          <button
            className="text-button"
            disabled={isSubmitting}
            onClick={() => {
              const nextMode = isRegistering ? "login" : "register";
              setMode(nextMode);
              navigate(nextMode === "register" ? "/register" : "/login");
              setErrorMessage(null);
              setNotice(null);
            }}
            type="button"
          >
            {isRegistering ? "Sign in" : "Create an account"}
          </button>
        </p>
        <p className="switch-mode">
          <AppLink className="text-button" href="/" onNavigate={navigate}>
            Browse rooms
          </AppLink>
        </p>
      </section>
    </main>
  );
}

export default App;
