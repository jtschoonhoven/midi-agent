import { createContext, useContext, useState, useEffect, useRef, useCallback, type ReactNode } from "react";
import * as Tone from "tone";

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
  time_signature?: string;
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

// Scheduled event with absolute timestamp
interface ScheduledEvent {
  timestamp: number; // in seconds
  channel: number;
  note: number;
  velocity: number;
  trackId: string;
}

export function PlaybackProvider({ children }: { children: ReactNode }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [bpm, setBpmState] = useState(120);
  const [songData, setSongData] = useState<SongData | null>(null);
  const synthsRef = useRef<Map<number, Tone.PolySynth>>(new Map());
  const [midiOutputs, setMidiOutputs] = useState<MidiOutput[]>([BROWSER_AUDIO_OUTPUT]);
  const [selectedMidiOutput, setSelectedMidiOutput] = useState<MidiOutput>(BROWSER_AUDIO_OUTPUT);
  const [hasMidiAccess, setHasMidiAccess] = useState(false);
  const midiAccessRef = useRef<MIDIAccess | null>(null);

  // Playback state
  const playbackStartTimeRef = useRef<number>(0);
  const scheduledEventsRef = useRef<ScheduledEvent[]>([]);
  const eventIndexRef = useRef<number>(0);
  const animationFrameRef = useRef<number | null>(null);

  // Get beats per measure from time signature string (e.g., "4/4" -> 4, "3/4" -> 3, "6/8" -> 6)
  const getBeatsPerMeasure = (timeSignature?: string): number => {
    if (!timeSignature) return 4;
    const [numerator] = timeSignature.split("/").map(Number);
    return numerator || 4;
  };

  // Convert MIDI event timing to absolute timestamp in seconds
  const midiEventToSeconds = (
    event: MidiEvent,
    measureOffset: number,
    currentBpm: number,
    timeSignature?: string
  ): number => {
    const { measure, beat, beat_div4, beat_div16 } = event;

    // Calculate absolute measure position including offset
    const absoluteMeasure = measure + measureOffset;

    // Calculate total beats from start
    const beatsPerMeasure = getBeatsPerMeasure(timeSignature);
    const totalBeats = absoluteMeasure * beatsPerMeasure + beat;

    // Add subdivisions
    // beat_div4 ranges 0-3, beat_div16 ranges 0-3, giving 16 subdivisions per beat
    const subdivision = (beat_div4 * 4 + beat_div16) / 16; // Convert to fraction of a beat
    const totalBeatsWithSubdivision = totalBeats + subdivision;

    // Convert beats to seconds: (beats / bpm) * 60
    const seconds = (totalBeatsWithSubdivision / currentBpm) * 60;

    return seconds;
  };

  // Build sorted list of all events with absolute timestamps
  const buildEventSchedule = useCallback((songData: SongData, currentBpm: number): ScheduledEvent[] => {
    const events: ScheduledEvent[] = [];

    songData.tracks.forEach((track) => {
      let trackOffsetMeasures = 0;

      track.loops.forEach((loop) => {
        // Schedule events for each repeat of the loop
        for (let repeat = 0; repeat < loop.repeat; repeat++) {
          const loopOffsetMeasures = trackOffsetMeasures + (repeat * loop.measures);

          loop.midi_events.forEach((event) => {
            if (event.event === "note_on") {
              const timestamp = midiEventToSeconds(
                event,
                loopOffsetMeasures,
                currentBpm,
                songData.time_signature
              );

              events.push({
                timestamp,
                channel: track.midi_channel,
                note: event.value,
                velocity: 100, // Default velocity
                trackId: track.id,
              });
            }
          });
        }

        // Update offset for next loop (all repeats of current loop)
        trackOffsetMeasures += loop.measures * loop.repeat;
      });
    });

    // Sort by timestamp
    events.sort((a, b) => a.timestamp - b.timestamp);

    console.log(`Built schedule with ${events.length} MIDI events`);
    return events;
  }, []);

  // Generic MIDI send function
  const sendMidiNote = useCallback((channel: number, note: number, velocity: number) => {
    if (selectedMidiOutput.type === "browser") {
      // Use Tone.js for browser audio
      const synth = synthsRef.current.get(channel);
      if (synth) {
        const freq = Tone.Frequency(note, "midi").toFrequency();
        synth.triggerAttackRelease(freq, "8n");
      }
    } else {
      // Send to real MIDI device
      const midiAccess = midiAccessRef.current;
      if (!midiAccess) return;

      // Find the matching MIDI output
      midiAccess.outputs.forEach((output) => {
        const outputId = output.id || output.name || "unknown";
        if (outputId === selectedMidiOutput.id) {
          // MIDI note on message: [status, note, velocity]
          // Status byte: 0x90 + channel (0-15)
          const noteOnStatus = 0x90 + (channel - 1); // Convert 1-indexed to 0-indexed
          output.send([noteOnStatus, note, velocity]);

          // Schedule note off after a short duration (8th note approximation)
          const noteDurationMs = (60 / bpm) * 1000 / 2; // 8th note duration
          setTimeout(() => {
            const noteOffStatus = 0x80 + (channel - 1);
            output.send([noteOffStatus, note, 0]);
          }, noteDurationMs);
        }
      });
    }
  }, [selectedMidiOutput, bpm]);

  // Playback loop using requestAnimationFrame
  const playbackLoop = useCallback(() => {
    if (!isPlaying) return;

    const currentTime = performance.now();
    const elapsedSeconds = (currentTime - playbackStartTimeRef.current) / 1000;

    // Process all events up to current elapsed time
    const events = scheduledEventsRef.current;
    let currentIndex = eventIndexRef.current;

    while (currentIndex < events.length && events[currentIndex].timestamp <= elapsedSeconds) {
      const event = events[currentIndex];
      sendMidiNote(event.channel, event.note, event.velocity);
      currentIndex++;
    }

    eventIndexRef.current = currentIndex;

    // Continue loop if there are more events
    if (currentIndex < events.length) {
      animationFrameRef.current = requestAnimationFrame(playbackLoop);
    } else {
      // Playback finished
      console.log("Playback finished");
      setIsPlaying(false);
    }
  }, [isPlaying, sendMidiNote]);

  // Start/continue playback loop when isPlaying changes
  useEffect(() => {
    if (isPlaying) {
      playbackStartTimeRef.current = performance.now();
      animationFrameRef.current = requestAnimationFrame(playbackLoop);
    } else {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    }

    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, playbackLoop]);

  // Rebuild event schedule when song data or BPM changes
  useEffect(() => {
    if (!songData) {
      scheduledEventsRef.current = [];
      return;
    }

    // Build the event schedule
    const events = buildEventSchedule(songData, bpm);
    scheduledEventsRef.current = events;
    eventIndexRef.current = 0;

    // Create synths for browser audio output if needed
    if (selectedMidiOutput.type === "browser") {
      songData.tracks.forEach((track) => {
        if (!synthsRef.current.has(track.midi_channel)) {
          const synth = new Tone.PolySynth(Tone.Synth, {
            oscillator: { type: "triangle" },
            envelope: {
              attack: 0.005,
              decay: 0.1,
              sustain: 0.3,
              release: 1,
            },
          }).toDestination();
          synthsRef.current.set(track.midi_channel, synth);
          console.log(`Created synth for MIDI channel ${track.midi_channel}`);
        }
      });
    }
  }, [songData, bpm, selectedMidiOutput, buildEventSchedule]);

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
      navigator.requestMIDIAccess()
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
    if (selectedMidiOutput.type === "browser" && Tone.context.state !== "running") {
      await Tone.start();
    }

    // Reset to beginning
    eventIndexRef.current = 0;
    setIsPlaying(true);
  };

  const pause = () => {
    setIsPlaying(false);
  };

  const stop = () => {
    setIsPlaying(false);
    eventIndexRef.current = 0;
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
    // Rebuild schedule with new BPM if song is loaded
    if (songData) {
      const events = buildEventSchedule(songData, newBpm);
      scheduledEventsRef.current = events;
      eventIndexRef.current = 0;
    }
  };

  const loadSong = useCallback((newSongData: SongData | null) => {
    // Stop playback when loading new song
    if (isPlaying) {
      setIsPlaying(false);
    }
    eventIndexRef.current = 0;
    setSongData(newSongData);

    // Update BPM from song data if provided
    if (newSongData) {
      setBpmState(newSongData.bpm);
    }
  }, [isPlaying]);

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
