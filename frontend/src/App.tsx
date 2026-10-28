import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  getMyProfile,
  login,
  registerAccount,
  type UserProfile,
} from "./api";
import ListingDetailsPage from "./pages/ListingDetailsPage";
import ListingsPage from "./pages/ListingsPage";
import "./App.css";

type AuthMode = "login" | "register";
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

function App() {
  const [pathname, setPathname] = useState(window.location.pathname);
  const [mode, setMode] = useState<AuthMode>(
    window.location.pathname === "/register" ? "register" : "login",
  );
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
          ...(fields.businessName.trim()
            ? { business_name: fields.businessName }
            : {}),
        });
        setMode("login");
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
      setAccessToken(tokenResponse.access_token);
      setProfile(currentProfile);
      setFields(emptyForm);
      navigate("/profile");
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

  if (pathname === "/profile" && profile !== null && accessToken !== null) {
    return (
      <main className="page-shell">
        <section className="profile-card" aria-labelledby="profile-heading">
          <p className="eyebrow">Room Rentals</p>
          <h1 id="profile-heading">Welcome, {profile.full_name}</h1>
          <p className="intro">
            You are signed in. Your account information is shown below.
          </p>

          <dl className="profile-list">
            <div>
              <dt>Email</dt>
              <dd>{profile.email}</dd>
            </div>
            <div>
              <dt>Phone</dt>
              <dd>{profile.phone_no}</dd>
            </div>
            {profile.business_name !== null && (
              <div>
                <dt>Business</dt>
                <dd>{profile.business_name}</dd>
              </div>
            )}
            <div>
              <dt>Account roles</dt>
              <dd className="role-list">
                {profile.roles.map((role) => (
                  <span className="role-chip" key={role}>
                    {role}
                  </span>
                ))}
              </dd>
            </div>
          </dl>

          <button
            className="primary-button"
            onClick={handleSignOut}
            type="button"
          >
            Sign out
          </button>
          <p className="security-note">
            Your access token is kept in memory only. You will need to sign in
            again after reloading this page.
          </p>
        </section>
      </main>
    );
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
            ? "Create an account to find your next room."
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

          {isRegistering && (
            <>
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
              <p className="security-note">
                New accounts are registered with the tenant role.
              </p>
            </>
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
