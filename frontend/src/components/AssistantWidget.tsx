import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";

import {
  confirmAssistantListing,
  createAssistantConversation,
  createContactRequest,
  getAssistantConversation,
  getAssistantConversations,
  sendAssistantMessage,
  uploadListingPhoto,
  type AssistantConversation,
  type AssistantMessage,
  type AssistantRole,
} from "../api";
import type { Listing } from "../types/listing";
import "./AssistantWidget.css";

type AssistantWidgetProps = {
  accessToken: string;
  onNavigate: (path: string) => void;
  role: AssistantRole;
};

function formatRent(value: string | number): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return "Rent unavailable";
  }
  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatAvailability(value: string): string {
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return "Availability date unavailable";
  }
  return new Intl.DateTimeFormat("en-ZA", { dateStyle: "medium" }).format(
    parsed,
  );
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The request could not be completed. Please try again.";
}

function makeLocalUserMessage(content: string): AssistantMessage {
  return {
    message_id: -Date.now(),
    sender_role: "user",
    content,
    created_at: new Date().toISOString(),
    listings: [],
    draft: null,
    created_listing: null,
    notification: null,
  };
}

function ListingResultCard({
  accessToken,
  areaName,
  listing,
  onNavigate,
}: {
  accessToken: string;
  areaName: string;
  listing: Listing;
  onNavigate: (path: string) => void;
}) {
  const [isRequestingContact, setIsRequestingContact] = useState(false);
  const [contactRequested, setContactRequested] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function requestContact(): Promise<void> {
    setError(null);
    setIsRequestingContact(true);
    try {
      await createContactRequest(accessToken, listing.listing_id);
      setContactRequested(true);
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setIsRequestingContact(false);
    }
  }

  return (
    <article className="assistant-listing-card">
      {listing.photos[0] && (
        <img
          alt={`Room interior for ${listing.title}`}
          className="assistant-listing-photo"
          src={listing.photos[0].url}
        />
      )}
      <div className="assistant-listing-content">
        <p className="assistant-listing-type">{listing.room_type.replaceAll("_", " ")}</p>
        <h4>{listing.title}</h4>
        <p className="assistant-listing-rent">
          {formatRent(listing.monthly_rent)} <span>/ month</span>
        </p>
        <p>
          {areaName} · {listing.address}
        </p>
        <p>Available {formatAvailability(listing.date_available)}</p>
        {listing.amenities.length > 0 && (
          <p>Amenities: {listing.amenities.join(", ")}</p>
        )}
        {error !== null && (
          <p className="assistant-error" role="alert">
            {error}
          </p>
        )}
        {contactRequested ? (
          <div className="assistant-contact-success" role="status">
            <span>Contact request sent.</span>
            <button
              className="assistant-inline-button"
              onClick={() => onNavigate("/conversations")}
              type="button"
            >
              Open Messages
            </button>
          </div>
        ) : (
          <button
            className="assistant-secondary-button"
            disabled={isRequestingContact}
            onClick={() => void requestContact()}
            type="button"
          >
            {isRequestingContact ? "Sending request…" : "Contact landlord"}
          </button>
        )}
        <button
          className="assistant-inline-button"
          onClick={() => onNavigate(`/listings/${listing.listing_id}`)}
          type="button"
        >
          View listing
        </button>
      </div>
    </article>
  );
}

