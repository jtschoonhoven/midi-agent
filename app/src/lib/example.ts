/**
 * Example usage of the type-safe API client
 *
 * This file demonstrates how to use the generated types
 * with full autocomplete and type checking.
 */

import { createSong, createLoop, appendLoopChat, checkHealth } from "./api";

// Example: Create a song and loop with full type safety
export async function exampleCreateSongAndLoop() {
  // Create a new song
  const songResult = await createSong({
    title: "My Song",
    bpm: 120, // TypeScript enforces 30-360 range
    key: "C", // TypeScript will autocomplete valid keys!
    time_signature: "4/4", // TypeScript will autocomplete valid time signatures!
  });

  // Response is fully typed
  if (songResult.data) {
    console.log("Song created:", songResult.data.title);
    console.log("Key:", songResult.data.key); // Autocomplete works!
    console.log("BPM:", songResult.data.bpm);

    // Get the first track (created automatically)
    const firstTrack = songResult.data.tracks[0];

    // Create a loop for the track
    const loopResult = await createLoop({
      track_id: firstTrack.id,
      measures: 4, // TypeScript enforces 1-32 range
      extend_measures: 0, // Optional, defaults to 0
    });

    if (loopResult.data) {
      console.log("Loop created with", loopResult.data.measures, "measures");

      // Add a chat message to generate MIDI
      const chatResult = await appendLoopChat(loopResult.data.id, {
        msg: "Create a cheerful melody in C major",
        measures: 4,
      });

      if (chatResult.data) {
        console.log("MIDI Events:", chatResult.data.midi_events);
        console.log("Chat history:", chatResult.data.chats);
      }
    }
  }

  // Errors are also typed
  if (songResult.error) {
    console.error("API Error:", songResult.error);
  }
}

// Example: Health check
export async function exampleHealthCheck() {
  const result = await checkHealth();

  if (result.data) {
    console.log("Health status:", result.data.status);
  }
}

// TypeScript will catch errors at compile time:
//
// ❌ This won't compile (invalid key):
// createSong({ key: "H" })  // Error: Type '"H"' is not assignable to Key
//
// ❌ This won't compile (invalid time signature):
// createSong({ time_signature: "5/8" })  // Error: Type '"5/8"' is not assignable
//
// ❌ This won't compile (BPM out of range):
// createSong({ bpm: 500 })  // Error: Number 500 exceeds constraint
//
// ❌ This won't compile (missing required field):
// createSong({ title: "test" })  // Error: bpm, key, time_signature are required
