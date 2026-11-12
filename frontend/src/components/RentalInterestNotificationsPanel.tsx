import { useEffect, useState } from "react";

import {
  getMyRentalInterestNotifications,
  markRentalInterestNotificationRead,
  type RentalInterestNotification,
} from "../api";
import "./RentalInterestPanels.css";

type RentalInterestNotificationsPanelProps = {
  accessToken: string;
  onNavigate: (path: string) => void;
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Date unavailable"
    : new Intl.DateTimeFormat("en-ZA", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(date);
}

export default function RentalInterestNotificationsPanel({
  accessToken,
  onNavigate,
}: RentalInterestNotificationsPanelProps) {
  const [notifications, setNotifications] = useState<
    RentalInterestNotification[]
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    setIsLoading(true);
    setLoadError(null);
    getMyRentalInterestNotifications(accessToken)
      .then((items) => {
        if (active) {
          setNotifications(items);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "Notifications could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [accessToken]);

  async function markAsRead(notificationId: number): Promise<void> {
    setActionError(null);
    setUpdatingId(notificationId);
    try {
      const updated = await markRentalInterestNotificationRead(
        accessToken,
        notificationId,
      );
      setNotifications((items) =>
        items.map((item) =>
          item.notification_id === updated.notification_id ? updated : item,
        ),
      );
    } catch (error: unknown) {
      setActionError(
        error instanceof Error
          ? error.message
          : "The notification could not be marked as read.",
      );
    } finally {
      setUpdatingId(null);
    }
  }

  const unreadCount = notifications.filter(
    (notification) => notification.read_at === null,
  ).length;

  return (
    <section
      aria-labelledby="rental-interest-notifications-heading"
      className="rental-interest-notifications tenant-panel"
    >
      <div className="tenant-panel-heading">
        <div>
          <p className="tenant-eyebrow tenant-eyebrow-muted">
            UPDATES
          </p>
          <h2 id="rental-interest-notifications-heading">
            Rental-interest notifications
          </h2>
        </div>
        {unreadCount > 0 && (
          <span className="rental-interest-badge">
            {unreadCount} unread
          </span>
        )}
      </div>
      {isLoading && (
        <p className="tenant-inline-state" role="status">
          Loading notifications…
        </p>
      )}
      {loadError !== null && (
        <p className="message message-error" role="alert">
          {loadError}
        </p>
      )}
      {actionError !== null && (
        <p className="message message-error" role="alert">
          {actionError}
        </p>
      )}
      {!isLoading && loadError === null && notifications.length === 0 && (
        <p className="rental-interest-empty-filter">
          Updates about registrations, waitlist changes, expiry, and closures
          will appear here.
        </p>
      )}
      {notifications.length > 0 && (
        <ul className="rental-interest-notification-list">
          {notifications.slice(0, 6).map((notification) => (
            <li
              className={
                notification.read_at === null
                  ? "rental-interest-notification unread"
                  : "rental-interest-notification"
              }
              key={notification.notification_id}
            >
              <div>
                <strong>{notification.title}</strong>
                <p>{notification.body}</p>
                <time dateTime={notification.created_at}>
                  {formatDate(notification.created_at)}
                </time>
              </div>
              <div className="rental-interest-notification-actions">
                <button
                  className="rental-interest-secondary-button"
                  onClick={() =>
                    onNavigate(`/listings/${notification.listing_id}`)
                  }
                  type="button"
                >
                  View room
                </button>
                {notification.read_at === null && (
                  <button
                    className="rental-interest-text-button"
                    disabled={updatingId !== null}
                    onClick={() =>
                      void markAsRead(notification.notification_id)
                    }
                    type="button"
                  >
                    {updatingId === notification.notification_id
                      ? "Saving…"
                      : "Mark read"}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
