import ListingDetailsPage from "./pages/ListingDetailsPage";
import ListingsPage from "./pages/ListingsPage";

export default function App() {
  const match = window.location.pathname.match(/^\/listings\/(\d+)\/?$/);
  if (match) {
    const listingId = Number(match[1]);
    if (Number.isSafeInteger(listingId) && listingId > 0) {
      return <ListingDetailsPage listingId={listingId} />;
    }
  }

  return <ListingsPage />;
}