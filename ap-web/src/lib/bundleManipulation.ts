/**
 * Client-side agent bundle manipulation: download, modify, and re-upload
 * `.tar.gz` bundles via the session agent endpoints.
 *
 * Used by the in-session MCP server editor to add/remove MCP server
 * YAML files (`tools/mcp/<name>.yaml`) from an existing agent bundle
 * without re-authoring the entire spec.
 */

import { authenticatedFetch } from "./identity";
import type { McpServerSummary } from "@/hooks/useAgents";

// ── Tar helpers ────────────────────────────────────────────────────

interface TarEntry {
  name: string;
  content: Uint8Array;
}

/** Decompress gzip bytes using the browser's DecompressionStream. */
async function gunzip(data: ArrayBuffer): Promise<Uint8Array> {
  const ds = new DecompressionStream("gzip");
  const writer = ds.writable.getWriter();
  writer.write(data);
  writer.close();
  const reader = ds.readable.getReader();
  const chunks: Uint8Array[] = [];
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(new Uint8Array(value));
  }
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const result = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    result.set(c, off);
    off += c.length;
  }
  return result;
}

/** Gzip compress bytes. */
async function gzip(data: Uint8Array): Promise<Uint8Array> {
  const cs = new CompressionStream("gzip");
  const writer = cs.writable.getWriter();
  writer.write(data.buffer as ArrayBuffer);
  writer.close();
  const reader = cs.readable.getReader();
  const chunks: Uint8Array[] = [];
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(new Uint8Array(value));
  }
  const total = chunks.reduce((n, c) => n + c.length, 0);
  const result = new Uint8Array(total);
  let off = 0;
  for (const c of chunks) {
    result.set(c, off);
    off += c.length;
  }
  return result;
}

/** Read a null-terminated string from a tar header field. */
function readTarString(tar: Uint8Array, offset: number, length: number): string {
  const slice = tar.slice(offset, offset + length);
  const nullIdx = slice.indexOf(0);
  return new TextDecoder().decode(nullIdx >= 0 ? slice.slice(0, nullIdx) : slice);
}

/** Read an octal number from a tar header field. */
function readTarOctal(tar: Uint8Array, offset: number, length: number): number {
  return parseInt(readTarString(tar, offset, length), 8) || 0;
}

/** Parse a POSIX tar archive into entries. */
function parseTar(tar: Uint8Array): TarEntry[] {
  const entries: TarEntry[] = [];
  let pos = 0;
  while (pos + 512 <= tar.length) {
    // Check for end-of-archive (two zero blocks)
    let allZero = true;
    for (let i = 0; i < 512; i++) {
      if (tar[pos + i] !== 0) {
        allZero = false;
        break;
      }
    }
    if (allZero) break;

    const name = readTarString(tar, pos, 100);
    const size = readTarOctal(tar, pos + 124, 12);
    const prefix = readTarString(tar, pos + 345, 155);
    const fullName = prefix ? `${prefix}/${name}` : name;

    const contentStart = pos + 512;
    const content = tar.slice(contentStart, contentStart + size);
    entries.push({ name: fullName, content: new Uint8Array(content) });

    // Advance past header + content blocks (padded to 512)
    pos = contentStart + Math.ceil(size / 512) * 512;
  }
  return entries;
}

/** Write a number as null-terminated octal string into a tar header. */
function writeOctal(header: Uint8Array, offset: number, length: number, value: number): void {
  const str = value.toString(8).padStart(length - 1, "0");
  const bytes = new TextEncoder().encode(str);
  header.set(bytes.slice(0, length - 1), offset);
  header[offset + length - 1] = 0;
}

