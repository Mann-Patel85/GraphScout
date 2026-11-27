/** Split corpus text into its leading "[Infobox …]" key/value block and the article body. */
export function splitInfobox(text: string): { fields: Array<[string, string]>; body: string } {
  const lines = text.split("\n");
  if (!lines[0]?.trim().startsWith("[Infobox")) return { fields: [], body: text.trim() };

  const fields: Array<[string, string]> = [];
  let i = 1;
  for (; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) break;
    const idx = line.indexOf(":");
    if (idx > 0) fields.push([line.slice(0, idx).trim(), line.slice(idx + 1).trim()]);
  }
  return { fields, body: lines.slice(i).join("\n").trim() };
}

/** Infobox keys worth showing in a compact preview, in display order. */
export const KEY_FIELDS = ["event", "games", "venue", "date", "dates", "competitors", "gold"];
