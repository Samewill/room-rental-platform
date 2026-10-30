import { useEffect, useState } from "react";

import {
  assignReportToSelf,
  dismissReport,
  getAdminReports,
  getReportHistory,
  resolveReport,
  type ReportHistoryRecord,
  type ReportResponse,
  type ReportStatus,
  type UserProfile,
} from "../api";

type AdminReportsPageProps = {
  accessToken: string;
  profile: UserProfile;
  onBackToDashboard: () => void;
  onSignOut: () => void;
};

const statusOptions: { value: ReportStatus | "all"; label: string }[] = [
  { value: "all", label: "All reports" },
  { value: "open", label: "Open" },
  { value: "under_review", label: "Under review" },
  { value: "resolved", label: "Resolved" },
  { value: "dismissed", label: "Dismissed" },
];

const noteStyle = {
  background: "#fff",
  border: "1px solid #dfe3e7",
  borderRadius: 8,
  color: "#182b36",
  font: "inherit",
  minHeight: 78,
  padding: "10px 12px",
  resize: "vertical" as const,
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

function getTargetLabel(report: ReportResponse): string {
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

export default function AdminReportsPage({
  accessToken,
  profile,
  onBackToDashboard,
  onSignOut,
}: AdminReportsPageProps) {
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [statusFilter, setStatusFilter] = useState<ReportStatus | "all">(
    "open",
  );
  const [historyByReport, setHistoryByReport] = useState<
    Record<number, ReportHistoryRecord[]>
  >({});
  const [expandedHistory, setExpandedHistory] = useState<number[]>([]);
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [busyReportId, setBusyReportId] = useState<number | null>(null);
  const [historyLoadingId, setHistoryLoadingId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setErrorMessage(null);

    async function loadReports(): Promise<void> {
      try {
        const currentReports = await getAdminReports(
          accessToken,
          statusFilter === "all" ? undefined : statusFilter,
        );
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
  }, [accessToken, statusFilter]);

  async function runAction(
    reportId: number,
    action: () => Promise<ReportResponse>,
    successMessage: string,
  ): Promise<void> {
    setBusyReportId(reportId);
    setErrorMessage(null);
    setNotice(null);
    try {
      const updatedReport = await action();
      setReports((currentReports) => {
        const remainsInFilter =
          statusFilter === "all" || updatedReport.status === statusFilter;
        if (!remainsInFilter) {
          return currentReports.filter(
            (report) => report.report_id !== reportId,
          );
        }
        return currentReports.map((report) =>
          report.report_id === reportId ? updatedReport : report,
        );
      });
      setHistoryByReport((current) => {
        const next = { ...current };
        delete next[reportId];
        return next;
      });
      setNotice(successMessage);
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setBusyReportId(null);
    }
  }

  async function toggleHistory(reportId: number): Promise<void> {
    setErrorMessage(null);
    if (expandedHistory.includes(reportId)) {
      setExpandedHistory((current) =>
        current.filter((id) => id !== reportId),
      );
      return;
    }

    setExpandedHistory((current) => [...current, reportId]);
    if (historyByReport[reportId] !== undefined) {
      return;
    }

    setHistoryLoadingId(reportId);
    try {
      const history = await getReportHistory(accessToken, reportId);
      setHistoryByReport((current) => ({ ...current, [reportId]: history }));
    } catch (error: unknown) {
      setErrorMessage(getErrorMessage(error));
      setExpandedHistory((current) =>
        current.filter((id) => id !== reportId),
      );
    } finally {
      setHistoryLoadingId(null);
    }
  }

  function renderReport(report: ReportResponse) {
    const note = notes[report.report_id] ?? "";
    const historyIsExpanded = expandedHistory.includes(report.report_id);
    const history = historyByReport[report.report_id];
    const isBusy = busyReportId === report.report_id;

    return (
      <li
        key={report.report_id}
        style={{
          background: "#fff",
          border: "1px solid #e3e7ed",
          borderRadius: 10,
          display: "grid",
          gap: 14,
          padding: 18,
        }}
      >
        <div
          style={{
            alignItems: "center",
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            justifyContent: "space-between",
          }}
        >
          <h3 style={{ color: "#182b36", margin: 0 }}>
            Report #{report.report_id}
          </h3>
          <span className="role-chip">
            {report.status.replaceAll("_", " ")}
          </span>
        </div>

        <dl
          style={{
            display: "grid",
            gap: "10px 20px",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            margin: 0,
          }}
        >
          <div>
            <dt style={{ color: "#77868d", fontSize: 13 }}>Target</dt>
            <dd style={{ margin: "4px 0 0" }}>{getTargetLabel(report)}</dd>
          </div>
          <div>
            <dt style={{ color: "#77868d", fontSize: 13 }}>Reason</dt>
            <dd style={{ margin: "4px 0 0" }}>
              {report.reason.replaceAll("_", " ")}
            </dd>
          </div>
          <div>
            <dt style={{ color: "#77868d", fontSize: 13 }}>Submitted by</dt>
            <dd style={{ margin: "4px 0 0" }}>Tenant #{report.tenant_id}</dd>
          </div>
          <div>
            <dt style={{ color: "#77868d", fontSize: 13 }}>Assigned admin</dt>
            <dd style={{ margin: "4px 0 0" }}>
              {report.admin_id === null
                ? "Not assigned"
                : `Admin #${report.admin_id}`}
            </dd>
          </div>
        </dl>

        <p style={{ lineHeight: 1.6, margin: 0 }}>
          {report.details ?? "No additional details provided."}
        </p>
        <time
          dateTime={report.created_at}
          style={{ color: "#77868d", fontSize: 13 }}
        >
          Submitted {formatDate(report.created_at)}
        </time>

        {report.status === "under_review" && (
          <label
            style={{
              color: "#344852",
              display: "grid",
              fontSize: 14,
              fontWeight: 650,
              gap: 7,
            }}
          >
            Resolution or dismissal note (optional)
            <textarea
              maxLength={2000}
              onChange={(event) =>
                setNotes((current) => ({
                  ...current,
                  [report.report_id]: event.target.value,
                }))
              }
              rows={3}
              style={noteStyle}
              value={note}
            />
          </label>
        )}

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
          }}
        >
          {report.status === "open" && report.admin_id === null && (
            <button
              className="primary-button"
              disabled={isBusy}
              onClick={() =>
                void runAction(
                  report.report_id,
                  () => assignReportToSelf(accessToken, report.report_id),
                  `Report #${report.report_id} is now under review.`,
                )
              }
              style={{ margin: 0, width: "auto" }}
              type="button"
            >
              Assign to me
            </button>
          )}
          {report.status === "under_review" && (
            <>
              <button
                className="primary-button"
                disabled={isBusy}
                onClick={() =>
                  void runAction(
                    report.report_id,
                    () =>
                      resolveReport(accessToken, report.report_id, {
                        note: note.trim() || undefined,
                      }),
                    `Report #${report.report_id} was resolved.`,
                  )
                }
                style={{ margin: 0, width: "auto" }}
                type="button"
              >
                Resolve
              </button>
              <button
                className="secondary-button"
                disabled={isBusy}
                onClick={() =>
                  void runAction(
                    report.report_id,
                    () =>
                      dismissReport(accessToken, report.report_id, {
                        note: note.trim() || undefined,
                      }),
                    `Report #${report.report_id} was dismissed.`,
                  )
                }
                type="button"
              >
                Dismiss
              </button>
            </>
          )}
          <button
            className="secondary-button"
            disabled={historyLoadingId === report.report_id}
            onClick={() => void toggleHistory(report.report_id)}
            type="button"
          >
            {historyLoadingId === report.report_id
              ? "Loading history..."
              : historyIsExpanded
                ? "Hide history"
                : "View history"}
          </button>
        </div>

        {historyIsExpanded && (
          <section aria-label={`History for report ${report.report_id}`}>
            <h4 style={{ color: "#182b36", margin: "0 0 8px" }}>
              Report history
            </h4>
            {history?.length === 0 && <p>No history records yet.</p>}
            {history !== undefined && history.length > 0 && (
              <ol style={{ display: "grid", gap: 8, paddingLeft: 22 }}>
                {history.map((item) => (
                  <li key={item.history_id}>
                    <strong>{item.action.replaceAll("_", " ")}</strong>
                    {" · "}
                    {formatDate(item.created_at)}
                    {" · User #"}
                    {item.actor_user_id}
                    {item.note !== null && <p>{item.note}</p>}
                  </li>
                ))}
              </ol>
            )}
          </section>
        )}
      </li>
    );
  }

  return (
    <main className="page-shell">
      <section
        aria-labelledby="admin-reports-heading"
        style={{
          background: "#f7f8fa",
          border: "1px solid #e3e7ed",
          borderRadius: 14,
          margin: "0 auto",
          maxWidth: 1000,
          padding: 28,
          width: "100%",
        }}
      >
        <header
          style={{
            alignItems: "center",
            display: "flex",
            flexWrap: "wrap",
            gap: 16,
            justifyContent: "space-between",
            marginBottom: 20,
          }}
        >
          <div>
            <p className="eyebrow">Room Rentals · Administration</p>
            <h1 id="admin-reports-heading">Report queue</h1>
            <p className="intro" style={{ marginBottom: 0 }}>
              Welcome, {profile.full_name}. Review, assign, and close reports.
            </p>
          </div>
          <button
            className="secondary-button"
            onClick={onSignOut}
            type="button"
          >
            Sign out
          </button>
        </header>

        <div
          style={{
            alignItems: "end",
            display: "flex",
            flexWrap: "wrap",
            gap: 12,
            justifyContent: "space-between",
            marginBottom: 20,
          }}
        >
          <label
            style={{
              color: "#344852",
              display: "grid",
              fontSize: 14,
              fontWeight: 650,
              gap: 7,
              maxWidth: 280,
              width: "100%",
            }}
          >
            Filter reports
            <select
              onChange={(event) =>
                setStatusFilter(event.target.value as ReportStatus | "all")
              }
              style={noteStyle}
              value={statusFilter}
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button
            className="secondary-button"
            onClick={onBackToDashboard}
            type="button"
          >
            Back to listing moderation
          </button>
        </div>

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
        {isLoading && <p role="status">Loading report queue...</p>}
        {!isLoading && reports.length === 0 && (
          <p>No reports match this filter.</p>
        )}
        <ol
          aria-label="Admin report queue"
          style={{ display: "grid", gap: 14, listStyle: "none", padding: 0 }}
        >
          {reports.map(renderReport)}
        </ol>
      </section>
    </main>
  );
}
