import { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  Stack,
  CircularProgress,
  Container,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormHelperText,
  IconButton,
  Tooltip,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Collapse,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import * as Tone from "tone";
import { generateMidi, restoreConversation } from "../lib/api";
import type { components } from "../types/api";

type MidiResponse = components["schemas"]["MidiResponse"];
type GenerateRequest = components["schemas"]["GenerateRequest"];

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  midiResponse?: MidiResponse;
}

const MODEL_OPTIONS: GenerateRequest["plan_model"][] = [
  "claude-haiku-4-5",
  "claude-sonnet-4-5",
  "gpt-4o-mini",
  "gpt-4o",
  "gpt-5-2",
  "gpt-5-mini",
  "gpt-5-nano",
];

const KEY_OPTIONS: NonNullable<GenerateRequest["key"]>[] = [
  "C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
];

const TIME_SIGNATURE_OPTIONS: NonNullable<GenerateRequest["time_signature"]>[] = [
  "3/4", "4/4", "5/4", "6/8", "7/8",
];

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Form state
  const [userId] = useState("550e8400-e29b-41d4-a716-446655440000");
  const [threadId, setThreadId] = useState("550e8400-e29b-41d4-a716-446655440001");
  const [planModel, setPlanModel] = useState<GenerateRequest["plan_model"]>("gpt-5-nano");
  const [generateModel, setGenerateModel] = useState<GenerateRequest["generate_model"]>("gpt-5-nano");
  const [key, setKey] = useState<GenerateRequest["key"]>(null);
  const [bpm, setBpm] = useState<number | "">(""); // Empty string for null
  const [timeSignature, setTimeSignature] = useState<GenerateRequest["time_signature"]>(null);
  const [measures, setMeasures] = useState<number | "">(""); // Empty string for null

  // MIDI state
  const [midiAccess, setMidiAccess] = useState<MIDIAccess | null>(null);
  const [midiOutputs, setMidiOutputs] = useState<MIDIOutput[]>([]);
  const [selectedMidiOutput, setSelectedMidiOutput] = useState<string>("browser-midi");
  const [midiAccessRequested, setMidiAccessRequested] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);

  // Tab state
  const [currentTab, setCurrentTab] = useState(0);
  const [parametersExpanded, setParametersExpanded] = useState(true);

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const shouldScrollRef = useRef(true);
  const playbackTimeoutsRef = useRef<number[]>([]);
  const synthRef = useRef<Tone.PolySynth | null>(null);
  const bpmRef = useRef<number | "">(bpm);

  // Update BPM ref whenever BPM state changes
  useEffect(() => {
    bpmRef.current = bpm;
  }, [bpm]);

  // Generate new thread ID
  const handleRegenerateThreadId = () => {
    setThreadId(crypto.randomUUID());
    setMessages([]); // Clear messages for new thread
  };

  // Request MIDI access
  const handleRequestMidiAccess = useCallback(async () => {
    try {
      setMidiAccessRequested(true);
      const access = await navigator.requestMIDIAccess();
      setMidiAccess(access);

      // Get all MIDI outputs
      const outputs: MIDIOutput[] = [];
      access.outputs.forEach((output) => {
        outputs.push(output);
      });
      setMidiOutputs(outputs);

      // Don't auto-select hardware device - keep browser-midi as default
    } catch (error) {
      console.error("MIDI access denied:", error);
      setMidiAccessRequested(false);
    }
  }, []);

  // Initialize Tone.js synth
  useEffect(() => {
    if (!synthRef.current) {
      synthRef.current = new Tone.PolySynth(Tone.Synth).toDestination();
    }
    return () => {
      if (synthRef.current) {
        synthRef.current.dispose();
        synthRef.current = null;
      }
    };
  }, []);

  // Auto-request MIDI access on mount
  useEffect(() => {
    handleRequestMidiAccess();
  }, [handleRequestMidiAccess]);

  // Restore conversation on mount
  useEffect(() => {
    const loadConversation = async () => {
      try {
        const result = await restoreConversation({
          user_id: userId,
          thread_id: threadId,
        });

        if (result.data) {
          const restoredMessages: Message[] = result.data.messages.map((msg) => {
            if (msg.role === "assistant" && msg.midi_events && msg.plan_data) {
              // Reconstruct MidiResponse from stored data
              const midiResponse: MidiResponse = {
                plan: {
                  key: msg.plan_data.key as any,
                  bpm: msg.plan_data.bpm as number,
                  time_signature: msg.plan_data.time_signature as any,
                  measures: msg.plan_data.measures as number,
                  style: msg.plan_data.style as string,
                  chord_progression: msg.plan_data.chord_progression as string[],
                  reasoning: msg.plan_data.reasoning as string,
                },
                midi: msg.midi_events as any[],
              };
              return {
                role: "assistant" as const,
                content: msg.content,
                midiResponse,
              };
            }
            return {
              role: msg.role as "user" | "assistant" | "system",
              content: msg.content,
            };
          });
          setMessages(restoredMessages);

          // Update form inputs from the last user message (for model selection)
          const lastUserMsg = result.data.messages
            .filter((m) => m.role === "user")
            .pop();
          if (lastUserMsg?.plan_model) {
            setPlanModel(lastUserMsg.plan_model as any);
          }
          if (lastUserMsg?.generate_model) {
            setGenerateModel(lastUserMsg.generate_model as any);
          }

          // Update form inputs from the last assistant message (for musical parameters)
          const lastAssistantMsg = result.data.messages
            .filter((m) => m.role === "assistant")
            .pop();
          if (lastAssistantMsg?.plan_data) {
            setKey(lastAssistantMsg.plan_data.key as any);
            setBpm(lastAssistantMsg.plan_data.bpm as number);
            setTimeSignature(lastAssistantMsg.plan_data.time_signature as any);
            setMeasures(lastAssistantMsg.plan_data.measures as number);
          }
        }
      } catch (error: any) {
        // Gracefully ignore 404 errors (expected for new conversations)
        if (error?.response?.status !== 404) {
          console.error("Failed to restore conversation:", error);
        }
      }
    };

    loadConversation();
  }, [userId, threadId]);

  // Auto-scroll to bottom when new messages arrive (unless user has scrolled up)
  useEffect(() => {
    if (shouldScrollRef.current && chatContainerRef.current) {
      // Use requestAnimationFrame to ensure DOM has updated before scrolling
      requestAnimationFrame(() => {
        if (chatContainerRef.current) {
          chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
      });
    }
  }, [messages]);

  // Restore scroll position when switching back to Generate tab
  useEffect(() => {
    if (currentTab === 0 && shouldScrollRef.current && chatContainerRef.current) {
      // Use requestAnimationFrame to ensure the tab content is fully rendered
      requestAnimationFrame(() => {
        if (chatContainerRef.current) {
          chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
      });
    }
  }, [currentTab]);

  // Cleanup playback on tab change
  useEffect(() => {
    // Stop playback when switching away from MIDI tab
    if (currentTab !== 1 && isPlaying) {
      playbackTimeoutsRef.current.forEach(id => clearTimeout(id));
      playbackTimeoutsRef.current = [];
      setIsPlaying(false);

      if (selectedMidiOutput === "browser-midi") {
        // Release all notes in Tone.js
        if (synthRef.current) {
          synthRef.current.releaseAll();
        }
      } else if (selectedMidiOutput && midiAccess) {
        const output = Array.from(midiAccess.outputs.values()).find(o => o.id === selectedMidiOutput);
        if (output) {
          output.send([0xB0, 64, 0]);  // Sustain Off
          output.send([0xB0, 123, 0]); // All Notes Off
          output.send([0xB0, 121, 0]); // Reset Controllers
        }
      }
    }
  }, [currentTab, selectedMidiOutput, midiAccess, isPlaying]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      playbackTimeoutsRef.current.forEach(id => clearTimeout(id));
      playbackTimeoutsRef.current = [];

      if (selectedMidiOutput === "browser-midi") {
        // Release all notes in Tone.js
        if (synthRef.current) {
          synthRef.current.releaseAll();
        }
      } else if (selectedMidiOutput && midiAccess) {
        const output = Array.from(midiAccess.outputs.values()).find(o => o.id === selectedMidiOutput);
        if (output) {
          output.send([0xB0, 64, 0]);  // Sustain Off
          output.send([0xB0, 123, 0]); // All Notes Off
          output.send([0xB0, 121, 0]); // Reset Controllers
        }
      }
    };
  }, []);

  // Get MIDI events from the most recent generation only
  const allMidiEvents = (() => {
    const messagesWithMidi = messages.filter(msg => msg.midiResponse);
    const lastMessage = messagesWithMidi[messagesWithMidi.length - 1];
    return lastMessage?.midiResponse?.midi || [];
  })();

  // Start MIDI playback
  const startPlayback = useCallback(() => {
    if (!selectedMidiOutput || allMidiEvents.length === 0) return;

    // Check if using Browser MIDI (Tone.js) or hardware MIDI
    const isBrowserMidi = selectedMidiOutput === "browser-midi";

    // For hardware MIDI, ensure we have access and a valid output
    let output: MIDIOutput | undefined;
    if (!isBrowserMidi) {
      if (!midiAccess) return;
      output = Array.from(midiAccess.outputs.values()).find(o => o.id === selectedMidiOutput);
      if (!output) return;
    }

    // Get time signature from the most recent generation
    const messagesWithMidi = messages.filter(msg => msg.midiResponse);
    const lastMessage = messagesWithMidi[messagesWithMidi.length - 1];
    const planBpm = lastMessage?.midiResponse?.plan.bpm || 120;
    const timeSignature = lastMessage?.midiResponse?.plan.time_signature || "4/4";
    const measures = lastMessage?.midiResponse?.plan.measures || 1;
    const beatsPerMeasure = parseInt(timeSignature.split("/")[0]) || 4;

    console.log("Starting playback:", {
      events: allMidiEvents.length,
      planBpm,
      timeSignature,
      beatsPerMeasure,
      measures
    });

    // Convert events to beat times (not absolute milliseconds)
    const beatEvents = allMidiEvents.map((event: any) => {
      const beatTime = (event.measure - 1) * beatsPerMeasure + (event.beat - 1) +
                      (event.beat_div4 - 1) / 4 + (event.beat_div16 - 1) / 16;
      const midiValue = Math.round((event.value / 100) * 127);
      return {
        beatTime: beatTime,
        event: event.event,
        value: midiValue
      };
    }).sort((a, b) => a.beatTime - b.beatTime);

    console.log("Beat events:", beatEvents.slice(0, 5));

    // Calculate total beats based on the number of measures in the pattern
    const totalBeats = measures * beatsPerMeasure;

    // Function to send a MIDI event
    const sendMidiEvent = (beatEvent: typeof beatEvents[0]) => {
      const midiNote = noteNameToMidiNumber(beatEvent.event);

      if (isBrowserMidi && synthRef.current && midiNote !== null) {
        // Convert MIDI note number to note name for Tone.js
        const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        const octave = Math.floor(midiNote / 12) - 1;
        const noteIndex = midiNote % 12;
        const noteName = `${noteNames[noteIndex]}${octave}`;

        if (beatEvent.value > 0) {
          const velocity = beatEvent.value / 127;
          synthRef.current.triggerAttack(noteName, Tone.now(), velocity);
        } else {
          synthRef.current.triggerRelease(noteName, Tone.now());
        }
      } else if (output) {
        if (midiNote !== null) {
          if (beatEvent.value > 0) {
            output.send([0x90, midiNote, beatEvent.value]);
          } else {
            output.send([0x80, midiNote, 0]);
          }
        } else {
          // Handle control messages
          if (beatEvent.event === "Sustain") {
            output.send([0xB0, 64, beatEvent.value]);
          } else if (beatEvent.event === "ModWheel") {
            output.send([0xB0, 1, beatEvent.value]);
          } else if (beatEvent.event === "AllNotesOff") {
            output.send([0xB0, 123, 0]);
          }
        }
      }
    };

    // Schedule events one at a time, picking up current BPM for each
    const scheduleNextEvent = (index: number, currentBeat: number) => {
      if (index >= beatEvents.length) {
        // All events played, schedule loop restart
        const currentBpm = (typeof bpmRef.current === 'number' && bpmRef.current > 0) ? bpmRef.current : planBpm;
        const remainingBeats = totalBeats - currentBeat;
        const remainingMs = remainingBeats * (60000 / currentBpm);

        const loopTimeoutId = window.setTimeout(() => {
          console.log("Looping back to start");
          startPlayback();
        }, remainingMs);
        playbackTimeoutsRef.current.push(loopTimeoutId);
        return;
      }

      const nextEvent = beatEvents[index];
      const currentBpm = (typeof bpmRef.current === 'number' && bpmRef.current > 0) ? bpmRef.current : planBpm;
      const beatDelta = nextEvent.beatTime - currentBeat;
      const delayMs = beatDelta * (60000 / currentBpm);

      const timeoutId = window.setTimeout(() => {
        sendMidiEvent(nextEvent);
        scheduleNextEvent(index + 1, nextEvent.beatTime);
      }, delayMs);

      playbackTimeoutsRef.current.push(timeoutId);
    };

    // Start scheduling from first event
    scheduleNextEvent(0, 0);
  }, [selectedMidiOutput, midiAccess, allMidiEvents, messages]);

  const handleScroll = () => {
    if (chatContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
      // Check if user is at the bottom (within 2px to account for subpixel rendering)
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 2;
      shouldScrollRef.current = isAtBottom;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    shouldScrollRef.current = true; // Re-enable auto-scroll on new message

    try {
      const result = await generateMidi({
        user_id: userId,
        thread_id: threadId,
        plan_model: planModel,
        generate_model: generateModel,
        prompt: input,
        key: key,
        bpm: bpm === "" ? null : bpm,
        time_signature: timeSignature,
        measures: measures === "" ? null : measures,
      });

      if (result.data) {
        const assistantMessage: Message = {
          role: "assistant",
          content: result.data.plan.reasoning,
          midiResponse: result.data,
        };

        // Track previous values before updating
        const { plan } = result.data;
        const changedParams: string[] = [];

        if (plan.key !== key) changedParams.push("key");
        if (plan.bpm !== (bpm === "" ? null : bpm)) changedParams.push("bpm");
        if (plan.time_signature !== timeSignature) changedParams.push("time signature");
        if (plan.measures !== (measures === "" ? null : measures)) changedParams.push("measures");

        // Create system message if any params changed
        const newMessages: Message[] = [assistantMessage];
        if (changedParams.length > 0) {
          const systemMessage: Message = {
            role: "system",
            content: `Updated ${changedParams.join(", ")}`,
          };
          newMessages.push(systemMessage);
        }

        setMessages((prev) => [...prev, ...newMessages]);

        // Update form inputs with returned values from the plan
        setKey(plan.key);
        setBpm(plan.bpm);
        setTimeSignature(plan.time_signature);
        setMeasures(plan.measures);
      } else if (result.error) {
        const errorMessage: Message = {
          role: "assistant",
          content: `Error: ${JSON.stringify(result.error)}`,
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Convert note name to MIDI note number (e.g., "C4" -> 60)
  const noteNameToMidiNumber = (noteName: string): number | null => {
    const noteMap: { [key: string]: number } = {
      "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4,
      "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
    };

    const match = noteName.match(/^([A-G][b#]?)(-?\d+)$/);
    if (!match) return null;

    const [, note, octave] = match;
    const noteValue = noteMap[note];
    if (noteValue === undefined) return null;

    return (parseInt(octave) + 1) * 12 + noteValue;
  };

  // Play/Stop MIDI playback
  const handlePlayStop = () => {
    if (isPlaying) {
      // Stop playback
      playbackTimeoutsRef.current.forEach(id => clearTimeout(id));
      playbackTimeoutsRef.current = [];
      setIsPlaying(false);

      // Stop all notes
      if (selectedMidiOutput === "browser-midi") {
        // Release all notes in Tone.js
        if (synthRef.current) {
          synthRef.current.releaseAll();
        }
      } else if (selectedMidiOutput && midiAccess) {
        // Send cleanup messages to hardware MIDI
        const output = Array.from(midiAccess.outputs.values()).find(o => o.id === selectedMidiOutput);
        if (output) {
          output.send([0xB0, 64, 0]);  // Sustain Off
          output.send([0xB0, 123, 0]); // All Notes Off
          output.send([0xB0, 121, 0]); // Reset Controllers
        }
      }
    } else {
      // Start playback
      setIsPlaying(true);
      startPlayback();
    }
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper
        elevation={2}
        sx={{
          p: 3,
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 2,
        }}
      >
        {/* Header */}
        <Typography variant="h5" component="h1" gutterBottom>
          MIDI Agent
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Configure parameters and describe the music you want to create
        </Typography>

        {/* Tabs */}
        <Tabs value={currentTab} onChange={(_, newValue) => setCurrentTab(newValue)} sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}>
          <Tab label="Generate" />
          <Tab label="MIDI" />
        </Tabs>

        {/* Tab Content */}
        {currentTab === 0 && (
          <>
            {/* Parameters Form */}
            <Box sx={{ mb: 3 }}>
              {/* Collapsible Header */}
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  mb: 2,
                  cursor: "pointer",
                }}
                onClick={() => setParametersExpanded(!parametersExpanded)}
              >
                <Typography variant="subtitle1">
                  Parameters
                </Typography>
                <IconButton
                  size="small"
                  sx={{
                    transform: parametersExpanded ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 0.3s",
                  }}
                >
                  <ExpandMoreIcon />
                </IconButton>
              </Box>

              {/* Collapsible Content */}
              <Collapse in={parametersExpanded}>
                <Stack spacing={2}>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  {/* User ID & Thread ID */}
                  <TextField
                    fullWidth
                    label="User ID"
                    value={userId}
                    size="small"
                    helperText="UUID for tracking"
                    disabled
                  />
                  <Box sx={{ position: "relative", width: "100%" }}>
                    <TextField
                      fullWidth
                      label="Thread ID"
                      value={threadId}
                      size="small"
                      helperText="Conversation context"
                      disabled
                      slotProps={{
                        input: {
                          endAdornment: (
                            <Tooltip title="Generate new thread ID">
                              <IconButton
                                size="small"
                                onClick={handleRegenerateThreadId}
                                edge="end"
                              >
                                <RefreshIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ),
                        },
                      }}
                    />
                  </Box>
                </Stack>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  {/* Plan Model & Generate Model */}
                  <FormControl fullWidth size="small">
                    <InputLabel>Plan Model</InputLabel>
                    <Select
                      value={planModel}
                      label="Plan Model"
                      onChange={(e) => setPlanModel(e.target.value as GenerateRequest["plan_model"])}
                    >
                      {MODEL_OPTIONS.map((model) => (
                        <MenuItem key={model} value={model}>
                          {model}
                        </MenuItem>
                      ))}
                    </Select>
                    <FormHelperText>Model for planning stage</FormHelperText>
                  </FormControl>
                  <FormControl fullWidth size="small">
                    <InputLabel>Generate Model</InputLabel>
                    <Select
                      value={generateModel}
                      label="Generate Model"
                      onChange={(e) => setGenerateModel(e.target.value as GenerateRequest["generate_model"])}
                    >
                      {MODEL_OPTIONS.map((model) => (
                        <MenuItem key={model} value={model}>
                          {model}
                        </MenuItem>
                      ))}
                    </Select>
                    <FormHelperText>Model for generation stage</FormHelperText>
                  </FormControl>
                </Stack>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  {/* Key */}
                  <FormControl fullWidth size="small">
                    <InputLabel>Key</InputLabel>
                    <Select<string>
                      value={key || ""}
                      label="Key"
                      onChange={(e) => setKey(e.target.value === "" ? null : e.target.value as NonNullable<GenerateRequest["key"]>)}
                    >
                      <MenuItem value="">
                        <em>None (auto)</em>
                      </MenuItem>
                      {KEY_OPTIONS.map((k) => (
                        <MenuItem key={k} value={k}>
                          {k}
                        </MenuItem>
                      ))}
                    </Select>
                    <FormHelperText>Musical key (optional)</FormHelperText>
                  </FormControl>
                  <TextField
                    fullWidth
                    label="BPM"
                    type="number"
                    value={bpm}
                    onChange={(e) => {
                      const val = e.target.value;
                      setBpm(val === "" ? "" : Number(val));
                    }}
                    size="small"
                    inputProps={{ min: 30, max: 360 }}
                    helperText="Tempo 30-360 (optional)"
                  />
                </Stack>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  {/* Time Signature */}
                  <FormControl fullWidth size="small">
                    <InputLabel>Time Signature</InputLabel>
                    <Select<string>
                      value={timeSignature || ""}
                      label="Time Signature"
                      onChange={(e) => setTimeSignature(e.target.value === "" ? null : e.target.value as NonNullable<GenerateRequest["time_signature"]>)}
                    >
                      <MenuItem value="">
                        <em>None (auto)</em>
                      </MenuItem>
                      {TIME_SIGNATURE_OPTIONS.map((ts) => (
                        <MenuItem key={ts} value={ts}>
                          {ts}
                        </MenuItem>
                      ))}
                    </Select>
                    <FormHelperText>Time signature (optional)</FormHelperText>
                  </FormControl>
                  <TextField
                    fullWidth
                    label="Measures"
                    type="number"
                    value={measures}
                    onChange={(e) => {
                      const val = e.target.value;
                      setMeasures(val === "" ? "" : Number(val));
                    }}
                    size="small"
                    inputProps={{ min: 1, max: 32 }}
                    helperText="Number of measures 1-32 (optional)"
                  />
                </Stack>

                </Stack>
              </Collapse>
            </Box>

            {/* Chat History */}
            <Box
              ref={chatContainerRef}
              onScroll={handleScroll}
              sx={{
                maxHeight: 300,
                overflow: "auto",
                mb: 2,
                p: 2,
                bgcolor: "background.default",
                borderRadius: 1,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Stack spacing={2}>
                {messages.length === 0 && (
                  <Box sx={{ textAlign: "center", py: 4 }}>
                    <Typography color="text.secondary" variant="body2">
                      No messages yet. Start by describing the music you'd like to generate.
                    </Typography>
                  </Box>
                )}

                {messages.map((message, index) => {
                  // System messages: gray text, no bubble
                  if (message.role === "system") {
                    return (
                      <Box key={index} sx={{ textAlign: "center", py: 0.5 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic" }}>
                          {message.content}
                        </Typography>
                      </Box>
                    );
                  }

                  // User and assistant messages: bubbles
                  return (
                    <Box
                      key={index}
                      sx={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: message.role === "user" ? "flex-end" : "flex-start",
                      }}
                    >
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ mb: 0.5, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 }}
                      >
                        {message.role === "user" ? "You" : "MIDI Agent"}
                      </Typography>
                      <Paper
                        elevation={0}
                        sx={{
                          p: 1.5,
                          maxWidth: "85%",
                          bgcolor: message.role === "user" ? "primary.main" : "action.hover",
                          color: message.role === "user" ? "primary.contrastText" : "text.primary",
                        }}
                      >
                        <Typography
                          variant="body2"
                          sx={{
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                          }}
                        >
                          {message.content}
                        </Typography>
                      </Paper>
                    </Box>
                  );
                })}

                {isLoading && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <CircularProgress size={16} />
                    <Typography variant="caption" color="text.secondary">
                      Generating...
                    </Typography>
                  </Box>
                )}
              </Stack>
            </Box>

            {/* Chat Input */}
            <Box component="form" onSubmit={handleSubmit}>
              <Stack direction="row" spacing={1}>
                <TextField
                  fullWidth
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Describe the music you want..."
                  disabled={isLoading}
                  variant="outlined"
                  size="small"
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={isLoading || !input.trim()}
                  sx={{ minWidth: 100 }}
                >
                  {isLoading ? "..." : "Send"}
                </Button>
              </Stack>
            </Box>
          </>
        )}

        {/* MIDI Tab */}
        {currentTab === 1 && (
          <Box>
            {/* MIDI Controls */}
            <Stack spacing={2} sx={{ mb: 3 }}>
              {/* MIDI Access Button */}
              <Button
                variant="contained"
                color={midiAccess ? "success" : "error"}
                onClick={handleRequestMidiAccess}
                disabled={midiAccessRequested || midiAccess !== null}
                size="medium"
                fullWidth
              >
                {midiAccess ? "MIDI access granted" : (midiAccessRequested ? "Requesting access..." : "Allow MIDI access")}
              </Button>

              {/* MIDI Output Device Dropdown */}
              <FormControl fullWidth size="small">
                <InputLabel>MIDI Output Device</InputLabel>
                <Select
                  value={selectedMidiOutput}
                  label="MIDI Output Device"
                  onChange={(e) => setSelectedMidiOutput(e.target.value)}
                  disabled={isPlaying}
                >
                  {/* Browser MIDI - always available */}
                  <MenuItem value="browser-midi">Browser MIDI</MenuItem>

                  {/* Hardware MIDI devices */}
                  {midiOutputs.map((output) => (
                    <MenuItem key={output.id} value={output.id}>
                      {output.name || `Device ${output.id}`}
                    </MenuItem>
                  ))}
                </Select>
                <FormHelperText>Select MIDI output for playback</FormHelperText>
              </FormControl>

              {/* BPM Input */}
              <TextField
                fullWidth
                label="BPM"
                type="number"
                value={bpm}
                onChange={(e) => {
                  const val = e.target.value;
                  setBpm(val === "" ? "" : Number(val));
                }}
                size="small"
                inputProps={{ min: 30, max: 360 }}
                helperText="Tempo 30-360 (optional)"
              />
            </Stack>

            {/* Play/Stop Button */}
            <Box sx={{ mb: 2 }}>
              <Button
                variant="contained"
                color={isPlaying ? "error" : "primary"}
                onClick={handlePlayStop}
                disabled={allMidiEvents.length === 0}
                fullWidth
              >
                {isPlaying ? "Stop" : "Play"}
              </Button>
            </Box>

            {/* MIDI Events Display */}
            {allMidiEvents.length === 0 ? (
              <Box sx={{ textAlign: "center", py: 8 }}>
                <Typography color="text.secondary" variant="body1">
                  No MIDI
                </Typography>
              </Box>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Measure</TableCell>
                      <TableCell>Beat</TableCell>
                      <TableCell>Timing</TableCell>
                      <TableCell>Event</TableCell>
                      <TableCell>Value</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {allMidiEvents.map((event: any, index: number) => (
                      <TableRow key={index}>
                        <TableCell>{event.measure}</TableCell>
                        <TableCell>{event.beat}</TableCell>
                        <TableCell>{event.beat_div4}.{event.beat_div16}</TableCell>
                        <TableCell>{event.event}</TableCell>
                        <TableCell>{event.value}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        )}
      </Paper>
    </Container>
  );
}
