import { useEffect, useRef, useState } from "react";

import { getGoogleMapId, loadGoogleMapsLibraries } from "../googleMaps";
import "./ListingResultsMap.css";

export type ListingMapPoint = {
  listingId: number;
  title: string;
  monthlyRent: string | number;
  latitude: number;
  longitude: number;
};

type SearchCenter = {
  latitude: number;
  longitude: number;
};

type ListingResultsMapProps = {
  listings: ListingMapPoint[];
  onNavigate: (path: string) => void;
  radius: 5 | 10;
  searchCenter: SearchCenter | null;
};

const SOUTH_AFRICA_CENTER: google.maps.LatLngLiteral = {
  lat: -29,
  lng: 24,
};

function formatRent(value: string | number): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) {
    return "Rent unavailable";
  }

  return new Intl.NumberFormat("en-ZA", {
    style: "currency",
    currency: "ZAR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function ListingResultsMap({
  listings,
  onNavigate,
  radius,
  searchCenter,
}: ListingResultsMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const markerLibraryRef = useRef<google.maps.MarkerLibrary | null>(null);
  const markersRef = useRef<google.maps.marker.AdvancedMarkerElement[]>([]);
  const infoWindowRef = useRef<google.maps.InfoWindow | null>(null);
  const radiusCircleRef = useRef<google.maps.Circle | null>(null);
  const onNavigateRef = useRef(onNavigate);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  onNavigateRef.current = onNavigate;

  useEffect(() => {
    let active = true;

    async function createMap(): Promise<void> {
      try {
        const { maps, marker } = await loadGoogleMapsLibraries();
        const element = containerRef.current;
        if (!active || element === null) {
          return;
        }

        mapRef.current = new maps.Map(element, {
          center: SOUTH_AFRICA_CENTER,
          zoom: 5,
          mapId: getGoogleMapId(),
          gestureHandling: "greedy",
          zoomControl: true,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
        });
        markerLibraryRef.current = marker;
        infoWindowRef.current = new maps.InfoWindow();
        setMapError(null);
        setMapReady(true);
      } catch (error: unknown) {
        if (active) {
          setMapError(
            error instanceof Error
              ? error.message
              : "Google Maps could not be loaded.",
          );
        }
      }
    }

    void createMap();
    return () => {
      active = false;
      for (const mapMarker of markersRef.current) {
        mapMarker.map = null;
      }
      markersRef.current = [];
      infoWindowRef.current?.close();
      infoWindowRef.current = null;
      radiusCircleRef.current?.setMap(null);
      radiusCircleRef.current = null;
      markerLibraryRef.current = null;
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const markerLibrary = markerLibraryRef.current;
    if (!mapReady || map === null || markerLibrary === null) {
      return;
    }

    for (const mapMarker of markersRef.current) {
      mapMarker.map = null;
    }
    markersRef.current = [];
    infoWindowRef.current?.close();
    radiusCircleRef.current?.setMap(null);
    radiusCircleRef.current = null;

    const bounds = new google.maps.LatLngBounds();
    for (const listing of listings) {
      const position = {
        lat: listing.latitude,
        lng: listing.longitude,
      };
      const markerContent = document.createElement("div");
      markerContent.className = "listing-results-map-marker";
      markerContent.textContent = formatRent(listing.monthlyRent);

      const mapMarker = new markerLibrary.AdvancedMarkerElement({
        map,
        position,
        title: listing.title,
        content: markerContent,
      });
      mapMarker.addListener("click", () => {
        const content = document.createElement("div");
        content.className = "listing-results-map-info";

        const title = document.createElement("strong");
        title.textContent = listing.title;
        content.append(title);

        const rent = document.createElement("p");
        rent.textContent = `${formatRent(listing.monthlyRent)} / month`;
        content.append(rent);

        const link = document.createElement("a");
        const path = `/listings/${listing.listingId}`;
        link.href = path;
        link.textContent = "View details";
        link.addEventListener("click", (event) => {
          event.preventDefault();
          onNavigateRef.current(path);
        });
        content.append(link);

        infoWindowRef.current?.setContent(content);
        infoWindowRef.current?.open({ map, anchor: mapMarker });
      });
      markersRef.current.push(mapMarker);
      bounds.extend(position);
    }

    if (searchCenter !== null) {
      const center = {
        lat: searchCenter.latitude,
        lng: searchCenter.longitude,
      };
      radiusCircleRef.current = new google.maps.Circle({
        map,
        center,
        radius: radius * 1000,
        fillColor: "#244b35",
        fillOpacity: 0.08,
        strokeColor: "#244b35",
        strokeOpacity: 0.65,
        strokeWeight: 1,
        clickable: false,
      });
      map.setCenter(center);
      map.setZoom(radius === 5 ? 12 : 11);
    } else if (listings.length === 1) {
      map.setCenter({
        lat: listings[0].latitude,
        lng: listings[0].longitude,
      });
      map.setZoom(13);
    } else if (listings.length > 1) {
      map.fitBounds(bounds, 32);
    } else {
      map.setCenter(SOUTH_AFRICA_CENTER);
      map.setZoom(5);
    }
  }, [listings, mapReady, radius, searchCenter]);

  return (
    <section aria-label="Map of matching rooms" className="listing-results-map">
      {mapError !== null && (
        <p className="listing-results-map-error" role="alert">
          The results map is unavailable: {mapError}
        </p>
      )}
      <div
        aria-label="Matching room locations"
        className="listing-results-map-canvas"
        ref={containerRef}
        role="application"
        tabIndex={0}
      />
      <p className="listing-results-map-note">
        Pins show approximate public locations. Select a pin for listing
        details.
      </p>
    </section>
  );
}
