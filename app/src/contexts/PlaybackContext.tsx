import { createContext, useContext, useState, useEffect, useRef, useCallback, type ReactNode } from "react";
import { listInstruments } from "../lib/api";

// Dynamic import to avoid initializing AudioContext on page load
let Tone: typeof import("tone") | null = null;
async function getTone() {
  if (!Tone) {
    Tone = await import("tone");
  }
  return Tone;
}

// API base URL for loading samples
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8246";

interface MidiEvent {
  measure: number;
  beat: number;
  beat_div4: number;
  beat_div16: number;
  event: string;
  value: number;
  chord?: string;
}

interface Loop {
  id: string;
  offset: number;
  measures: number;
  extend_measures: number;
  midi_events: MidiEvent[];
  track_id: string;
}

interface Track {
  id: string;
  midi_channel: number;
  instrument: "piano" | "bass" | "drum";
  loops: Loop[];
}

interface SongData {
  tracks: Track[];
  bpm: number;
  time_signature: string;
}

interface MidiOutput {
  id: string;
  name: string;
  type: "browser" | "device";
}

interface PlaybackContextType {
  isPlaying: boolean;
  bpm: number;
  currentBeat: number;
  play: () => void;
  pause: () => void;
  stop: () => void;
  togglePlayPause: () => void;
  playFromBeat: (beat: number) => Promise<void>;
  setBpm: (bpm: number) => void;
  loadSong: (songData: SongData | null) => void;
  midiOutputs: MidiOutput[];
  selectedMidiOutput: MidiOutput;
  setSelectedMidiOutput: (output: MidiOutput) => void;
  requestMidiAccess: () => Promise<void>;
  hasMidiAccess: boolean;
  setLoopZone: (startBeat: number | null, endBeat: number | null) => void;
  mutedTracks: Set<string>;
  soloedTracks: Set<string>;
  toggleMute: (trackId: string) => void;
  toggleSolo: (trackId: string) => void;
}

const PlaybackContext = createContext<PlaybackContextType | undefined>(undefined);

const BROWSER_AUDIO_OUTPUT: MidiOutput = {
  id: "browser-audio",
  name: "Browser Audio",
  type: "browser",
};

