import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  getConversationMessages,
  getMyConversations,
  getWhatsAppStatus,
  retryWhatsAppDelivery,
  startWhatsAppVerification,
  confirmWhatsAppVerification,
  unlinkWhatsApp,
  markConversationMessageRead,
  sendConversationMessage,
  type Conversation,
  type ConversationMessage,
  type UserProfile,
} from "../api";
import AppLink from "../components/AppLink";
import "./ConversationsPage.css";

type ConversationsPageProps = {
  accessToken: string;
  onNavigate: (path: string) => void;
  onSignOut: () => void;
  profile: UserProfile;
};

function formatConversationDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }
  return new Intl.DateTimeFormat("en-ZA", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function ConversationsPage({
  accessToken,
  onNavigate,
  onSignOut,
  profile,
}: ConversationsPageProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<
    number | null
  >(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [conversationError, setConversationError] = useState<string | null>(
    null,
  );
  const [messageError, setMessageError] = useState<string | null>(null);
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [updatingMessageId, setUpdatingMessageId] = useState<number | null>(
    null,
  );
  const [retryingWhatsAppMessageId, setRetryingWhatsAppMessageId] = useState<
    number | null
  >(null);
  const [messagesReloadKey, setMessagesReloadKey] = useState(0);
  const [conversationsReloadKey, setConversationsReloadKey] = useState(0);
  const [whatsappEnabled, setWhatsAppEnabled] = useState(false);
  const [whatsappStatusLoading, setWhatsAppStatusLoading] = useState(true);
  const [whatsappPhone, setWhatsAppPhone] = useState("");
  const [whatsappCode, setWhatsAppCode] = useState("");
  const [whatsappVerificationSent, setWhatsAppVerificationSent] =
    useState(false);
  const [whatsappBusy, setWhatsAppBusy] = useState(false);
  const [whatsappError, setWhatsAppError] = useState<string | null>(null);
  const [whatsappNotice, setWhatsAppNotice] = useState<string | null>(null);

  const selectedConversation = useMemo(
    () =>
      conversations.find(
        (conversation) =>
          conversation.conversation_id === selectedConversationId,
      ) ?? null,
    [conversations, selectedConversationId],
  );
  const dashboardPath = profile.roles.includes("landlord")
    ? "/landlord"
    : "/tenant";

  useEffect(() => {
    let active = true;
    setIsLoadingConversations(true);
    setConversationError(null);

    async function loadConversations(): Promise<void> {
      try {
        const results = await getMyConversations(accessToken);
        if (active) {
          setConversations(results);
          setSelectedConversationId((current) =>
            current !== null &&
            results.some(
              (conversation) =>
                conversation.conversation_id === current,
            )
              ? current
              : (results[0]?.conversation_id ?? null),
          );
        }
      } catch (error: unknown) {
        if (active) {
          setConversationError(
            error instanceof Error
              ? error.message
              : "Your conversations could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setIsLoadingConversations(false);
        }
      }
    }

    void loadConversations();
    return () => {
      active = false;
    };
  }, [accessToken, conversationsReloadKey]);

  useEffect(() => {
    let active = true;
    setWhatsAppStatusLoading(true);
    getWhatsAppStatus(accessToken)
      .then((status) => {
        if (active) {
          setWhatsAppEnabled(status.enabled);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setWhatsAppError(
            error instanceof Error
              ? error.message
              : "WhatsApp preferences could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (active) {
          setWhatsAppStatusLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [accessToken]);

  useEffect(() => {
    if (selectedConversationId === null) {
      setMessages([]);
      setIsLoadingMessages(false);
      return;
    }

    const conversationId = selectedConversationId;
    let active = true;
    setMessages([]);
    setMessageError(null);
    setIsLoadingMessages(true);

    async function loadMessages(): Promise<void> {
      try {
        const results = await getConversationMessages(
          accessToken,
          conversationId,
        );
        if (active) {
          setMessages(results);
        }
      } catch (error: unknown) {
        if (active) {
          setMessageError(
            error instanceof Error
              ? error.message
              : "Messages could not be loaded.",
          );
        }
      } finally {
        if (active) {
          setIsLoadingMessages(false);
        }
      }
    }

    void loadMessages();
    return () => {
      active = false;
    };
  }, [accessToken, messagesReloadKey, selectedConversationId]);

  async function handleSendMessage(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    const content = draft.trim();
    if (selectedConversationId === null || content === "" || isSending) {
      return;
    }

    setMessageError(null);
    setIsSending(true);
    try {
      const sentMessage = await sendConversationMessage(
        accessToken,
        selectedConversationId,
        content,
      );
      setMessages((current) => [...current, sentMessage]);
      setDraft("");
    } catch (error: unknown) {
      setMessageError(
        error instanceof Error
          ? error.message
          : "Your message could not be sent.",
      );
    } finally {
      setIsSending(false);
    }
  }

  async function handleMarkRead(messageId: number): Promise<void> {
    if (selectedConversationId === null || updatingMessageId !== null) {
      return;
    }

    setMessageError(null);
    setUpdatingMessageId(messageId);
    try {
      const updatedMessage = await markConversationMessageRead(
        accessToken,
        selectedConversationId,
        messageId,
      );
      setMessages((current) =>
        current.map((message) =>
          message.message_id === updatedMessage.message_id
            ? updatedMessage
            : message,
        ),
      );
    } catch (error: unknown) {
      setMessageError(
        error instanceof Error
          ? error.message
          : "The message status could not be updated.",
      );
    } finally {
      setUpdatingMessageId(null);
    }
  }

  async function handleStartWhatsAppVerification(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setWhatsAppError(null);
    setWhatsAppNotice(null);
    setWhatsAppBusy(true);
    try {
      const result = await startWhatsAppVerification(
        accessToken,
        whatsappPhone.trim(),
      );
      setWhatsAppVerificationSent(true);
      setWhatsAppPhone("");
      setWhatsAppNotice(result.detail);
    } catch (error: unknown) {
      setWhatsAppError(
        error instanceof Error
          ? error.message
          : "WhatsApp verification could not be started.",
      );
    } finally {
      setWhatsAppBusy(false);
    }
  }

  async function handleConfirmWhatsAppVerification(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setWhatsAppError(null);
    setWhatsAppNotice(null);
    setWhatsAppBusy(true);
    try {
      const status = await confirmWhatsAppVerification(
        accessToken,
        whatsappCode.trim(),
      );
      setWhatsAppEnabled(status.enabled);
      setWhatsAppVerificationSent(false);
      setWhatsAppCode("");
      setWhatsAppNotice("WhatsApp messaging is enabled.");
    } catch (error: unknown) {
      setWhatsAppError(
        error instanceof Error
          ? error.message
          : "The WhatsApp verification code could not be confirmed.",
      );
    } finally {
      setWhatsAppBusy(false);
    }
  }

  async function handleUnlinkWhatsApp(): Promise<void> {
    setWhatsAppError(null);
    setWhatsAppNotice(null);
    setWhatsAppBusy(true);
    try {
      await unlinkWhatsApp(accessToken);
      setWhatsAppEnabled(false);
      setWhatsAppVerificationSent(false);
      setWhatsAppCode("");
      setWhatsAppNotice("WhatsApp messaging has been turned off.");
    } catch (error: unknown) {
      setWhatsAppError(
        error instanceof Error
          ? error.message
          : "WhatsApp messaging could not be turned off.",
      );
    } finally {
      setWhatsAppBusy(false);
    }
  }

  async function handleRetryWhatsAppDelivery(messageId: number): Promise<void> {
    if (selectedConversationId === null || retryingWhatsAppMessageId !== null) {
      return;
    }

    setMessageError(null);
    setRetryingWhatsAppMessageId(messageId);
    try {
      const updatedMessage = await retryWhatsAppDelivery(
        accessToken,
        selectedConversationId,
        messageId,
      );
      setMessages((current) =>
        current.map((message) =>
          message.message_id === updatedMessage.message_id
            ? updatedMessage
            : message,
        ),
      );
    } catch (error: unknown) {
      setMessageError(
        error instanceof Error
          ? error.message
          : "WhatsApp delivery could not be retried.",
      );
    } finally {
      setRetryingWhatsAppMessageId(null);
    }
  }

  return (
    <main className="page-shell conversations-page">
      <section className="conversations-shell">
        <header className="conversations-header">
          <div>
            <p className="eyebrow">Room Rentals</p>
            <h1>Your conversations</h1>
            <p className="intro">
              Talk with tenants and landlords about room enquiries.
            </p>
          </div>
          <nav aria-label="Conversation navigation">
            <AppLink
              className="conversations-back-link"
              href={dashboardPath}
              onNavigate={onNavigate}
            >
              Back to dashboard
            </AppLink>
            <button
              className="secondary-button"
              onClick={onSignOut}
              type="button"
            >
              Sign out
            </button>
          </nav>
        </header>

        <div className="conversations-layout">
          <section
            aria-labelledby="conversation-list-heading"
            className="conversation-list-panel"
          >
            <div className="conversation-panel-heading">
              <div>
                <h2 id="conversation-list-heading">Inbox</h2>
                <p>
                  {conversations.length}{" "}
                  {conversations.length === 1 ? "conversation" : "conversations"}
                </p>
              </div>
              <button
                aria-label="Refresh conversations"
                className="conversation-refresh-button"
                disabled={isLoadingConversations}
                onClick={() =>
                  setConversationsReloadKey((current) => current + 1)
                }
                type="button"
              >
                Refresh
              </button>
            </div>

            <section
              aria-labelledby="whatsapp-settings-heading"
              className="whatsapp-settings"
            >
              <h3 id="whatsapp-settings-heading">WhatsApp relay</h3>
              <p>
                Message through the platform’s WhatsApp Business number.
                Participants never see each other’s phone numbers. Send STOP on
                WhatsApp or unlink here to opt out.
              </p>
              {whatsappError !== null && (
                <p className="message message-error" role="alert">
                  {whatsappError}
                </p>
              )}
              {whatsappNotice !== null && (
                <p className="whatsapp-notice" role="status">
                  {whatsappNotice}
                </p>
              )}
              {whatsappStatusLoading ? (
                <p role="status">Checking WhatsApp settings…</p>
              ) : whatsappEnabled ? (
                <button
                  className="secondary-button"
                  disabled={whatsappBusy}
                  onClick={() => void handleUnlinkWhatsApp()}
                  type="button"
                >
                  Turn off WhatsApp
                </button>
              ) : whatsappVerificationSent ? (
                <form
                  className="whatsapp-settings-form"
                  onSubmit={(event) => void handleConfirmWhatsAppVerification(event)}
                >
                  <label htmlFor="whatsapp-verification-code">
                    Six-digit verification code
                  </label>
                  <input
                    autoComplete="one-time-code"
                    id="whatsapp-verification-code"
                    inputMode="numeric"
                    maxLength={6}
                    onChange={(event) => setWhatsAppCode(event.target.value)}
                    pattern="[0-9]{6}"
                    required
                    value={whatsappCode}
                  />
                  <button disabled={whatsappBusy} type="submit">
                    Verify number
                  </button>
                </form>
              ) : (
                <form
                  className="whatsapp-settings-form"
                  onSubmit={(event) => void handleStartWhatsAppVerification(event)}
                >
                  <label htmlFor="whatsapp-phone-number">
                    WhatsApp number (international format)
                  </label>
                  <input
                    autoComplete="tel"
                    id="whatsapp-phone-number"
                    onChange={(event) => setWhatsAppPhone(event.target.value)}
                    pattern="\+[1-9][0-9]{7,14}"
                    placeholder="+27123456789"
                    required
                    type="tel"
                    value={whatsappPhone}
                  />
                  <label className="whatsapp-consent">
                    <input required type="checkbox" />
                    <span>
                      I agree to receive conversation messages on WhatsApp
                      from the platform’s business number.
                    </span>
                  </label>
                  <button disabled={whatsappBusy} type="submit">
                    Verify and enable
                  </button>
                </form>
              )}
            </section>

            {conversationError !== null && (
              <p className="message message-error" role="alert">
                {conversationError}
              </p>
            )}
            {isLoadingConversations && (
              <p className="conversation-loading" role="status">
                Loading conversations…
              </p>
            )}
            {!isLoadingConversations &&
              conversationError === null &&
              conversations.length === 0 && (
                <div className="conversation-empty-state">
                  <span aria-hidden="true">✉</span>
                  <h3>No conversations yet</h3>
                  <p>
                    Send a contact request for a room to start a conversation
                    with its landlord.
                  </p>
                  <AppLink href="/" onNavigate={onNavigate}>
                    Browse rooms
                  </AppLink>
                </div>
              )}
            {!isLoadingConversations && conversations.length > 0 && (
              <ul className="conversation-list">
                {conversations.map((conversation) => (
                  <li key={conversation.conversation_id}>
                    <button
                      aria-current={
                        conversation.conversation_id ===
                        selectedConversationId
                          ? "true"
                          : undefined
                      }
                      className={`conversation-list-item${
                        conversation.conversation_id ===
                        selectedConversationId
                          ? " selected"
                          : ""
                      }`}
                      onClick={() =>
                        setSelectedConversationId(
                          conversation.conversation_id,
                        )
                      }
                      type="button"
                    >
                      <span aria-hidden="true" className="conversation-avatar">
                        {conversation.conversation_id}
                      </span>
                      <span className="conversation-list-copy">
                        <strong>
                          Contact request #{conversation.contact_request_id}
                        </strong>
                        <time dateTime={conversation.created_at}>
                          Started{" "}
                          {formatConversationDate(conversation.created_at)}
                        </time>
                      </span>
                      <span aria-hidden="true" className="conversation-chevron">
                        ›
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section
            aria-label="Messages"
            className="conversation-message-panel"
          >
            {selectedConversation === null ? (
              <div className="conversation-select-prompt">
                <span aria-hidden="true">↖</span>
                <h2>Select a conversation</h2>
                <p>Choose an enquiry from your inbox to view its messages.</p>
              </div>
            ) : (
              <>
                <header className="conversation-thread-header">
                  <div>
                    <p className="eyebrow">ROOM ENQUIRY</p>
                    <h2>
                      Contact request #{selectedConversation.contact_request_id}
                    </h2>
                    <p>
                      Conversation started{" "}
                      {formatConversationDate(selectedConversation.created_at)}
                    </p>
                  </div>
                  <button
                    aria-label="Refresh messages"
                    className="conversation-refresh-button"
                    disabled={isLoadingMessages}
                    onClick={() =>
                      setMessagesReloadKey((current) => current + 1)
                    }
                    type="button"
                  >
                    Refresh
                  </button>
                </header>

                <div
                  aria-live="polite"
                  className="conversation-message-list"
                  role="log"
                >
                  {isLoadingMessages && (
                    <p className="conversation-loading" role="status">
                      Loading messages…
                    </p>
                  )}
                  {!isLoadingMessages &&
                    messageError === null &&
                    messages.length === 0 && (
                      <div className="conversation-thread-empty">
                        <p>No messages in this conversation yet.</p>
                        <p>Send a message to start the discussion.</p>
                      </div>
                    )}
                  {messages.map((message) => {
                    const isOwnMessage = message.sender_id === profile.user_id;
                    return (
                      <article
                        className={`conversation-message${
                          isOwnMessage ? " own" : ""
                        }`}
                        key={message.message_id}
                      >
                        <div className="conversation-message-meta">
                          <strong>{isOwnMessage ? "You" : "Other participant"}</strong>
                          <time dateTime={message.sent_at}>
                            {formatConversationDate(message.sent_at)}
                          </time>
                        </div>
                        <p>{message.content}</p>
                        <div className="conversation-message-footer">
                          <span>
                            {isOwnMessage && message.status === "read"
                              ? "Read"
                              : message.status === "read"
                                ? "Read"
                                : "Sent"}
                          </span>
                          {isOwnMessage &&
                            message.whatsapp_delivery_status === "sent" && (
                              <span>Sent via WhatsApp</span>
                            )}
                          {isOwnMessage &&
                            message.whatsapp_delivery_status === "failed" && (
                              <button
                                className="conversation-read-button"
                                disabled={retryingWhatsAppMessageId !== null}
                                onClick={() =>
                                  void handleRetryWhatsAppDelivery(
                                    message.message_id,
                                  )
                                }
                                type="button"
                              >
                                {retryingWhatsAppMessageId ===
                                message.message_id
                                  ? "Retrying…"
                                  : "Retry WhatsApp"}
                              </button>
                            )}
                          {!isOwnMessage && message.status === "sent" && (
                            <button
                              className="conversation-read-button"
                              disabled={updatingMessageId !== null}
                              onClick={() =>
                                void handleMarkRead(message.message_id)
                              }
                              type="button"
                            >
                              {updatingMessageId === message.message_id
                                ? "Updating…"
                                : "Mark as read"}
                            </button>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>

                {messageError !== null && (
                  <p className="message message-error" role="alert">
                    {messageError}
                  </p>
                )}
                <form
                  className="conversation-compose"
                  onSubmit={(event) => void handleSendMessage(event)}
                >
                  <label htmlFor="conversation-message-input">
                    Write a message
                  </label>
                  <textarea
                    id="conversation-message-input"
                    maxLength={4000}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="Type your message…"
                    required
                    rows={3}
                    value={draft}
                  />
                  <div className="conversation-compose-footer">
                    <span>{draft.length}/4000</span>
                    <button
                      className="primary-button"
                      disabled={draft.trim() === "" || isSending}
                      type="submit"
                    >
                      {isSending ? "Sending…" : "Send message"}
                    </button>
                  </div>
                </form>
              </>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}
