import type { UserProfile } from "../api";

export type DashboardRole = "tenant" | "landlord" | "admin";

type DashboardPageProps = {
  profile: UserProfile;
  role: DashboardRole;
  onSignOut: () => void;
};

const dashboardContent: Record<
  DashboardRole,
  { heading: string; description: string; nextStep: string }
> = {
  tenant: {
    heading: "Your tenant dashboard",
    description: "Find a room that feels like home.",
    nextStep:
      "Browse available rooms without needing an account. Tenant contact-request tools are not available yet.",
  },
  landlord: {
    heading: "Your landlord dashboard",
    description: "Manage your room rentals from one place.",
    nextStep:
      "Your landlord account is ready. Listing management tools are not available yet.",
  },
  admin: {
    heading: "Admin workspace",
    description: "This area is for authorized platform administrators.",
    nextStep:
      "Admin invitations and two-step verification have not been implemented yet.",
  },
};

export default function DashboardPage({
  profile,
  role,
  onSignOut,
}: DashboardPageProps) {
  const content = dashboardContent[role];

  return (
    <main className="page-shell">
      <section className="profile-card" aria-labelledby="dashboard-heading">
        <p className="eyebrow">Room Rentals</p>
        <h1 id="dashboard-heading">{content.heading}</h1>
        <p className="intro">Welcome, {profile.full_name}. {content.description}</p>

        <dl className="profile-list">
          <div>
            <dt>Email</dt>
            <dd>{profile.email}</dd>
          </div>
          <div>
            <dt>Account role</dt>
            <dd className="role-list">
              <span className="role-chip">{role}</span>
            </dd>
          </div>
        </dl>

        <p className="dashboard-note">{content.nextStep}</p>

        <div className="dashboard-actions">
          <a className="primary-button dashboard-link" href="/">
            Browse rooms
          </a>
          <button
            className="secondary-button"
            onClick={onSignOut}
            type="button"
          >
            Sign out
          </button>
        </div>
      </section>
    </main>
  );
}