/** Build a POSIX tar archive from entries. */
function buildTar(entries: TarEntry[]): Uint8Array {
  const blocks: Uint8Array[] = [];
  const encoder = new TextEncoder();

  for (const entry of entries) {
    const header = new Uint8Array(512);
    // Split long names into prefix (345) + name (100)
    let name = entry.name;
    let prefix = "";
    if (name.length > 100) {
      const sep = name.lastIndexOf("/", 99);
      if (sep > 0) {
        prefix = name.slice(0, sep);
        name = name.slice(sep + 1);
      }
    }
    header.set(encoder.encode(name).slice(0, 100), 0);
    if (prefix) header.set(encoder.encode(prefix).slice(0, 155), 345);

    writeOctal(header, 100, 8, 0o644);
    writeOctal(header, 108, 8, 0);
    writeOctal(header, 116, 8, 0);
    writeOctal(header, 124, 12, entry.content.length);
    writeOctal(header, 136, 12, Math.floor(Date.now() / 1000));
    header[156] = 0x30; // '0' regular file
    header.set(encoder.encode("ustar\0"), 257);
    header.set(encoder.encode("00"), 263);

    // Checksum
    for (let i = 148; i < 156; i++) header[i] = 0x20;
    let checksum = 0;
    for (let i = 0; i < 512; i++) checksum += header[i];
    writeOctal(header, 148, 7, checksum);
    header[155] = 0x20;

    blocks.push(header);
    const contentBlocks = Math.ceil(entry.content.length / 512);
    const padded = new Uint8Array(contentBlocks * 512);
    padded.set(entry.content);
    blocks.push(padded);
  }

  // End-of-archive
  blocks.push(new Uint8Array(1024));

  const totalSize = blocks.reduce((sum, b) => sum + b.length, 0);
  const result = new Uint8Array(totalSize);
  let offset = 0;
  for (const block of blocks) {
    result.set(block, offset);
    offset += block.length;
  }
  return result;
}

// ── Public API ─────────────────────────────────────────────────────

