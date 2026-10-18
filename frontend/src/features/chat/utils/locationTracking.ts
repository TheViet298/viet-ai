import { calculateHaversineDistanceKm } from "./distance";

export function shouldSyncLocation(previous: { lat: number; lng: number; time: number } | null, current: { lat: number; lng: number }, now: number): boolean {
  return !previous || calculateHaversineDistanceKm(previous, current) >= 0.15 || now - previous.time >= 30000;
}

export function startLocationWatch(
  geolocation: Pick<Geolocation, "watchPosition" | "clearWatch">,
  onPosition: (position: GeolocationPosition) => void,
  onError: (error: GeolocationPositionError) => void,
): () => void {
  let active = true;
  const watchId = geolocation.watchPosition(
    (position) => { if (active) onPosition(position); },
    (error) => { if (active) onError(error); },
    { timeout: 8000, enableHighAccuracy: true, maximumAge: 5000 },
  );
  return () => { if (active) { active = false; geolocation.clearWatch(watchId); } };
}
