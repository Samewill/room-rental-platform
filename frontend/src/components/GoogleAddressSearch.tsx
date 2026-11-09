import { useEffect, useRef, useState } from "react";

import { loadGoogleMapsLibraries } from "../googleMaps";
import "./RoomMap.css";

export type GoogleAddressSelection = {
  placeId: string;
  address: string;
  displayAddress: string | null;
  latitude: number;
  longitude: number;
};

type GoogleAddressSearchProps = {
  value: string;
  onChange: (value: string) => void;
  onResultSelected: (result: GoogleAddressSelection) => void;
};

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Google Maps address search could not be loaded.";
}

export default function GoogleAddressSearch({
  value,
  onChange,
  onResultSelected,
}: GoogleAddressSearchProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const onChangeRef = useRef(onChange);
  const onResultSelectedRef = useRef(onResultSelected);
  const valueRef = useRef(value);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    onChangeRef.current = onChange;
    onResultSelectedRef.current = onResultSelected;
    valueRef.current = value;
  }, [onChange, onResultSelected]);

  useEffect(() => {
    let active = true;
    let autocomplete: google.maps.places.PlaceAutocompleteElement | null = null;

    async function mountAutocomplete(): Promise<void> {
      try {
        const { places } = await loadGoogleMapsLibraries();
        if (!active || containerRef.current === null) {
          return;
        }

        autocomplete = new places.PlaceAutocompleteElement({
          includedRegionCodes: ["za"],
          placeholder: "Search an address or area",
          requestedRegion: "za",
          maxlength: 200,
        });
        autocomplete.description =
          "Type an address or area and select a Google Maps suggestion.";
        autocomplete.value = value;
        autocomplete.className = "google-address-autocomplete";
        autocomplete.addEventListener("input", () => {
          onChangeRef.current(autocomplete?.value ?? "");
        });
        autocomplete.addEventListener("gmp-select", (event) => {
          void selectPlace(
            event as google.maps.places.PlacePredictionSelectEvent,
          );
        });
        containerRef.current.replaceChildren(autocomplete);
        setErrorMessage(null);
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

    async function selectPlace(
      event: google.maps.places.PlacePredictionSelectEvent,
    ): Promise<void> {
      try {
        const place = event.placePrediction.toPlace();
        await place.fetchFields({
          fields: ["id", "formattedAddress", "location"],
        });
        const location = place.location?.toJSON();
        if (
          !place.id ||
          !location ||
          !Number.isFinite(location.lat) ||
          !Number.isFinite(location.lng)
        ) {
          throw new Error("Google Maps did not return a location for this place.");
        }

        const address = valueRef.current.trim();
        if (!address) {
          throw new Error("Enter an address before selecting a Google result.");
        }
        onChangeRef.current(address);
        onResultSelectedRef.current({
          placeId: place.id,
          address,
          displayAddress: place.formattedAddress ?? null,
          latitude: location.lat,
          longitude: location.lng,
        });
      } catch (error: unknown) {
        if (active) {
          setErrorMessage(getErrorMessage(error));
        }
      }
    }

    void mountAutocomplete();
    return () => {
      active = false;
      autocomplete?.remove();
    };
  }, []);

  useEffect(() => {
    const autocomplete = containerRef.current?.firstElementChild;
    if (
      autocomplete instanceof HTMLElement &&
      "value" in autocomplete &&
      (autocomplete as google.maps.places.PlaceAutocompleteElement).value !==
        value
    ) {
      (autocomplete as google.maps.places.PlaceAutocompleteElement).value =
        value;
    }
  }, [value]);

  return (
    <div className="google-address-search">
      <div className="google-address-search-input" ref={containerRef} />
      {isLoading && <small role="status">Loading Google Maps address search…</small>}
      {errorMessage !== null && (
        <small className="address-search-error" role="alert">
          Address search is unavailable: {errorMessage}
        </small>
      )}
      {errorMessage === null && !isLoading && (
        <small className="google-address-search-hint">
          Start typing an address or area. Google Maps will show matching
          suggestions below the search; select one to position the map.
        </small>
      )}
      <small>
        Address searches are processed by Google Maps Platform.{" "}
        <a
          href="https://policies.google.com/privacy"
          rel="noreferrer"
          target="_blank"
        >
          Learn about Google’s privacy policy.
        </a>
      </small>
    </div>
  );
}