/** YAML quote a string value if it contains special characters. */
function yamlQuote(s: string): string {
  if (/[:\n"'#{}[\],&*?|>!%@`]/.test(s) || s.trim() !== s) {
    return JSON.stringify(s);
  }
  return s;
}

/** Build a tools/mcp/<name>.yaml content for an MCP server. */
function buildMcpYaml(server: McpServerInput): string {
  const lines: string[] = [];
  lines.push(`name: ${server.name}`);
  lines.push(`transport: ${server.transport}`);
  if (server.transport === "stdio") {
    if (server.command) lines.push(`command: ${yamlQuote(server.command)}`);
    if (server.args?.length) {
      lines.push(`args: [${server.args.map((a) => yamlQuote(a)).join(", ")}]`);
    }
    if (server.env && Object.keys(server.env).length > 0) {
      lines.push("env:");
      for (const [k, v] of Object.entries(server.env)) {
        lines.push(`  ${k}: ${yamlQuote(v)}`);
      }
    }
  } else {
    if (server.url) lines.push(`url: ${yamlQuote(server.url)}`);
    if (server.headers && Object.keys(server.headers).length > 0) {
      lines.push("headers:");
      for (const [k, v] of Object.entries(server.headers)) {
        lines.push(`  ${k}: ${yamlQuote(v)}`);
      }
    }
  }
  return lines.join("\n") + "\n";
}

export interface McpServerInput {
  name: string;
  transport: "http" | "stdio";
  url?: string;
  headers?: Record<string, string>;
  command?: string;
  args?: string[];
  env?: Record<string, string>;
}

/**
 * Download the current agent bundle, add an MCP server YAML file,
 * and re-upload via PUT.
 */
export async function addMcpServerToSession(
  sessionId: string,
  server: McpServerInput,
): Promise<void> {
  // 1. Download current bundle
  const res = await authenticatedFetch(
    `/v1/sessions/${encodeURIComponent(sessionId)}/agent/contents`,
  );
  if (!res.ok) throw new Error(`Failed to download bundle: ${res.status}`);
  const bundleBytes = await res.arrayBuffer();

  // 2. Decompress and parse tar
  const tar = await gunzip(bundleBytes);
  const entries = parseTar(tar);

  // 3. Add new MCP server file
  const yamlContent = buildMcpYaml(server);
  const fileName = `tools/mcp/${server.name}.yaml`;
  // Remove existing entry with same name if present
  const filtered = entries.filter((e) => e.name !== fileName);
  filtered.push({
    name: fileName,
    content: new TextEncoder().encode(yamlContent),
  });

  // 4. Rebuild tar.gz and upload
  const newTar = buildTar(filtered);
  const newGz = await gzip(newTar);
  const form = new FormData();
  form.append(
    "bundle",
    new File([newGz.buffer as ArrayBuffer], "agent.tar.gz", { type: "application/gzip" }),
  );
  const putRes = await authenticatedFetch(`/v1/sessions/${encodeURIComponent(sessionId)}/agent`, {
    method: "PUT",
    body: form,
  });
  if (!putRes.ok) {
    const text = await putRes.text();
    throw new Error(`Failed to update agent: ${putRes.status} ${text}`);
  }
}

/**
 * Download the current agent bundle, remove an MCP server YAML file,
 * and re-upload via PUT.
 */
export async function removeMcpServerFromSession(
  sessionId: string,
  serverName: string,
): Promise<void> {
  // 1. Download current bundle
  const res = await authenticatedFetch(
    `/v1/sessions/${encodeURIComponent(sessionId)}/agent/contents`,
  );
  if (!res.ok) throw new Error(`Failed to download bundle: ${res.status}`);
  const bundleBytes = await res.arrayBuffer();

  // 2. Decompress and parse tar
  const tar = await gunzip(bundleBytes);
  const entries = parseTar(tar);

  // 3. Remove the MCP server file
  const fileName = `tools/mcp/${serverName}.yaml`;
  const filtered = entries.filter((e) => e.name !== fileName);

  // Also remove inline MCP declarations from config.yaml if present.
  // For inline MCPs, we need to remove the entry from the tools block.
  const configIdx = filtered.findIndex((e) => e.name === "config.yaml");
  if (configIdx >= 0) {
    const configText = new TextDecoder().decode(filtered[configIdx].content);
    const cleaned = removeInlineMcpFromYaml(configText, serverName);
    if (cleaned !== configText) {
      filtered[configIdx] = {
        name: "config.yaml",
        content: new TextEncoder().encode(cleaned),
      };
    }
  }

  if (filtered.length === entries.length && configIdx < 0) {
    // Nothing was removed
    return;
  }

  // 4. Rebuild tar.gz and upload
  const newTar = buildTar(filtered);
  const newGz = await gzip(newTar);
  const form = new FormData();
  form.append(
    "bundle",
    new File([newGz.buffer as ArrayBuffer], "agent.tar.gz", { type: "application/gzip" }),
  );
  const putRes = await authenticatedFetch(`/v1/sessions/${encodeURIComponent(sessionId)}/agent`, {
    method: "PUT",
    body: form,
  });
  if (!putRes.ok) {
    const text = await putRes.text();
    throw new Error(`Failed to update agent: ${putRes.status} ${text}`);
  }
}

/**
 * Remove an inline MCP server block from config.yaml text.
 * Handles the `tools:` block format where MCP servers are declared as:
 *   tools:
 *     servername:
 *       type: mcp
 *       ...
 */
function removeInlineMcpFromYaml(yaml: string, serverName: string): string {
  const lines = yaml.split("\n");
  const result: string[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    // Match "  <serverName>:" at the tools indentation level (2 spaces)
    if (line.match(new RegExp(`^  ${escapeRegex(serverName)}:\\s*$`))) {
      // Check if next line has "type: mcp"
      if (i + 1 < lines.length && lines[i + 1].trim().startsWith("type: mcp")) {
        // Skip this entire block (lines indented more than 2 spaces)
        i++;
        while (i < lines.length && (lines[i].match(/^    /) || lines[i].trim() === "")) {
          i++;
        }
        continue;
      }
    }
    result.push(line);
    i++;
  }
  return result.join("\n");
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** Convert a McpServerSummary (read-only wire format) to an input shape. */
export function summaryToInput(srv: McpServerSummary): McpServerInput {
  return {
    name: srv.name,
    transport: srv.transport as "http" | "stdio",
    url: srv.url ?? undefined,
    command: srv.command ?? undefined,
    args: srv.args,
  };
}
