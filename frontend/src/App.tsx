import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  getMyProfile,
  login,
  registerAccount,
  type UserProfile,
} from "./api";
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
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    function syncPathname() {
      setPathname(window.location.pathname);
      setMode(window.location.pathname === "/register" ? "register" : "login");
    }

    window.addEventListener("popstate", syncPathname);
    return () => window.removeEventListener("popstate", syncPathname);
  }, []);

  function navigate(path: string) {
    window.history.pushState(null, "", path);
    setPathname(path);
  }

  function updateField(field: keyof FormFields, value: string) {
    setFields((currentFields) => ({ ...currentFields, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
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
      setAccessToken(tokenResponse.access_token);
      setProfile(currentProfile);
      setFields(emptyForm);
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
    setAccessToken(null);
    setProfile(null);
    setFields(emptyForm);
    setErrorMessage(null);
    setNotice(null);
    navigate("/");
  }

  const listingMatch = pathname.match(/^\/listings\/(\d+)\/?$/);
  if (listingMatch !== null) {
    const listingId = Number(listingMatch[1]);
    if (Number.isSafeInteger(listingId) && listingId > 0) {
      return <ListingDetailsPage listingId={listingId} />;
    }
  }

  if (pathname === "/") {
    return <ListingsPage />;
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
            onSignOut={handleSignOut}
            profile={profile}
          />
        );
      }

      return (
        <DashboardPage
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
          <a className="text-button" href="/">
            Browse rooms
          </a>
        </p>
      </section>
    </main>
  );
}

export default App;
