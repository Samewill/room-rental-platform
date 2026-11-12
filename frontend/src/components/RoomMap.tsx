import { useEffect, useRef, useState } from "react";

import { getGoogleMapId, loadGoogleMapsLibraries } from "../googleMaps";
import "./RoomMap.css";

export type MapPoint = {
  latitude: number;
  longitude: number;
};

type RoomMapProps = {
  point: MapPoint | null;
  label: string;
  approximate?: boolean;
  draggable?: boolean;
  onPointChange?: (point: MapPoint) => void;
  placeId?: string | null;
};

const SOUTH_AFRICA_CENTER: google.maps.LatLngLiteral = {
  lat: -29,
  lng: 24,
};

export default function RoomMap({
  point,
  label,
  approximate = false,
  draggable = false,
  onPointChange,
  placeId = null,
}: RoomMapProps) {
  const mapElementRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<google.maps.Map | null>(null);
  const markerRef = useRef<google.maps.marker.AdvancedMarkerElement | null>(
    null,
  );
  const onPointChangeRef = useRef(onPointChange);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  onPointChangeRef.current = onPointChange;

  useEffect(() => {
    let active = true;

    async function createMap(): Promise<void> {
      try {
        const { maps, marker } = await loadGoogleMapsLibraries();
        const element = mapElementRef.current;
        if (!active || element === null) {
          return;
        }

        const map = new maps.Map(element, {
          center: SOUTH_AFRICA_CENTER,
          zoom: 5,
          mapId: getGoogleMapId(),
          gestureHandling: "greedy",
          zoomControl: true,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
        });
        mapRef.current = map;
        const pin = document.createElement("span");
        pin.setAttribute("aria-hidden", "true");
        pin.textContent = "📍";
        pin.style.fontSize = "32px";
        pin.style.lineHeight = "1";
        const mapMarker = new marker.AdvancedMarkerElement({
          map,
          title: label,
          gmpDraggable: draggable,
          content: pin,
        });
        markerRef.current = mapMarker;
        setMapReady(true);
        if (draggable) {
          mapMarker.addListener("dragend", () => {
            const position = mapMarker.position;
            if (position === null || position === undefined) {
              return;
            }

            onPointChangeRef.current?.({
              latitude:
                typeof position.lat === "function"
                  ? position.lat()
                  : position.lat,
              longitude:
                typeof position.lng === "function"
                  ? position.lng()
                  : position.lng,
            });
          });
        }
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
      setMapReady(false);
      if (markerRef.current !== null) {
        markerRef.current.map = null;
        markerRef.current = null;
      }
      mapRef.current = null;
    };
  }, [draggable, label]);

  useEffect(() => {
    let active = true;

    async function updateMapLocation(): Promise<void> {
      const map = mapRef.current;
      const marker = markerRef.current;
      if (!mapReady || map === null || marker === null) {
        return;
      }

      let location = point;
      if (location === null && placeId !== null) {
        try {
          const { places } = await loadGoogleMapsLibraries();
          const place = new places.Place({ id: placeId });
          await place.fetchFields({ fields: ["location"] });
          const coordinates = place.location?.toJSON();
          if (coordinates !== undefined) {
            location = {
              latitude: coordinates.lat,
              longitude: coordinates.lng,
            };
          }
        } catch (error: unknown) {
          if (active) {
            setMapError(
              error instanceof Error
                ? error.message
                : "The selected Google Maps location could not be loaded.",
            );
          }
          return;
        }
      }

      if (!active) {
        return;
      }
      if (location === null) {
        marker.position = null;
        map.setCenter(SOUTH_AFRICA_CENTER);
        map.setZoom(5);
        return;
      }

      const position = {
        lat: location.latitude,
        lng: location.longitude,
      };
      marker.position = position;
      marker.title = label;
      map.setCenter(position);
      map.setZoom(Math.max(map.getZoom() ?? 5, 13));
      setMapError(null);
    }

    void updateMapLocation();
    return () => {
      active = false;
    };
  }, [label, mapReady, placeId, point?.latitude, point?.longitude]);

  return (
    <section aria-label={label} className="room-map">
      {mapError !== null && (
        <p className="room-map-configuration" role="alert">
          Google Maps is unavailable: {mapError}
        </p>
      )}
      <div
        aria-label={label}
        className="room-map-canvas"
        ref={mapElementRef}
        role="application"
        tabIndex={0}
      />
      {approximate && (
        <p className="room-map-privacy-note">
          Approximate location only; the precise address is not shown on this
          public map.
        </p>
      )}
    </section>
  );
}
