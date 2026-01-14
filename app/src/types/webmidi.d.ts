/**
 * Type definitions for Web MIDI API
 * https://www.w3.org/TR/webmidi/
 */

interface Navigator {
  requestMIDIAccess(options?: MIDIOptions): Promise<MIDIAccess>;
}

interface MIDIOptions {
  sysex?: boolean;
  software?: boolean;
}

interface MIDIAccess extends EventTarget {
  inputs: MIDIInputMap;
  outputs: MIDIOutputMap;
  onstatechange: ((event: MIDIConnectionEvent) => void) | null;
  sysexEnabled: boolean;
}

interface MIDIInputMap extends ReadonlyMap<string, MIDIInput> {}
interface MIDIOutputMap extends ReadonlyMap<string, MIDIOutput> {}

interface MIDIPort extends EventTarget {
  id: string;
  manufacturer?: string;
  name?: string;
  type: MIDIPortType;
  version?: string;
  state: MIDIPortDeviceState;
  connection: MIDIPortConnectionState;
  onstatechange: ((event: MIDIConnectionEvent) => void) | null;
  open(): Promise<MIDIPort>;
  close(): Promise<MIDIPort>;
}

interface MIDIInput extends MIDIPort {
  type: "input";
  onmidimessage: ((event: MIDIMessageEvent) => void) | null;
}

interface MIDIOutput extends MIDIPort {
  type: "output";
  send(data: Uint8Array | number[], timestamp?: number): void;
  clear(): void;
}

type MIDIPortType = "input" | "output";
type MIDIPortDeviceState = "connected" | "disconnected";
type MIDIPortConnectionState = "open" | "closed" | "pending";

interface MIDIConnectionEvent extends Event {
  port: MIDIPort;
}

interface MIDIMessageEvent extends Event {
  data: Uint8Array;
  receivedTime: number;
}
