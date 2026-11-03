import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  getMyReports,
  submitReport,
  type ReportCreateRequest,
  type ReportReason,
  type ReportResponse,
  type ReportTarget,
  type UserProfile,
} from "../api";

type TenantReportsPageProps = {
  accessToken: string;
  profile: UserProfile;
  onBackToDashboard: () => void;
  initialListingId?: number;
};

const reasons: { value: ReportReason; label: string }[] = [
  { value: "scam", label: "Scam" },
  { value: "fake_listing", label: "Fake listing" },
  { value: "inaccurate_info", label: "Inaccurate information" },
  { value: "abusive", label: "Abusive behavior" },
  { value: "other", label: "Other" },
];

const fieldStyle = {
  background: "#fff",
  border: "1px solid #dfe3e7",
  borderRadius: 8,
  color: "#182b36",
  font: "inherit",
  minHeight: 44,
  padding: "10px 12px",
  width: "100%",
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The request could not be completed. Please try again.";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }
  return new Intl.DateTimeFormat("en-ZA", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function getReportTargetLabel(report: ReportResponse): string {
  if (report.target_user_id !== null) {
    const accountLabel = `Account #${report.target_user_id}`;
    return report.listing_id === null
      ? accountLabel
      : `${accountLabel} · Listing #${report.listing_id}`;
  }
  return report.listing_id === null
    ? "Target unavailable"
    : `Listing #${report.listing_id}`;
}

export default function TenantReportsPage({
  accessToken,
  profile,
  onBackToDashboard,
  initialListingId,
}: TenantReportsPageProps) {
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [target, setTarget] = useState<ReportTarget>("listing");
  const [listingId, setListingId] = useState(
    initialListingId === undefined ? "" : String(initialListingId),
  );
  const [targetUserId, setTargetUserId] = useState("");
  const [reason, setReason] = useState<ReportReason>("scam");
  const [details, setDetails] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadReports(): Promise<void> {
      try {
        const currentReports = await getMyReports(accessToken);
        if (active) {
          setReports(currentReports);
        }
      } catch (error: unknown) {
        if (active) {
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    void loadReports();
    return () => {
      active = false;
    };
  }, [accessToken]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setNotice(null);

    const targetId = Number(target === "user" ? targetUserId : listingId);
    if (!Number.isSafeInteger(targetId) || targetId <= 0) {
      setErrorMessage("Enter a valid ID greater than zero.");
      return;
    }

    const payload: ReportCreateRequest =
      target === "user"
        ? {
            target,
            target_user_id: targetId,
            reason,
            details: details.trim(),
          }
        : {
            target,
            listing_id: targetId,
            reason,
            details: details.trim(),
          };

    setIsSubmitting(true);
    try {
      const createdReport = await submitReport(accessToken, payload);
      setReports((currentReports) => [createdReport, ...currentReports]);
      setDetails("");
      setNotice("Your report was submitted. You can follow its status below.");
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="page-shell">
      <section
        aria-labelledby="tenant-reports-heading"
        style={{
          background: "#fff",
          border: "1px solid #e7e9ed",
          borderRadius: 14,
          boxShadow: "0 2px 8px rgb(26 45 76 / 4%)",
          margin: "0 auto",
          maxWidth: 850,
          padding: 32,
          width: "100%",
        }}
      >
        <button
          className="secondary-button"
          onClick={onBackToDashboard}
          type="button"
        >
          Back to dashboard
        </button>
        <p className="eyebrow" style={{ marginTop: 24 }}>
          Room Rentals · Tenant reports
        </p>
        <h1 id="tenant-reports-heading">Report an issue</h1>
        <p className="intro">
          Welcome, {profile.full_name}. Submit a report and check its status
          here.
        </p>

        {errorMessage !== null && (
          <p className="message message-error" role="alert">
            {errorMessage}
          </p>
        )}
        {notice !== null && (
          <p className="message message-success" role="status">
            {notice}
          </p>
        )}

        <form
          className="auth-form"
          onSubmit={(event) => void handleSubmit(event)}
          style={{
            borderBottom: "1px solid #e7ecef",
            paddingBottom: 28,
          }}
        >
          <h2 style={{ color: "#182b36", fontSize: 21, margin: "0 0 2px" }}>
            Submit a report
          </h2>
          <label>
            What are you reporting?
            <select
              onChange={(event) =>
                setTarget(event.target.value as ReportTarget)
              }
              style={fieldStyle}
              value={target}
            >
              <option value="listing">A listing</option>
              <option value="landlord">A landlord via their listing</option>
              <option value="user">A user account</option>
            </select>
          </label>

          {target === "user" ? (
            <label>
              User account ID
              <input
                min="1"
                onChange={(event) => setTargetUserId(event.target.value)}
                required
                style={fieldStyle}
                type="number"
                value={targetUserId}
              />
            </label>
          ) : (
            <label>
              Public listing ID
              <input
                min="1"
                onChange={(event) => setListingId(event.target.value)}
                required
                style={fieldStyle}
                type="number"
                value={listingId}
              />
            </label>
          )}

          <label>
            Reason
            <select
              onChange={(event) =>
                setReason(event.target.value as ReportReason)
              }
              style={fieldStyle}
              value={reason}
            >
              {reasons.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <label>
            What happened? Include details that will help us review the report.
            <textarea
              maxLength={2000}
              minLength={10}
              onChange={(event) => setDetails(event.target.value)}
              required
              rows={5}
              style={{ ...fieldStyle, minHeight: 120, resize: "vertical" }}
              value={details}
            />
          </label>
          <button
            className="primary-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Submitting report..." : "Submit report"}
          </button>
        </form>

        <section
          aria-labelledby="report-status-heading"
          style={{ paddingTop: 24 }}
        >
          <h2
            id="report-status-heading"
            style={{ color: "#182b36", fontSize: 21, margin: "0 0 16px" }}
          >
            Your report status
          </h2>
          {isLoading && <p role="status">Loading your reports...</p>}
          {!isLoading && reports.length === 0 && (
            <p>You have not submitted any reports.</p>
          )}
          <ol
            aria-label="Submitted reports"
            style={{ display: "grid", gap: 14, listStyle: "none", padding: 0 }}
          >
            {reports.map((report) => (
              <li
                key={report.report_id}
                style={{
                  background: "#f8faf9",
                  border: "1px solid #e7ecef",
                  borderRadius: 10,
                  padding: 16,
                }}
              >
                <div
                  style={{
                    alignItems: "center",
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 8,
                    justifyContent: "space-between",
                  }}
                >
                  <strong>Report #{report.report_id}</strong>
                  <span className="role-chip">
                    {report.status.replaceAll("_", " ")}
                  </span>
                </div>
                <p style={{ color: "#596579", margin: "10px 0 6px" }}>
                  {getReportTargetLabel(report)} ·{" "}
                  {report.reason.replaceAll("_", " ")}
                </p>
                <p style={{ lineHeight: 1.55, margin: "6px 0" }}>
                  {report.details ?? "No additional details provided."}
                </p>
                <time
                  dateTime={report.created_at}
                  style={{ color: "#77868d", fontSize: 13 }}
                >
                  Submitted {formatDate(report.created_at)}
                </time>
              </li>
            ))}
          </ol>
        </section>
      </section>
    </main>
  );
}
