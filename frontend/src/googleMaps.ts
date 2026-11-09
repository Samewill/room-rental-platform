import { importLibrary, setOptions } from "@googlemaps/js-api-loader";

let optionsConfigured = false;
let librariesPromise: Promise<{
  maps: google.maps.MapsLibrary;
  marker: google.maps.MarkerLibrary;
  places: google.maps.PlacesLibrary;
}> | null = null;

export function getGoogleMapsApiKey(): string {
  return import.meta.env.VITE_GOOGLE_MAPS_API_KEY?.trim() ?? "";
}

export function getGoogleMapId(): string {
  return import.meta.env.VITE_GOOGLE_MAP_ID?.trim() || "DEMO_MAP_ID";
}

export function loadGoogleMapsLibraries(): Promise<{
  maps: google.maps.MapsLibrary;
  marker: google.maps.MarkerLibrary;
  places: google.maps.PlacesLibrary;
}> {
  const key = getGoogleMapsApiKey();
  if (!key) {
    return Promise.reject(
      new Error("Configure VITE_GOOGLE_MAPS_API_KEY to enable Google Maps."),
    );
  }

  if (!optionsConfigured) {
    setOptions({ key, v: "weekly" });
    optionsConfigured = true;
  }

  if (librariesPromise === null) {
    librariesPromise = Promise.all([
      importLibrary("maps") as Promise<google.maps.MapsLibrary>,
      importLibrary("marker") as Promise<google.maps.MarkerLibrary>,
      importLibrary("places") as Promise<google.maps.PlacesLibrary>,
    ])
      .then(([maps, marker, places]) => ({ maps, marker, places }))
      .catch((error: unknown) => {
        librariesPromise = null;
        throw error;
      });
  }
  return librariesPromise;
}
