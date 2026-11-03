import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import {
  getConversationMessages,
  getMyConversations,
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
  const [messagesReloadKey, setMessagesReloadKey] = useState(0);
  const [conversationsReloadKey, setConversationsReloadKey] = useState(0);

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