export function PlaybackProvider({ children }: { children: ReactNode }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [bpm, setBpmState] = useState(120);
  const [songData, setSongData] = useState<SongData | null>(null);
  const [currentBeat, setCurrentBeat] = useState<number>(-1);
  const [loopZoneStart, setLoopZoneStartState] = useState<number | null>(null);
  const [loopZoneEnd, setLoopZoneEndState] = useState<number | null>(null);
  const synthsRef = useRef<Map<number, any>>(new Map());
  const synthsLoadedRef = useRef<Set<number>>(new Set());
  const synthsInstrumentRef = useRef<Map<number, "piano" | "bass" | "drum">>(new Map());
  const [midiOutputs, setMidiOutputs] = useState<MidiOutput[]>([BROWSER_AUDIO_OUTPUT]);
  const [selectedMidiOutput, setSelectedMidiOutput] = useState<MidiOutput>(BROWSER_AUDIO_OUTPUT);
  const [hasMidiAccess, setHasMidiAccess] = useState(false);
  const midiAccessRef = useRef<MIDIAccess | null>(null);
  const audioContextStartedRef = useRef<boolean>(false);
  const [mutedTracks, setMutedTracks] = useState<Set<string>>(new Set());
  const [soloedTracks, setSoloedTracks] = useState<Set<string>>(new Set());
  const mutedTracksRef = useRef<Set<string>>(new Set());
  const soloedTracksRef = useRef<Set<string>>(new Set());

  // Store all instruments and samples from backend
  type Instrument = {
    id: string;
    title: string;
    type: "piano" | "bass" | "drum";
    license_type: string;
    license_uri: string;
    samples: Array<{ id: string; uri: string; midi_event: string }>;
  };
  const [instruments, setInstruments] = useState<Instrument[]>([]);

  // Playback state
  const animationFrameRef = useRef<number | null>(null);
  const currentBeatRef = useRef<number>(-1);
  const isPlayingRef = useRef<boolean>(false);
  const bpmRef = useRef<number>(bpm);
  const loopZoneStartRef = useRef<number | null>(null);
  const loopZoneEndRef = useRef<number | null>(null);

  // Keep refs in sync with state
  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  useEffect(() => {
    bpmRef.current = bpm;
  }, [bpm]);

  useEffect(() => {
    loopZoneStartRef.current = loopZoneStart;
  }, [loopZoneStart]);

  useEffect(() => {
    loopZoneEndRef.current = loopZoneEnd;
  }, [loopZoneEnd]);

  useEffect(() => {
    mutedTracksRef.current = mutedTracks;
  }, [mutedTracks]);

  useEffect(() => {
    soloedTracksRef.current = soloedTracks;
  }, [soloedTracks]);

  const toggleMute = useCallback((trackId: string) => {
    setMutedTracks((prev) => {
      const next = new Set(prev);
      if (next.has(trackId)) {
        next.delete(trackId);
      } else {
        next.add(trackId);
      }
      return next;
    });
  }, []);

  const toggleSolo = useCallback((trackId: string) => {
    setSoloedTracks((prev) => {
      const next = new Set(prev);
      if (next.has(trackId)) {
        next.delete(trackId);
      } else {
        next.add(trackId);
      }
      return next;
    });
  }, []);

  // Get beats per measure from time signature string (e.g., "4/4" -> 4, "3/4" -> 3, "6/8" -> 6)
  const getBeatsPerMeasure = (timeSignature?: string): number => {
    if (!timeSignature) return 4;
    const [numerator] = timeSignature.split("/").map(Number);
    return numerator || 4;
  };

  /**
   * Send MIDI events to the selected MIDI output.
   * @param channel - The MIDI channel to send the events to.
   * @param events - The MIDI events to send.
   */
  const sendMidiEvents = useCallback(
    async (channel: number, events: MidiEvent[]) => {
      if (selectedMidiOutput.type === "browser") {
        // Don't send events if audio context hasn't been started yet
        if (!audioContextStartedRef.current || !Tone) return;

        const instrument = synthsRef.current.get(channel);
        if (!instrument) return;

        const now = Tone!.now();

        // Check if it's a Players instance (for drums) or Sampler (for melodic instruments)
        const isPlayers = "player" in instrument;

        events.forEach((event) => {
          const eventName = event.event;

          // Check if it's a valid event (not a CC event like "Sustain")
          if (eventName && typeof eventName === "string") {
            if (isPlayers) {
              // For drum Players: just trigger the sample on note on events
              if (event.value > 0) {
                try {
                  instrument.player(eventName).start(now);
                } catch (error) {
                  console.warn(`Failed to play drum sample ${eventName}:`, error);
                }
              }
              // Note: Players don't support note off, samples play to completion
            } else {
              // For melodic Sampler: use triggerAttack/triggerRelease
              const velocity = event.value / 100; // Normalize velocity to 0-1

              if (event.value > 0) {
                // Note on
                instrument.triggerAttack(eventName, now, velocity);
              } else {
                // Note off
                instrument.triggerRelease(eventName, now);
              }
            }
          }
        });
      } else {
        // Send to real MIDI device
        const midiAccess = midiAccessRef.current;
        if (!midiAccess) return;

        // Get Tone for frequency conversion
        const tone = await getTone();

        // Find the matching MIDI output
        midiAccess.outputs.forEach((output) => {
          const outputId = output.id || output.name || "unknown";
          if (outputId === selectedMidiOutput.id) {
            events.forEach((event) => {
              const note = tone.Frequency(event.event).toMidi();
              const velocity = Math.floor(event.value * 1.27);

              // Use Note Off (0x80) for note-off events, Note On (0x90) for note-on events
              const statusByte = event.value > 0 ? 0x90 + (channel - 1) : 0x80 + (channel - 1);

              output.send([statusByte, note, velocity]);
            });
          }
        });
      }
    },
    [selectedMidiOutput]
  );

  // Playback loop using requestAnimationFrame
  const playbackLoop = useCallback(() => {
    if (!isPlayingRef.current || !songData) return;

    // Capture songData in closure so TypeScript knows it's not null
    const currentSongData = songData;
    const beatsPerMeasure = getBeatsPerMeasure(currentSongData.time_signature);

    let prevTimeMs = performance.now();

    function frame() {
      // Stop if playback was paused/stopped or songData is gone
      // Use ref to check current value, not stale closure value
      if (!isPlayingRef.current || !currentSongData) {
        animationFrameRef.current = null;
        return;
      }

      const curTimeMs = performance.now();

      // Recalculate each frame in case the BPM has changed
      // Use ref to get current BPM value, not stale closure value
      const beatsPerMs = bpmRef.current / 60 / 1000;

      // How much time has elapsed since the last frame in ms
      const timeDeltaMs = curTimeMs - prevTimeMs;

      // How many (fractional) beats have elapsed since the last frame
      const beatDelta = timeDeltaMs * beatsPerMs;
      let prevBeat = currentBeatRef.current;
      let curBeat = Math.max(0, prevBeat) + beatDelta;

      // Check if loop zone is active and handle looping
      const loopStart = loopZoneStartRef.current;
      const loopEnd = loopZoneEndRef.current;
      if (loopStart !== null && loopEnd !== null && loopEnd > loopStart) {
        // If we've gone past the loop end, jump back to loop start
        if (curBeat >= loopEnd) {
          curBeat = loopStart;
          // Adjust prevBeat so events at the loop start will fire
          prevBeat = loopStart - 0.01;
        }
      }

      currentBeatRef.current = curBeat;
      setCurrentBeat(curBeat);

      // Collect events that should fire in this frame
      const eventsToSend: Array<{ channel: number; event: MidiEvent }> = [];

      currentSongData.tracks.forEach((track) => {
        // Skip muted tracks, and skip non-soloed tracks when any track is soloed
        const muted = mutedTracksRef.current;
        const soloed = soloedTracksRef.current;
        if (muted.has(track.id)) return;
        if (soloed.size > 0 && !soloed.has(track.id)) return;

        track.loops.forEach((loop) => {
          const loopStartBeat = loop.offset * beatsPerMeasure;
          const totalMeasures = loop.measures + loop.extend_measures;
          const loopEndBeat = loopStartBeat + totalMeasures * beatsPerMeasure;

          if (curBeat >= loopStartBeat && curBeat < loopEndBeat) {
            loop.midi_events.forEach((event) => {
              // Calculate the beat position of this event within the ORIGINAL loop (0-based from loop start)
              const eventBeatInOriginalLoop =
                (event.measure - 1) * beatsPerMeasure +
                (event.beat - 1) +
                (event.beat_div4 - 1) / 4 +
                (event.beat_div16 - 1) / 16;

              const originalLoopBeats = loop.measures * beatsPerMeasure;

              if (loop.extend_measures >= 0) {
                // Positive or zero: event repeats every originalLoopBeats
                const totalBeats = totalMeasures * beatsPerMeasure;

                // Check each repetition of the event within the extended loop
                for (let repetition = 0; repetition * originalLoopBeats < totalBeats; repetition++) {
                  const eventAbsoluteBeat = loopStartBeat + repetition * originalLoopBeats + eventBeatInOriginalLoop;

                  if (eventAbsoluteBeat > prevBeat && eventAbsoluteBeat <= curBeat) {
                    eventsToSend.push({ channel: track.midi_channel, event });
                  }
                }
              } else {
                // Negative: only play events that fall within the truncated range
                if (eventBeatInOriginalLoop < totalMeasures * beatsPerMeasure) {
                  const eventAbsoluteBeat = loopStartBeat + eventBeatInOriginalLoop;

                  if (eventAbsoluteBeat > prevBeat && eventAbsoluteBeat <= curBeat) {
                    eventsToSend.push({ channel: track.midi_channel, event });
                  }
                }
              }
            });
          }
        });
      });

      // Send all events (fire and forget - we don't want to block the frame)
      eventsToSend.forEach(({ channel, event }) => {
        sendMidiEvents(channel, [event]).catch((error) => {
          console.error("Error sending MIDI event:", error);
        });
      });

      prevTimeMs = curTimeMs;

      const frameId = requestAnimationFrame(frame);
      animationFrameRef.current = frameId;
    }

    const frameId = requestAnimationFrame(frame);
    animationFrameRef.current = frameId;
  }, [songData, sendMidiEvents]); // Removed isPlaying and bpm - they're checked via refs/closure

  // Start/stop playback loop when isPlaying changes
  useEffect(() => {
    if (isPlaying) {
      playbackLoop();
    } else {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    }

    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };
  }, [isPlaying, playbackLoop]);

  // Helper function to ensure synths are created for browser audio
  const ensureSynthsCreated = useCallback(async () => {
    if (!songData || selectedMidiOutput.type !== "browser" || !audioContextStartedRef.current || !Tone) {
      return;
    }

    // Wait for instruments to be loaded
    if (instruments.length === 0) {
      console.warn("Instruments not loaded yet");
      return;
    }

    const loadPromises: Promise<void>[] = [];

    songData.tracks.forEach((track) => {
      const channel = track.midi_channel;
      const instrumentType = track.instrument;

      // Check if instrument type has changed for this channel
      const existingInstrumentType = synthsInstrumentRef.current.get(channel);
      if (existingInstrumentType && existingInstrumentType !== instrumentType) {
        console.log(
          `Instrument changed from ${existingInstrumentType} to ${instrumentType} on channel ${channel}, recreating...`
        );
        // Dispose old sampler/player
        const oldInstrument = synthsRef.current.get(channel);
        if (oldInstrument && oldInstrument.dispose) {
          oldInstrument.dispose();
        }
        // Clear from cache
        synthsRef.current.delete(channel);
        synthsLoadedRef.current.delete(channel);
        synthsInstrumentRef.current.delete(channel);
      }

      // If sampler doesn't exist, create it
      if (!synthsRef.current.has(channel)) {
        // Find the instrument for this track
        const instrument = instruments.find((inst) => inst.type === instrumentType);
        if (!instrument) {
          console.error(`No ${instrumentType} instrument found`);
          return;
        }

        // Build sample map from instrument samples
        // Format: { "C3": "http://localhost:8246/public/instruments/piano/C3.wav", ... }
        const sampleMap: Record<string, string> = {};
        instrument.samples.forEach((sample) => {
          // midi_event is already the note name (e.g., "C3", "A4")
          // uri is the relative path (e.g., "public/instruments/piano/C3.wav")
          sampleMap[sample.midi_event] = `${API_BASE_URL}/${sample.uri}`;
        });

        console.log(`${instrumentType} sampler using ${Object.keys(sampleMap).length} samples for channel ${channel}`);

        const loadPromise = new Promise<void>((resolve, reject) => {
          // Use Players for drums (arbitrary key names), Sampler for melodic instruments
          if (instrumentType === "drum") {
            const players = new Tone!.Players({
              urls: sampleMap,
              onload: () => {
                console.log(`${instrumentType} players loaded for MIDI channel ${channel}`);
                synthsLoadedRef.current.add(channel);
                synthsInstrumentRef.current.set(channel, instrumentType);
                resolve();
              },
              onerror: (error) => {
                console.error(`Failed to load ${instrumentType} players for MIDI channel ${channel}:`, error);
                reject(error);
              },
            }).toDestination();

            synthsRef.current.set(channel, players);
            console.log(`Created ${instrumentType} players for MIDI channel ${channel}`);
          } else {
            const sampler = new Tone!.Sampler({
              urls: sampleMap,
              release: 1,
              onload: () => {
                console.log(`${instrumentType} sampler loaded for MIDI channel ${channel}`);
                synthsLoadedRef.current.add(channel);
                synthsInstrumentRef.current.set(channel, instrumentType);
                resolve();
              },
              onerror: (error) => {
                console.error(`Failed to load ${instrumentType} sampler for MIDI channel ${channel}:`, error);
                reject(error);
              },
            }).toDestination();

            synthsRef.current.set(channel, sampler);
            console.log(`Created ${instrumentType} sampler for MIDI channel ${channel}`);
          }
        });

        loadPromises.push(loadPromise);
      }
      // If sampler exists but hasn't loaded yet, wait for it
      else if (!synthsLoadedRef.current.has(channel)) {
        const sampler = synthsRef.current.get(channel);
        if (sampler && !sampler.loaded) {
          console.log(`Waiting for existing sampler on channel ${channel} to finish loading...`);
          const waitPromise = new Promise<void>((resolve) => {
            const checkLoaded = () => {
              if (sampler.loaded) {
                synthsLoadedRef.current.add(channel);
                console.log(`Sampler on channel ${channel} is now loaded`);
                resolve();
              } else {
                setTimeout(checkLoaded, 100);
              }
            };
            checkLoaded();
          });
          loadPromises.push(waitPromise);
        }
      }
    });

    // Wait for all samplers to finish loading
    if (loadPromises.length > 0) {
      console.log(`Waiting for ${loadPromises.length} samplers to load...`);
      try {
        await Promise.all(loadPromises);
        console.log("All samplers loaded successfully");
      } catch (error) {
        console.error("Failed to load samplers:", error);
        throw error;
      }
    }
  }, [songData, selectedMidiOutput, instruments]);

  // Scan for MIDI devices when MIDI access is granted
  const scanMidiDevices = useCallback((midiAccess: MIDIAccess) => {
    const devices: MidiOutput[] = [BROWSER_AUDIO_OUTPUT];

    midiAccess.outputs.forEach((output) => {
      if (output.state === "connected") {
        devices.push({
          id: output.id || output.name || "unknown",
          name: output.name || "Unnamed MIDI Device",
          type: "device",
        });
      }
    });

    setMidiOutputs(devices);
    console.log(`Found ${devices.length - 1} MIDI output devices`);
  }, []);

  // Request MIDI access
  const requestMidiAccess = useCallback(async () => {
    if (!navigator.requestMIDIAccess) {
      alert("Web MIDI API is not supported in this browser. Please use Chrome, Edge, or Opera.");
      return;
    }

    try {
      const midiAccess = await navigator.requestMIDIAccess();
      midiAccessRef.current = midiAccess;
      setHasMidiAccess(true);
      scanMidiDevices(midiAccess);

      // Listen for device connection/disconnection
      midiAccess.onstatechange = () => {
        scanMidiDevices(midiAccess);
      };

      console.log("MIDI access granted");
    } catch (error) {
      console.error("Failed to get MIDI access:", error);
      alert("Failed to get MIDI access. Please check your browser permissions.");
    }
  }, [scanMidiDevices]);

  // Fetch all instruments and samples on mount
  useEffect(() => {
    const fetchInstruments = async () => {
      try {
        const result = await listInstruments();

        if (result.data) {
          setInstruments(result.data.instruments);
          console.log(`Loaded ${result.data.instruments.length} instruments`);
        }
      } catch (error) {
        console.error("Failed to fetch instruments:", error);
      }
    };

    fetchInstruments();
  }, []);

  const play = async () => {
    // Start the audio context if using browser audio
    // Note: Tone.start() is idempotent and safe to call multiple times
    if (selectedMidiOutput.type === "browser") {
      const tone = await getTone();
      await tone.start();
      audioContextStartedRef.current = true;
    }

    // Create synths after audio context is started (requires user gesture)
    await ensureSynthsCreated();

    // Resume from current position (or start from beginning if at -1)
    setIsPlaying(true);
  };

  const pause = () => {
    setIsPlaying(false);
  };

  const stop = () => {
    setIsPlaying(false);
    currentBeatRef.current = -1;
    setCurrentBeat(-1);
  };

  const togglePlayPause = async () => {
    if (isPlaying) {
      pause();
    } else {
      // If at the end or not started, reset to beginning
      if (currentBeatRef.current < 0) {
        currentBeatRef.current = -1;
        setCurrentBeat(-1);
      }
      await play();
    }
  };

  const playFromBeat = async (beat: number) => {
    // Set to specific beat position FIRST (subtract small amount to catch events at this beat)
    currentBeatRef.current = beat - 0.01;
    setCurrentBeat(beat - 0.01);

    // Start the audio context if using browser audio
    if (selectedMidiOutput.type === "browser") {
      const tone = await getTone();
      await tone.start();
      audioContextStartedRef.current = true;
    }

    // Create synths after audio context is started (requires user gesture)
    await ensureSynthsCreated();

    setIsPlaying(true);
  };

  const setBpm = (newBpm: number) => {
    setBpmState(newBpm);
  };

  const loadSong = useCallback((newSongData: SongData | null) => {
    // Stop playback only if song data is cleared
    if (!newSongData && isPlayingRef.current) {
      setIsPlaying(false);
    }

    // Only reset beat position if we're actually changing the song
    // (not just reloading the same song data)
    currentBeatRef.current = -1;
    setCurrentBeat(-1);
    setSongData(newSongData);

    // Update BPM from song data if provided
    if (newSongData) {
      setBpmState(newSongData.bpm);
    }
  }, []);

  const setLoopZone = (startBeat: number | null, endBeat: number | null) => {
    setLoopZoneStartState(startBeat);
    setLoopZoneEndState(endBeat);
  };

  return (
    <PlaybackContext.Provider
      value={{
        isPlaying,
        bpm,
        currentBeat,
        play,
        pause,
        stop,
        togglePlayPause,
        playFromBeat,
        setBpm,
        loadSong,
        midiOutputs,
        selectedMidiOutput,
        setSelectedMidiOutput,
        requestMidiAccess,
        hasMidiAccess,
        setLoopZone,
        mutedTracks,
        soloedTracks,
        toggleMute,
        toggleSolo,
      }}
    >
      {children}
    </PlaybackContext.Provider>
  );
}

export function usePlayback() {
  const context = useContext(PlaybackContext);
  if (context === undefined) {
    throw new Error("usePlayback must be used within a PlaybackProvider");
  }
  return context;
}
