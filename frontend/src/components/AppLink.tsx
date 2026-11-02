import type { AnchorHTMLAttributes, MouseEvent } from "react";

type AppLinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & {
  href: string;
  onNavigate: (path: string) => void;
};

export default function AppLink({
  href,
  onNavigate,
  onClick,
  ...anchorProps
}: AppLinkProps) {
  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    onClick?.(event);
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      anchorProps.target === "_blank" ||
      anchorProps.download !== undefined
    ) {
      return;
    }

    const destination = new URL(href, window.location.href);
    if (destination.origin !== window.location.origin) {
      return;
    }

    event.preventDefault();
    onNavigate(
      `${destination.pathname}${destination.search}${destination.hash}`,
    );
  }

  return (
    <a {...anchorProps} href={href} onClick={handleClick}>
      {anchorProps.children}
    </a>
  );
}
