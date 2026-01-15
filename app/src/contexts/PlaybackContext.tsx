import { createContext, useContext, useState, useEffect, useRef, useCallback, type ReactNode } from "react";

// Dynamic import to avoid initializing AudioContext on page load
let Tone: typeof import("tone") | null = null;
async function getTone() {
  if (!Tone) {
    Tone = await import("tone");
  }
  return Tone;
}

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
  repeat: number;
  midi_events: MidiEvent[];
  track_id: string;
}

interface Track {
  id: string;
  midi_channel: number;
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
  play: () => void;
  pause: () => void;
  stop: () => void;
  togglePlayPause: () => void;
  setBpm: (bpm: number) => void;
  loadSong: (songData: SongData | null) => void;
  midiOutputs: MidiOutput[];
  selectedMidiOutput: MidiOutput;
  setSelectedMidiOutput: (output: MidiOutput) => void;
  requestMidiAccess: () => Promise<void>;
  hasMidiAccess: boolean;
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
  const synthsRef = useRef<Map<number, any>>(new Map());
  const [midiOutputs, setMidiOutputs] = useState<MidiOutput[]>([BROWSER_AUDIO_OUTPUT]);
  const [selectedMidiOutput, setSelectedMidiOutput] = useState<MidiOutput>(BROWSER_AUDIO_OUTPUT);
  const [hasMidiAccess, setHasMidiAccess] = useState(false);
  const midiAccessRef = useRef<MIDIAccess | null>(null);
  const audioContextStartedRef = useRef<boolean>(false);

  // Playback state
  const animationFrameRef = useRef<number | null>(null);
  const currentBeatRef = useRef<number>(-1);
  const isPlayingRef = useRef<boolean>(false);
  const bpmRef = useRef<number>(bpm);

  // Keep refs in sync with state
  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  useEffect(() => {
    bpmRef.current = bpm;
  }, [bpm]);

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

        const synth = synthsRef.current.get(channel);
        if (!synth) return;

        const now = Tone!.now();
        events.forEach((event) => {
          const note = Tone!.Frequency(event.event).toFrequency();

          if (typeof note === "number" && Number.isFinite(note)) {
            if (event.value > 0) {
              synth.triggerAttack(note, now, event.value / 100);
            } else {
              synth.triggerRelease(note, now);
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
              output.send([0x90 + (channel - 1), note, velocity]);
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
      const prevBeat = currentBeatRef.current;
      const curBeat = Math.max(0, prevBeat) + beatDelta;
      currentBeatRef.current = curBeat;

      // Collect events that should fire in this frame
      const eventsToSend: Array<{ channel: number; event: MidiEvent }> = [];

      currentSongData.tracks.forEach((track) => {
        track.loops.forEach((loop) => {
          const loopStartBeat = loop.offset * beatsPerMeasure;
          const loopEndBeat = loopStartBeat + loop.measures * beatsPerMeasure * loop.repeat;

          if (curBeat >= loopStartBeat && curBeat < loopEndBeat) {
            loop.midi_events.forEach((event) => {
              const eventBeat =
                loopStartBeat +
                (event.measure - 1) * beatsPerMeasure +
                (event.beat - 1) +
                (event.beat_div4 - 1) / 4 +
                (event.beat_div16 - 1) / 16;
              if (eventBeat > prevBeat && eventBeat <= curBeat) {
                eventsToSend.push({ channel: track.midi_channel, event });
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

    songData.tracks.forEach((track) => {
      if (!synthsRef.current.has(track.midi_channel)) {
        const synth = new Tone!.PolySynth(Tone!.Synth, {
          oscillator: { type: "triangle" },
          envelope: {
            attack: 0.005,
            decay: 0.1,
            sustain: 0.3,
            release: 5,
          },
        }).toDestination();
        synthsRef.current.set(track.midi_channel, synth);
        console.log(`Created synth for MIDI channel ${track.midi_channel}`);
      }
    });
  }, [songData, selectedMidiOutput]);

  // Scan for MIDI devices when MIDI access is granted
  const scanMidiDevices = useCallback((midiAccess: MIDIAccess) => {
    const devices: MidiOutput[] = [BROWSER_AUDIO_OUTPUT];

    midiAccess.outputs.forEach((output) => {
      devices.push({
        id: output.id || output.name || "unknown",
        name: output.name || "Unnamed MIDI Device",
        type: "device",
      });
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

  // Check if MIDI access was previously granted on mount
  useEffect(() => {
    if (navigator.requestMIDIAccess) {
      navigator
        .requestMIDIAccess()
        .then((midiAccess) => {
          midiAccessRef.current = midiAccess;
          setHasMidiAccess(true);
          scanMidiDevices(midiAccess);

          midiAccess.onstatechange = () => {
            scanMidiDevices(midiAccess);
          };
        })
        .catch(() => {
          console.log("MIDI access not yet granted");
        });
    }
  }, [scanMidiDevices]);

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

    // Reset to beginning
    currentBeatRef.current = -1; // -1 to make sure we don't skip the first beat
    setIsPlaying(true);
  };

  const pause = () => {
    setIsPlaying(false);
  };

  const stop = () => {
    setIsPlaying(false);
    currentBeatRef.current = -1;
  };

  const togglePlayPause = async () => {
    if (isPlaying) {
      pause();
    } else {
      await play();
    }
  };

  const setBpm = (newBpm: number) => {
    setBpmState(newBpm);
  };

  const loadSong = useCallback(
    (newSongData: SongData | null) => {
      // Stop playback only if song data is cleared
      if (!newSongData && isPlaying) {
        setIsPlaying(false);
      }
      currentBeatRef.current = -1;
      setSongData(newSongData);

      // Update BPM from song data if provided
      if (newSongData) {
        setBpmState(newSongData.bpm);
      }
    },
    [isPlaying]
  );

  return (
    <PlaybackContext.Provider
      value={{
        isPlaying,
        bpm,
        play,
        pause,
        stop,
        togglePlayPause,
        setBpm,
        loadSong,
        midiOutputs,
        selectedMidiOutput,
        setSelectedMidiOutput,
        requestMidiAccess,
        hasMidiAccess,
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
