/**
 * Type-safe API client for MIDI Agent API
 *
 * This client is automatically typed based on the FastAPI OpenAPI schema.
 * All request/response types are validated at compile time.
 */

import createClient from "openapi-fetch";
import type { paths } from "../types/api";
import { getStoredApiKey } from "./auth";

// Create the API client with automatic type inference
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8246";
console.log("API_BASE_URL", API_BASE_URL);

export const apiClient = createClient<paths>({
  baseUrl: API_BASE_URL,
});

// Add Authorization header to all requests
apiClient.use({
  onRequest({ request }) {
    const apiKey = getStoredApiKey();
    if (apiKey) {
      request.headers.set("Authorization", `Bearer ${apiKey}`);
    }
    return request;
  },
});

/**
 * Check API health status
 */
export async function checkHealth() {
  return await apiClient.GET("/health");
}

/**
 * List all songs for the current user
 *
 * Example usage:
 * ```ts
 * const result = await listSongs();
 *
 * if (result.data) {
 *   console.log(result.data); // Array of songs
 * }
 * ```
 */
export async function listSongs() {
  return await apiClient.GET("/api/midi/songs/");
}

/**
 * Create a new song with an empty track
 *
 * Example usage:
 * ```ts
 * const result = await createSong({
 *   title: "My Song",
 *   bpm: 120,
 *   key: "C"
 * });
 *
 * if (result.data) {
 *   console.log(result.data); // Song details with empty track
 * }
 * ```
 */
export async function createSong(
  request: paths["/api/midi/songs/"]["post"]["requestBody"]["content"]["application/json"]
) {
  return await apiClient.POST("/api/midi/songs/", {
    body: request,
  });
}

/**
 * Get a specific song with all track details and loops
 *
 * Example usage:
 * ```ts
 * const result = await getSong("song-id");
 *
 * if (result.data) {
 *   console.log(result.data); // Song with tracks and loops
 * }
 * ```
 */
export async function getSong(songId: string) {
  return await apiClient.GET("/api/midi/songs/{song_id}", {
    params: {
      path: {
        song_id: songId,
      },
    },
  });
}

/**
 * Create a new loop for a track
 *
 * Example usage:
 * ```ts
 * const result = await createLoop({
 *   track_id: "track-uuid",
 *   measures: 4,
 *   repeat: 1
 * });
 *
 * if (result.data) {
 *   console.log(result.data); // Loop details with empty chat history
 * }
 * ```
 */
export async function createLoop(
  request: paths["/api/midi/loops/"]["post"]["requestBody"]["content"]["application/json"]
) {
  return await apiClient.POST("/api/midi/loops/", {
    body: request,
  });
}

/**
 * Append a chat message to a loop and trigger inference
 *
 * Example usage:
 * ```ts
 * const result = await appendLoopChat({
 *   loop_id: "loop-uuid",
 *   msg: "Create a funky bassline",
 *   measures: 4
 * });
 *
 * if (result.data) {
 *   console.log(result.data); // LoopDetailResponse with updated chat history
 * }
 * ```
 */
export async function appendLoopChat(
  request: paths["/api/midi/loops/{loop_id}/chats"]["post"]["requestBody"]["content"]["application/json"]
) {
  return await apiClient.POST("/api/midi/loops/{loop_id}/chats", {
    body: request,
  });
}

/**
 * Get a specific loop with full details including chat history
 *
 * Example usage:
 * ```ts
 * const result = await getLoop("loop-uuid");
 *
 * if (result.data) {
 *   console.log(result.data); // LoopDetailResponse with chats
 * }
 * ```
 */
export async function getLoop(loopId: string) {
  return await apiClient.GET("/api/midi/loops/{loop_id}", {
    params: {
      path: {
        loop_id: loopId,
      },
    },
  });
}

/**
 * Delete a loop and all associated chat messages
 *
 * Example usage:
 * ```ts
 * const result = await deleteLoop("loop-uuid");
 *
 * if (result.data) {
 *   console.log("Loop deleted successfully");
 * }
 * ```
 */
export async function deleteLoop(loopId: string) {
  return await apiClient.DELETE("/api/midi/loops/{loop_id}", {
    params: {
      path: {
        loop_id: loopId,
      },
    },
  });
}

/**
 * Download a loop as a WAV file
 *
 * This function triggers a browser download of the loop rendered to audio.
 *
 * Example usage:
 * ```ts
 * await downloadLoopWav("loop-uuid");
 * ```
 */
export async function downloadLoopWav(loopId: string): Promise<void> {
  const url = `${API_BASE_URL}/api/midi/loops/${loopId}/download`;

  try {
    // Make authenticated fetch request
    const apiKey = getStoredApiKey();
    const response = await fetch(url, {
      headers: {
        Authorization: apiKey ? `Bearer ${apiKey}` : "",
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to download: ${response.statusText}`);
    }

    // Get the blob from the response
    const blob = await response.blob();

    // Create a download link and trigger it
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `loop_${loopId.substring(0, 8)}.wav`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Clean up the object URL
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error("Failed to download loop:", error);
    throw error;
  }
}

/**
 * Update a loop's offset, repeat, or track_id
 *
 * Example usage:
 * ```ts
 * const result = await updateLoop("loop-uuid", {
 *   offset: 4,
 *   repeat: 2
 * });
 *
 * if (result.data) {
 *   console.log(result.data); // Updated loop details
 * }
 * ```
 */
export async function updateLoop(
  loopId: string,
  request: { offset?: number; extend_measures?: number; track_id?: string }
) {
  return await apiClient.PATCH("/api/midi/loops/{loop_id}", {
    params: {
      path: {
        loop_id: loopId,
      },
    },
    body: request,
  });
}

/**
 * Create a new track for a song
 *
 * Example usage:
 * ```ts
 * const result = await createTrack({
 *   song_id: "song-uuid",
 *   title: "Track 1"
 * });
 *
 * if (result.data) {
 *   console.log(result.data); // Track details
 * }
 * ```
 */
export async function createTrack(request: { song_id: string; title: string }) {
  return await apiClient.POST("/api/midi/tracks/", {
    body: request,
  });
}

/**
 * Update a track's title, MIDI channel, instrument, and/or color
 *
 * Example usage:
 * ```ts
 * const result = await updateTrack("track-uuid", {
 *   title: "Updated Track Name",
 *   midi_channel: 2,
 *   instrument: "bass",
 *   color: "success"
 * });
 *
 * if (result.data) {
 *   console.log(result.data); // Updated track details
 * }
 * ```
 */
export async function updateTrack(
  trackId: string,
  request: paths["/api/midi/tracks/{track_id}"]["patch"]["requestBody"]["content"]["application/json"]
) {
  return await apiClient.PATCH("/api/midi/tracks/{track_id}", {
    params: {
      path: {
        track_id: trackId,
      },
    },
    body: request,
  });
}

/**
 * Delete a track and all associated loops
 *
 * Example usage:
 * ```ts
 * const result = await deleteTrack("track-uuid");
 *
 * if (!result.error) {
 *   console.log("Track deleted successfully");
 * }
 * ```
 */
export async function deleteTrack(trackId: string) {
  return await apiClient.DELETE("/api/midi/tracks/{track_id}", {
    params: {
      path: {
        track_id: trackId,
      },
    },
  });
}

/**
 * List all available instruments and their samples
 *
 * Example usage:
 * ```ts
 * const result = await listInstruments();
 *
 * if (result.data) {
 *   console.log(result.data.instruments); // Array of instruments with samples
 * }
 * ```
 */
export async function listInstruments() {
  return await apiClient.GET("/api/midi/instruments");
}