function DraftSummary({
  accessToken,
  conversationId,
  draft,
  onConfirmed,
}: {
  accessToken: string;
  conversationId: number;
  draft: NonNullable<AssistantMessage["draft"]>;
  onConfirmed: () => void;
}) {
  const [files, setFiles] = useState<File[]>([]);
  const [isConfirming, setIsConfirming] = useState(false);
  const [created, setCreated] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function choosePhotos(event: ChangeEvent<HTMLInputElement>): void {
    const selected = Array.from(event.currentTarget.files ?? []);
    event.currentTarget.value = "";
    const invalid = selected.find(
      (file) =>
        !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
        file.size > 10 * 1024 * 1024,
    );
    if (invalid !== undefined) {
      setError(
        "Choose JPEG, PNG, or WebP photos that are each 10 MB or smaller.",
      );
      return;
    }
    setError(null);
    setFiles(selected);
  }

  async function confirm(): Promise<void> {
    setError(null);
    setIsConfirming(true);
    try {
      const { listing } = await confirmAssistantListing(
        accessToken,
        conversationId,
      );
      setCreated(true);
      const uploadFailures: string[] = [];
      for (const file of files) {
        try {
          await uploadListingPhoto(accessToken, listing.listing_id, file);
        } catch (uploadError: unknown) {
          uploadFailures.push(`${file.name}: ${getErrorMessage(uploadError)}`);
        }
      }
      if (uploadFailures.length > 0) {
        setError(
          `The listing was created as a draft, but these photos could not be uploaded: ${uploadFailures.join("; ")}`,
        );
      }
      onConfirmed();
    } catch (confirmError: unknown) {
      setError(getErrorMessage(confirmError));
    } finally {
      setIsConfirming(false);
    }
  }

  const summaryFields: Array<[string, string | number | null]> = [
    ["Area", draft.area_name],
    ["Room type", draft.room_type?.replaceAll("_", " ") ?? null],
    ["Monthly rent", draft.monthly_rent ? formatRent(draft.monthly_rent) : null],
    [
      "Deposit",
      draft.deposit_amount ? formatRent(draft.deposit_amount) : null,
    ],
    ["Address", draft.address],
    ["Available", draft.date_available],
    ["Title", draft.title],
    ["Description", draft.description],
    ["Amenities", draft.amenities.length ? draft.amenities.join(", ") : "None"],
  ];

  return (
    <section className="assistant-draft" aria-label="Listing draft summary">
      <h4>Review listing details</h4>
      <dl>
        {summaryFields.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value ?? "Not provided"}</dd>
          </div>
        ))}
      </dl>
      {!draft.ready_to_confirm && draft.missing_fields.length > 0 && (
        <p>Still needed: {draft.missing_fields.join(", ")}.</p>
      )}
      {draft.ready_to_confirm && (
        <>
          <label className="assistant-photo-picker">
            Add listing photos <span>(optional)</span>
            <input
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={choosePhotos}
              type="file"
            />
          </label>
          {files.length > 0 && (
            <p>{files.length} photo{files.length === 1 ? "" : "s"} selected</p>
          )}
          <button
            className="assistant-primary-button"
            disabled={isConfirming || created}
            onClick={() => void confirm()}
            type="button"
          >
            {isConfirming
              ? "Creating draft…"
              : created
                ? "Draft created"
                : "Confirm and create draft"}
          </button>
        </>
      )}
      {error !== null && (
        <p className="assistant-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

export default function AssistantWidget({
  accessToken,
  onNavigate,
  role,
}: AssistantWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [conversations, setConversations] = useState<AssistantConversation[]>(
    [],
  );
  const [activeConversationId, setActiveConversationId] = useState<
    number | null
  >(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [messageText, setMessageText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messageListRef = useRef<HTMLDivElement>(null);
  const conversationIdsRef = useRef<number[]>([]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    let active = true;
    async function refreshConversations(): Promise<void> {
      try {
        const items = await getAssistantConversations(accessToken);
        if (!active) {
          return;
        }
        const roleConversations = items.filter(
          (item) => item.assistant_role === role,
        );
        const newConversations = roleConversations.filter(
          (item) => !conversationIdsRef.current.includes(item.conversation_id),
        );
        const latestNewConversation = newConversations[0];
        setConversations(roleConversations);
        conversationIdsRef.current = roleConversations.map(
          (item) => item.conversation_id,
        );
        if (latestNewConversation !== undefined) {
          setMessages([]);
        }
        setActiveConversationId((current) => {
          if (current !== null) {
            return latestNewConversation?.conversation_id ?? current;
          }
          return roleConversations[0]?.conversation_id ?? null;
        });
      } catch (requestError: unknown) {
        if (active) {
          setError(getErrorMessage(requestError));
        }
      }
    }

    setError(null);
    void refreshConversations();
    const intervalId = window.setInterval(
      () => void refreshConversations(),
      10_000,
    );
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [accessToken, isOpen, role]);

  useEffect(() => {
    if (!isOpen || activeConversationId === null) {
      setMessages([]);
      return;
    }
    if (isSending) {
      return;
    }
    let active = true;
    setIsLoading(true);
    setError(null);
    getAssistantConversation(accessToken, activeConversationId)
      .then((conversation) => {
        if (active) {
          setMessages(conversation.messages);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(getErrorMessage(requestError));
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
  }, [accessToken, activeConversationId, isOpen, isSending]);

  useEffect(() => {
    messageListRef.current?.scrollTo({
      top: messageListRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  async function startConversation(): Promise<void> {
    setError(null);
    try {
      const conversation = await createAssistantConversation(
        accessToken,
        role,
      );
      setConversations((current) => [conversation, ...current]);
      conversationIdsRef.current = [
        conversation.conversation_id,
        ...conversationIdsRef.current,
      ];
      setActiveConversationId(conversation.conversation_id);
      setMessages([]);
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    }
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const content = messageText.trim();
    if (!content || isSending) {
      return;
    }
    setError(null);
    setIsSending(true);
    try {
      let conversationId = activeConversationId;
      if (conversationId === null) {
        const conversation = await createAssistantConversation(
          accessToken,
          role,
        );
        conversationId = conversation.conversation_id;
        setConversations((current) => [conversation, ...current]);
        conversationIdsRef.current = [
          conversation.conversation_id,
          ...conversationIdsRef.current,
        ];
        setActiveConversationId(conversationId);
      }
      setMessageText("");
      setMessages((current) => [...current, makeLocalUserMessage(content)]);
      const response = await sendAssistantMessage(
        accessToken,
        conversationId,
        content,
      );
      setMessages((current) => [...current, response]);
      setConversations((current) =>
        current
          .map((conversation) =>
            conversation.conversation_id === conversationId
              ? { ...conversation, updated_at: response.created_at }
              : conversation,
          )
          .sort((left, right) =>
            right.updated_at.localeCompare(left.updated_at),
          ),
      );
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
      setMessageText(content);
    } finally {
      setIsSending(false);
    }
  }

  function selectConversation(conversationId: number): void {
    setError(null);
    setMessages([]);
    setActiveConversationId(conversationId);
  }

  async function reloadActiveConversation(): Promise<void> {
    if (activeConversationId === null) {
      return;
    }
    try {
      const conversation = await getAssistantConversation(
        accessToken,
        activeConversationId,
      );
      setMessages(conversation.messages);
      setConversations((current) =>
        current.map((item) =>
          item.conversation_id === conversation.conversation_id
            ? { ...item, updated_at: conversation.updated_at }
            : item,
        ),
      );
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    }
  }

  const latestDraftMessageId = [...messages]
    .reverse()
    .find((message) => message.draft !== null)?.message_id;
  const listingHasBeenCreated = messages.some(
    (message) => message.created_listing !== null,
  );

  return (
    <>
      {!isOpen && (
        <button
          aria-label="Open AI assistant"
          className="assistant-launcher"
          onClick={() => setIsOpen(true)}
          type="button"
        >
          <span aria-hidden="true">✦</span>
          <span>AI assistant</span>
        </button>
      )}
      {isOpen && (
        <section
          aria-label="AI assistant"
          aria-modal="false"
          className="assistant-panel"
          role="dialog"
        >
          <header className="assistant-header">
            <div>
              <p>ROOM RENTALS</p>
              <h2>{role === "tenant" ? "Find a room" : "Create a listing"}</h2>
            </div>
            <button
              aria-label="Close AI assistant"
              className="assistant-close-button"
              onClick={() => setIsOpen(false)}
              type="button"
            >
              ×
            </button>
          </header>
          <div className="assistant-body">
            <aside className="assistant-sidebar" aria-label="Assistant chats">
              <button
                className="assistant-new-chat"
                disabled={isSending}
                onClick={() => void startConversation()}
                type="button"
              >
                + New chat
              </button>
              <div className="assistant-conversation-list">
                {conversations.map((conversation) => (
                  <button
                    aria-current={
                      activeConversationId === conversation.conversation_id
                        ? "page"
                        : undefined
                    }
                    className={`assistant-conversation-item${activeConversationId === conversation.conversation_id ? " active" : ""}`}
                    key={conversation.conversation_id}
                    disabled={isSending}
                    onClick={() =>
                      selectConversation(conversation.conversation_id)
                    }
                    type="button"
                  >
                    {conversation.assistant_role === "tenant"
                      ? "Room search"
                      : "Listing draft"}
                    <time dateTime={conversation.updated_at}>
                      {new Intl.DateTimeFormat("en-ZA", {
                        dateStyle: "short",
                      }).format(new Date(conversation.updated_at))}
                    </time>
                  </button>
                ))}
              </div>
            </aside>
            <div className="assistant-chat">
              <div
                aria-live="polite"
                className="assistant-message-list"
                ref={messageListRef}
                role="log"
              >
                {messages.length === 0 && !isLoading && (
                  <div className="assistant-welcome">
                    <span aria-hidden="true">✦</span>
                    <h3>
                      {role === "tenant"
                        ? "What kind of room are you looking for?"
                        : "Let's put your room listing together."}
                    </h3>
                    <p>
                      {role === "tenant"
                        ? "Share an area, budget, room type, or amenities. Results come from published platform listings."
                        : "Tell me about the room. I’ll ask for anything missing and let you review before creating a draft."}
                    </p>
                  </div>
                )}
                {messages.map((message) => (
                  <article
                    className={`assistant-message ${message.sender_role}`}
                    key={`${message.sender_role}-${message.message_id}`}
                  >
                    <p className="assistant-message-content">{message.content}</p>
                    {message.listings.map((item) => (
                      <ListingResultCard
                        accessToken={accessToken}
                        areaName={item.area_name}
                        key={item.listing.listing_id}
                        listing={item.listing}
                        onNavigate={onNavigate}
                      />
                    ))}
                    {message.notification !== null && (
                      <div
                        className={`assistant-approval-notification${message.notification.kind === "listing_rejected" ? " rejected" : ""}`}
                      >
                        <strong>
                          {message.notification.kind === "listing_approved"
                            ? "Listing approved"
                            : "Listing not approved"}
                        </strong>
                        <p>
                          {message.notification.kind === "listing_approved"
                            ? `${message.notification.listing_title} is now live.`
                            : `${message.notification.listing_title} was returned to drafts.`}
                        </p>
                        {message.notification.kind === "listing_rejected" && (
                          <p>
                            <strong>Reason:</strong>{" "}
                            {message.notification.reason ??
                              "No reason was provided."}
                          </p>
                        )}
                        <button
                          className="assistant-inline-button"
                          onClick={() =>
                            onNavigate(
                              message.notification?.kind === "listing_approved"
                                ? `/listings/${message.notification.listing_id}`
                                : "/landlord",
                            )
                          }
                          type="button"
                        >
                          {message.notification.kind === "listing_approved"
                            ? "View approved listing"
                            : "Edit listing"}
                        </button>
                      </div>
                    )}
                    {message.draft !== null &&
                      message.message_id === latestDraftMessageId &&
                      !listingHasBeenCreated &&
                      role === "landlord" &&
                      activeConversationId !== null && (
                        <DraftSummary
                          accessToken={accessToken}
                          conversationId={activeConversationId}
                          draft={message.draft}
                          key={`draft-${message.message_id}`}
                          onConfirmed={() => void reloadActiveConversation()}
                        />
                      )}
                  </article>
                ))}
                {isLoading && (
                  <p className="assistant-loading" role="status">
                    Loading conversation…
                  </p>
                )}
                {isSending && (
                  <p className="assistant-loading" role="status">
                    Thinking…
                  </p>
                )}
              </div>
              {error !== null && (
                <p className="assistant-error assistant-panel-error" role="alert">
                  {error}
                </p>
              )}
              <form className="assistant-composer" onSubmit={sendMessage}>
                <label className="assistant-sr-only" htmlFor="assistant-message">
                  Message the assistant
                </label>
                <textarea
                  id="assistant-message"
                  maxLength={4000}
                  onChange={(event) => setMessageText(event.target.value)}
                  placeholder={
                    role === "tenant"
                      ? "Describe the room you need…"
                      : "Describe the room you want to list…"
                  }
                  rows={2}
                  value={messageText}
                />
                <button
                  aria-label="Send message"
                  disabled={isSending || messageText.trim().length === 0}
                  type="submit"
                >
                  {isSending ? "…" : "Send"}
                </button>
              </form>
            </div>
          </div>
        </section>
      )}
    </>
  );
}
